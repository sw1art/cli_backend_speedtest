"""Worker process: consumes tasks from RabbitMQ and executes benchmarks."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from .application.exceptions import TaskNotFoundError
from .application.use_cases.execute_benchmark import ExecuteDownloadBenchmark
from .application.use_cases.fail_task import FailDownloadTask
from .core.config import get_settings
from .core.logging import setup_logging
from .infrastructure.database.database import Database
from .infrastructure.http_client.httpx_client import HttpxHttpClient
from .infrastructure.messaging.rabbitmq_client import RabbitMQClient
from .infrastructure.repositories.sqlalchemy_task_repository import SQLAlchemyTaskRepository

logger = logging.getLogger("download_benchmark.worker")


async def _handle_message(message, mq, execute, fail_task, settings) -> None:
    try:
        body = json.loads(message.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Dropping malformed message")
        await mq.ack(message)
        return

    try:
        task_id = UUID(body["task_id"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Dropping message without a valid task_id")
        await mq.ack(message)
        return

    retry_count = int(body.get("retry_count", 0))

    try:
        await execute.execute(task_id)
        await mq.ack(message)
    except TaskNotFoundError:
        logger.warning("Task %s not found; dropping message", task_id)
        await mq.ack(message)
    except Exception as exc:
        logger.exception("Benchmark for task %s failed", task_id)
        if retry_count < settings.max_retries:
            next_retry = retry_count + 1
            await mq.publish_retry(task_id, next_retry, settings.retry_delay_ms * next_retry)
            await mq.ack(message)
        else:
            try:
                await fail_task.execute(
                    task_id, f"Failed after {settings.max_retries} retries: {exc}"
                )
            except Exception:
                logger.exception("Failed to mark task %s as FAILED", task_id)
            await mq.ack(message)


async def run_worker() -> None:
    settings = get_settings()
    setup_logging()

    database = Database(settings.database_url)
    repository = SQLAlchemyTaskRepository(database.session_factory)
    http_client = HttpxHttpClient(timeout=settings.http_timeout)
    mq = RabbitMQClient(
        settings.rabbitmq_url, settings.rabbitmq_queue, settings.rabbitmq_retry_queue
    )

    execute = ExecuteDownloadBenchmark(repository=repository, http_client=http_client)
    fail_task = FailDownloadTask(repository=repository)

    await mq.connect()
    logger.info("Worker connected to RabbitMQ")

    try:
        async with mq.iterate() as iterator:
            async for message in iterator:
                try:
                    await _handle_message(message, mq, execute, fail_task, settings)
                except Exception:
                    logger.exception("Unhandled worker error; rejecting message")
                    try:
                        await message.reject(requeue=True)
                    except Exception:
                        logger.exception("Failed to reject message")
    finally:
        await http_client.aclose()
        await mq.close()
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(run_worker())
