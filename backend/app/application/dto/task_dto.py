"""Data transfer objects passed between the application and presentation layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ...domain.entities.download_task import DownloadTask


@dataclass(frozen=True)
class CreateTaskDTO:
    url: str
    total_requests: int = 10


@dataclass(frozen=True)
class RequestResultDTO:
    index: int
    elapsed_seconds: float
    bytes_downloaded: int
    status_code: Optional[int]
    success: bool
    error_message: Optional[str]


@dataclass(frozen=True)
class BenchmarkSummaryDTO:
    successful: int
    failed: int
    total_bytes: int
    total_time_seconds: float
    average_time_seconds: Optional[float]
    average_speed_bytes_per_second: Optional[float]


@dataclass(frozen=True)
class TaskDTO:
    id: UUID
    url: str
    status: str
    total_requests: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    summary: Optional[BenchmarkSummaryDTO]
    results: List[RequestResultDTO] = field(default_factory=list)

    @classmethod
    def from_entity(cls, task: DownloadTask, include_results: bool = True) -> "TaskDTO":
        # A summary is only meaningful once the task has reached a terminal
        # state; pending/processing tasks report ``summary: null``.
        summary = task.summary if (include_results and task.is_terminal) else None
        results = task.results if include_results else []
        return cls(
            id=task.id,
            url=task.url,
            status=task.status.value,
            total_requests=task.total_requests,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            error_message=task.error_message,
            summary=(
                BenchmarkSummaryDTO(
                    successful=summary.successful,
                    failed=summary.failed,
                    total_bytes=summary.total_bytes,
                    total_time_seconds=summary.total_time_seconds,
                    average_time_seconds=summary.average_time_seconds,
                    average_speed_bytes_per_second=summary.average_speed_bytes_per_second,
                )
                if summary is not None
                else None
            ),
            results=[
                RequestResultDTO(
                    index=r.index,
                    elapsed_seconds=r.elapsed_seconds,
                    bytes_downloaded=r.bytes_downloaded,
                    status_code=r.status_code,
                    success=r.success,
                    error_message=r.error_message,
                )
                for r in results
            ],
        )


@dataclass(frozen=True)
class TaskListDTO:
    items: List[TaskDTO]
    total: int
    limit: int
    offset: int
