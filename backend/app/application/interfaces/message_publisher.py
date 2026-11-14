"""Port for publishing task messages to the queue."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class MessagePublisher(ABC):
    @abstractmethod
    async def publish(self, task_id: UUID) -> None:
        """Publish a task id to the processing queue."""
