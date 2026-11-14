"""DownloadTask aggregate root and its state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from ..exceptions import InvalidTaskStatusTransition
from ..value_objects.benchmark import BenchmarkSummary, RequestResult
from ..value_objects.task_status import TaskStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DownloadTask:
    id: UUID
    url: str
    status: TaskStatus
    total_requests: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: List[RequestResult] = field(default_factory=list)

    @classmethod
    def create(cls, url: str, total_requests: int = 10) -> "DownloadTask":
        return cls(
            id=uuid4(),
            url=url,
            status=TaskStatus.PENDING,
            total_requests=total_requests,
            created_at=_utc_now(),
        )

    @property
    def summary(self) -> BenchmarkSummary:
        return BenchmarkSummary.from_results(self.results)

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def start(self, now: Optional[datetime] = None) -> None:
        if self.status is not TaskStatus.PENDING:
            raise InvalidTaskStatusTransition(f"Cannot start task in state {self.status.value}")
        self.status = TaskStatus.PROCESSING
        self.started_at = now or _utc_now()

    def complete(self, now: Optional[datetime] = None) -> None:
        if self.status is not TaskStatus.PROCESSING:
            raise InvalidTaskStatusTransition(f"Cannot complete task in state {self.status.value}")
        self.status = TaskStatus.COMPLETED
        self.finished_at = now or _utc_now()

    def fail(self, error_message: str, now: Optional[datetime] = None) -> None:
        if self.status not in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            raise InvalidTaskStatusTransition(f"Cannot fail task in state {self.status.value}")
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.finished_at = now or _utc_now()
