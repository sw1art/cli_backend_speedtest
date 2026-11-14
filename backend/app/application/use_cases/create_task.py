"""Use case: create a download task and enqueue it for processing."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from ...domain.entities.download_task import DownloadTask
from ...domain.repositories.task_repository import DownloadTaskRepository
from ...domain.services.url_validation import validate_url
from ..dto.task_dto import CreateTaskDTO, TaskDTO
from ..exceptions import InvalidTaskDataError, MessagePublishError
from ..interfaces.message_publisher import MessagePublisher


class CreateDownloadTask:
    def __init__(
        self,
        repository: DownloadTaskRepository,
        publisher: MessagePublisher,
        url_guard: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._url_guard = url_guard

    async def execute(self, dto: CreateTaskDTO) -> TaskDTO:
        url = validate_url(dto.url)
        if dto.total_requests < 1:
            raise InvalidTaskDataError("total_requests must be at least 1")
        if self._url_guard is not None:
            await self._url_guard(url)

        task = DownloadTask.create(url=url, total_requests=dto.total_requests)
        await self._repository.add(task)

        try:
            await self._publisher.publish(task.id)
        except Exception as exc:
            task.fail(f"Failed to enqueue task: {exc}")
            await self._repository.update(task)
            raise MessagePublishError(f"Failed to enqueue task: {exc}") from exc

        return TaskDTO.from_entity(task)
