"""In-memory fakes used across tests to keep layers decoupled."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from app.application.interfaces.http_client import HttpClient
from app.application.interfaces.message_publisher import MessagePublisher
from app.domain.entities.download_task import DownloadTask
from app.domain.repositories.task_repository import DownloadTaskRepository
from app.domain.value_objects.benchmark import RequestResult


class FakeTaskRepository(DownloadTaskRepository):
    def __init__(self, tasks: Optional[List[DownloadTask]] = None) -> None:
        self._tasks: Dict[UUID, DownloadTask] = {}
        for task in tasks or []:
            self._tasks[task.id] = task

    async def add(self, task: DownloadTask) -> DownloadTask:
        self._tasks[task.id] = task
        return task

    async def get(self, task_id: UUID) -> Optional[DownloadTask]:
        return self._tasks.get(task_id)

    async def update(self, task: DownloadTask) -> DownloadTask:
        self._tasks[task.id] = task
        return task

    async def list(self, limit: int = 100, offset: int = 0) -> List[DownloadTask]:
        items = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return items[offset : offset + limit]

    async def count(self) -> int:
        return len(self._tasks)


class FakePublisher(MessagePublisher):
    def __init__(self) -> None:
        self.published: List[UUID] = []
        self.fail = False

    async def publish(self, task_id: UUID) -> None:
        if self.fail:
            raise ConnectionError("broker down")
        self.published.append(task_id)


class FakeHttpClient(HttpClient):
    def __init__(
        self,
        results: Optional[List[RequestResult]] = None,
        exc: Optional[Exception] = None,
    ) -> None:
        self._results = results or []
        self._exc = exc
        self.calls: List[tuple] = []

    async def download(self, url: str, index: int) -> RequestResult:
        self.calls.append((url, index))
        if self._exc is not None:
            raise self._exc
        if index - 1 < len(self._results):
            return self._results[index - 1]
        return RequestResult(
            index=index,
            elapsed_seconds=1.0,
            bytes_downloaded=1000,
            status_code=200,
            success=True,
        )
