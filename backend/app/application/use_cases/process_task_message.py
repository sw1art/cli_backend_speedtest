"""Use case: handle a single incoming task message.

This keeps the worker's message-processing policy (parse, execute, retry, fail)
in the application layer so it can be unit-tested without a message broker.
Status notifications are injected via ``on_status`` so the application layer
stays free of observability/infrastructure concerns.
"""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional, Tuple
from uuid import UUID

from ..exceptions import TaskNotFoundError
from ..interfaces.message_publisher import RetryableMessagePublisher
from .execute_benchmark import ExecuteDownloadBenchmark
from .fail_task import FailDownloadTask

logger = logging.getLogger("download_benchmark.processor")


def parse_message_body(body: bytes) -> Optional[Tuple[UUID, int]]:
    """Parse a message body into ``(task_id, retry_count)``.

    Returns ``None`` when the body is malformed and should be dropped.
    """
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    try:
        task_id = UUID(data["task_id"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        retry_count = int(data.get("retry_count", 0))
    except (TypeError, ValueError):
        retry_count = 0
    return task_id, retry_count


class ProcessTaskMessage:
    def __init__(
        self,
        execute: ExecuteDownloadBenchmark,
        fail_task: FailDownloadTask,
        publisher: RetryableMessagePublisher,
        max_retries: int = 3,
        retry_delay_ms: int = 2000,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._execute = execute
        self._fail_task = fail_task
        self._publisher = publisher
        self._max_retries = max_retries
        self._retry_delay_ms = retry_delay_ms
        self._on_status = on_status

    async def process(self, body: bytes) -> None:
        """Process one message body.

        A clean return means the caller should acknowledge the message; a raised
        exception means the caller should requeue it.
        """
        parsed = parse_message_body(body)
        if parsed is None:
            logger.warning("Dropping malformed message")
            return

        task_id, retry_count = parsed
        try:
            dto = await self._execute.execute(task_id)
            self._notify_status(dto.status)
        except TaskNotFoundError:
            logger.warning("Task %s not found; dropping message", task_id)
        except Exception as exc:
            logger.exception("Benchmark for task %s failed", task_id)
            if retry_count < self._max_retries:
                next_retry = retry_count + 1
                await self._publisher.publish_retry(
                    task_id, next_retry, self._retry_delay_ms * next_retry
                )
            else:
                await self._fail_task.execute(
                    task_id, f"Failed after {self._max_retries} retries: {exc}"
                )
                self._notify_status("FAILED")

    def _notify_status(self, status: str) -> None:
        if self._on_status is not None:
            self._on_status(status)
