"""Use case: mark a task as FAILED (idempotent for terminal states)."""

from __future__ import annotations

from uuid import UUID

from ...domain.repositories.task_repository import DownloadTaskRepository
from ..dto.task_dto import TaskDTO
from ..exceptions import TaskNotFoundError


class FailDownloadTask:
    def __init__(self, repository: DownloadTaskRepository) -> None:
        self._repository = repository

    async def execute(self, task_id: UUID, error_message: str) -> TaskDTO:
        task = await self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")
        if not task.is_terminal:
            task.fail(error_message)
            await self._repository.update(task)
        return TaskDTO.from_entity(task)
