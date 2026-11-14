"""Task endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...application.dto.task_dto import CreateTaskDTO, TaskListDTO
from ...application.exceptions import MessagePublishError, TaskNotFoundError
from ...application.interfaces.message_publisher import MessagePublisher
from ...application.use_cases.create_task import CreateDownloadTask
from ...application.use_cases.get_history import GetDownloadHistory
from ...application.use_cases.get_results import GetDownloadResults
from ...application.use_cases.get_task import GetDownloadTask
from ...domain.repositories.task_repository import DownloadTaskRepository
from ..dependencies import get_message_publisher, get_task_repository
from ..schemas.task import (
    CreateTaskRequest,
    TaskListResponse,
    TaskResponse,
    TaskResultsResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: CreateTaskRequest,
    repository: DownloadTaskRepository = Depends(get_task_repository),
    publisher: MessagePublisher = Depends(get_message_publisher),
) -> TaskResponse:
    use_case = CreateDownloadTask(repository=repository, publisher=publisher)
    try:
        dto = await use_case.execute(
            CreateTaskDTO(url=payload.url, total_requests=payload.total_requests)
        )
    except MessagePublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    return TaskResponse.model_validate(dto)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    repository: DownloadTaskRepository = Depends(get_task_repository),
) -> TaskListResponse:
    dto: TaskListDTO = await GetDownloadHistory(repository=repository).execute(
        limit=limit, offset=offset
    )
    return TaskListResponse(
        items=[TaskResponse.model_validate(item) for item in dto.items],
        total=dto.total,
        limit=dto.limit,
        offset=dto.offset,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    repository: DownloadTaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    try:
        dto = await GetDownloadTask(repository=repository).execute(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TaskResponse.model_validate(dto)


@router.get("/{task_id}/results", response_model=TaskResultsResponse)
async def get_results(
    task_id: UUID,
    repository: DownloadTaskRepository = Depends(get_task_repository),
) -> TaskResultsResponse:
    try:
        dto = await GetDownloadResults(repository=repository).execute(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TaskResultsResponse(
        task_id=dto.id,
        url=dto.url,
        status=dto.status,
        summary=dto.summary,
        results=dto.results,
    )
