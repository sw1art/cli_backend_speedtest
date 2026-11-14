"""Use case: fetch the download task history (paginated)."""
from __future__ import annotations

from ...domain.repositories.task_repository import DownloadTaskRepository
from ..dto.task_dto import TaskDTO, TaskListDTO


class GetDownloadHistory:
    def __init__(self, repository: DownloadTaskRepository) -> None:
        self._repository = repository

    async def execute(self, limit: int = 100, offset: int = 0) -> TaskListDTO:
        tasks = await self._repository.list(limit=limit, offset=offset)
        total = await self._repository.count()
        return TaskListDTO(
            items=[TaskDTO.from_entity(t, include_results=False) for t in tasks],
            total=total,
            limit=limit,
            offset=offset,
        )
