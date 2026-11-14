"""Repository interface (port) for DownloadTask persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.download_task import DownloadTask


class DownloadTaskRepository(ABC):
    @abstractmethod
    async def add(self, task: DownloadTask) -> DownloadTask:
        """Persist a new task."""

    @abstractmethod
    async def get(self, task_id: UUID) -> Optional[DownloadTask]:
        """Fetch a task with its results, or ``None`` if it does not exist."""

    @abstractmethod
    async def update(self, task: DownloadTask) -> DownloadTask:
        """Persist changes to an existing task, including its results."""

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[DownloadTask]:
        """Fetch tasks in reverse chronological order (metadata only)."""

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of stored tasks."""
