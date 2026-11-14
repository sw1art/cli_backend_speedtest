"""Use case: execute a download benchmark for a task.

This is the worker-side use case. It is idempotent: terminal tasks are returned
as-is, a PENDING task is started, and a task already in PROCESSING (for example
after a crashed previous attempt) is resumed.
"""
from __future__ import annotations

from uuid import UUID

from ...domain.repositories.task_repository import DownloadTaskRepository
from ...domain.value_objects.task_status import TaskStatus
from ..dto.task_dto import TaskDTO
from ..exceptions import TaskNotFoundError
from ..interfaces.http_client import HttpClient


class ExecuteDownloadBenchmark:
    def __init__(
        self, repository: DownloadTaskRepository, http_client: HttpClient
    ) -> None:
        self._repository = repository
        self._http_client = http_client

    async def execute(self, task_id: UUID) -> TaskDTO:
        task = await self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")

        if task.is_terminal:
            return TaskDTO.from_entity(task)

        if task.status is TaskStatus.PENDING:
            task.start()
            await self._repository.update(task)

        results = []
        for index in range(1, task.total_requests + 1):
            result = await self._http_client.download(task.url, index)
            results.append(result)
        task.results = results

        if not any(r.success for r in results):
            task.fail("All requests failed")
        else:
            task.complete()
        await self._repository.update(task)

        return TaskDTO.from_entity(task)
