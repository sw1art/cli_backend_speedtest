"""Worker process: consumes tasks from RabbitMQ and executes benchmarks.

The message-processing policy lives in the application layer
(:class:`~app.application.use_cases.process_task_message.ProcessTaskMessage`);
this module is a thin composition root that wires infrastructure together and
runs the consumer loop.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from .application.use_cases.execute_benchmark import ExecuteDownloadBenchmark
from .application.use_cases.fail_task import FailDownloadTask
from .application.use_cases.process_task_message import ProcessTaskMessage
from .core.config import get_settings
from .core.logging import setup_logging
from .infrastructure.database.database import Database
from .infrastructure.http_client.httpx_client import HttpxHttpClient
from .infrastructure.messaging.rabbitmq_client import RabbitMQClient
from .infrastructure.observability.metrics import TASKS_COMPLETED, TASKS_FAILED
from .infrastructure.repositories.sqlalchemy_task_repository import SQLAlchemyTaskRepository
from .infrastructure.ssrf import build_url_guard

logger = logging.getLogger("download_benchmark.worker")


def _record_status(status: str) -> None:
    if status == "COMPLETED":
        TASKS_COMPLETED.inc()
    elif status == "FAILED":
        TASKS_FAILED.inc()


def _request_shutdown(signum, frame) -> None:
    raise KeyboardInterrupt


def _install_signal_handlers() -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _request_shutdown)
        except (ValueError, OSError, AttributeError):
            pass


async def run_worker() -> None:
    settings = get_settings()
    setup_logging()

    database = Database(settings.database_url)
    repository = SQLAlchemyTaskRepository(database.session_factory)
    http_client = HttpxHttpClient(timeout=settings.http_timeout)
    mq = RabbitMQClient(
        settings.rabbitmq_url, settings.rabbitmq_queue, settings.rabbitmq_retry_queue
    )

    url_guard = build_url_guard(settings)
    execute = ExecuteDownloadBenchmark(
        repository=repository, http_client=http_client, url_guard=url_guard
    )
    fail_task = FailDownloadTask(repository=repository)
    processor = ProcessTaskMessage(
        execute=execute,
        fail_task=fail_task,
        publisher=mq,
        max_retries=settings.max_retries,
        retry_delay_ms=settings.retry_delay_ms,
        on_status=_record_status,
    )

    await mq.connect()
    logger.info("Worker connected to RabbitMQ")

    try:
        async with mq.iterate() as iterator:
            async for message in iterator:
                try:
                    await processor.process(message.body)
                    await mq.ack(message)
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
    _install_signal_handlers()
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by signal")
