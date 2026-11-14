"""Pydantic schemas for the REST API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...domain.exceptions import InvalidURL
from ...domain.services.url_validation import validate_url
from ...domain.value_objects.task_status import TaskStatus


class CreateTaskRequest(BaseModel):
    url: str
    total_requests: int = Field(default=10, ge=1, le=100)

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        try:
            validate_url(value)
        except InvalidURL as exc:
            raise ValueError(str(exc)) from exc
        return value


class RequestResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    elapsed_seconds: float
    bytes_downloaded: int
    status_code: Optional[int]
    success: bool
    error_message: Optional[str]


class BenchmarkSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    successful: int
    failed: int
    total_bytes: int
    total_time_seconds: float
    average_time_seconds: Optional[float]
    average_speed_bytes_per_second: Optional[float]


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    status: TaskStatus
    total_requests: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    summary: Optional[BenchmarkSummaryResponse]
    results: List[RequestResultResponse] = Field(default_factory=list)


class TaskResultsResponse(BaseModel):
    task_id: UUID
    url: str
    status: TaskStatus
    summary: Optional[BenchmarkSummaryResponse]
    results: List[RequestResultResponse]


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    limit: int
    offset: int
