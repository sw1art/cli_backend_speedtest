"""Use case: fetch a single download task."""
from __future__ import annotations

from uuid import UUID

from ...domain.repositories.task_repository import DownloadTaskRepository
from ..dto.task_dto import TaskDTO
from ..exceptions import TaskNotFoundError


class GetDownloadTask:
    def __init__(self, repository: DownloadTaskRepository) -> None:
        self._repository = repository

    async def execute(self, task_id: UUID) -> TaskDTO:
        task = await self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return TaskDTO.from_entity(task)
