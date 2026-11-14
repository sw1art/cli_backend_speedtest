"""Use case: transition a task from PENDING to PROCESSING."""
from __future__ import annotations

from uuid import UUID

from ...domain.repositories.task_repository import DownloadTaskRepository
from ...domain.value_objects.task_status import TaskStatus
from ..dto.task_dto import TaskDTO
from ..exceptions import TaskNotFoundError


class StartDownloadTask:
    def __init__(self, repository: DownloadTaskRepository) -> None:
        self._repository = repository

    async def execute(self, task_id: UUID) -> TaskDTO:
        task = await self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")
        if task.status is TaskStatus.PENDING:
            task.start()
            await self._repository.update(task)
        return TaskDTO.from_entity(task)
