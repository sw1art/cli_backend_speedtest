"""Ports for publishing task messages to the queue."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class MessagePublisher(ABC):
    @abstractmethod
    async def publish(self, task_id: UUID) -> None:
        """Publish a task id to the processing queue."""


class RetryableMessagePublisher(MessagePublisher):
    """A publisher that can also schedule a delayed retry of a task message."""

    @abstractmethod
    async def publish_retry(self, task_id: UUID, retry_count: int, delay_ms: int) -> None:
        """Publish a task id to the retry queue with a delay."""
