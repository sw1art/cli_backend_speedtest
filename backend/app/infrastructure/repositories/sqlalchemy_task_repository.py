"""SQLAlchemy implementation of the DownloadTaskRepository port."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from ...domain.entities.download_task import DownloadTask
from ...domain.repositories.task_repository import DownloadTaskRepository
from ...domain.value_objects.benchmark import RequestResult
from ...domain.value_objects.task_status import TaskStatus
from ..database.models import DownloadTaskModel, RequestResultModel


class SQLAlchemyTaskRepository(DownloadTaskRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def add(self, task: DownloadTask) -> DownloadTask:
        async with self._session_factory() as session:
            session.add(self._to_model(task))
            await session.commit()
        return task

    async def get(self, task_id: UUID) -> Optional[DownloadTask]:
        async with self._session_factory() as session:
            model = await session.get(
                DownloadTaskModel,
                task_id,
                options=[selectinload(DownloadTaskModel.results)],
            )
            return self._to_entity(model) if model is not None else None

    async def update(self, task: DownloadTask) -> DownloadTask:
        async with self._session_factory() as session:
            model = await session.get(
                DownloadTaskModel,
                task.id,
                options=[selectinload(DownloadTaskModel.results)],
            )
            if model is None:
                raise LookupError(f"Task {task.id} not found while updating")

            model.url = task.url
            model.status = task.status.value
            model.total_requests = task.total_requests
            model.started_at = task.started_at
            model.finished_at = task.finished_at
            model.error_message = task.error_message

            model.results.clear()
            for r in task.results:
                model.results.append(
                    RequestResultModel(
                        request_index=r.index,
                        elapsed_seconds=r.elapsed_seconds,
                        bytes_downloaded=r.bytes_downloaded,
                        status_code=r.status_code,
                        success=r.success,
                        error_message=r.error_message,
                    )
                )
            await session.commit()
        return task

    async def list(self, limit: int = 100, offset: int = 0) -> List[DownloadTask]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(DownloadTaskModel)
                .order_by(DownloadTaskModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [
                self._to_entity(m, include_results=False)
                for m in result.scalars().all()
            ]

    async def count(self) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(DownloadTaskModel)
            )
            return int(result.scalar_one())

    @staticmethod
    def _to_model(task: DownloadTask) -> DownloadTaskModel:
        return DownloadTaskModel(
            id=task.id,
            url=task.url,
            status=task.status.value,
            total_requests=task.total_requests,
            created_at=task.created_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
            error_message=task.error_message,
            results=[
                RequestResultModel(
                    request_index=r.index,
                    elapsed_seconds=r.elapsed_seconds,
                    bytes_downloaded=r.bytes_downloaded,
                    status_code=r.status_code,
                    success=r.success,
                    error_message=r.error_message,
                )
                for r in task.results
            ],
        )

    @staticmethod
    def _to_entity(model: DownloadTaskModel, include_results: bool = True) -> DownloadTask:
        results = (
            [
                RequestResult(
                    index=r.request_index,
                    elapsed_seconds=r.elapsed_seconds,
                    bytes_downloaded=r.bytes_downloaded,
                    status_code=r.status_code,
                    success=r.success,
                    error_message=r.error_message,
                )
                for r in model.results
            ]
            if include_results
            else []
        )
        return DownloadTask(
            id=model.id,
            url=model.url,
            status=TaskStatus(model.status),
            total_requests=model.total_requests,
            created_at=model.created_at,
            started_at=model.started_at,
            finished_at=model.finished_at,
            error_message=model.error_message,
            results=results,
        )
