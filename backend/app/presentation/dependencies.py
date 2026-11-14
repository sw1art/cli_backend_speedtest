"""FastAPI dependency providers (composition wiring)."""
from __future__ import annotations

from fastapi import Request

from ..application.interfaces.message_publisher import MessagePublisher
from ..domain.repositories.task_repository import DownloadTaskRepository
from ..infrastructure.repositories.sqlalchemy_task_repository import SQLAlchemyTaskRepository


def get_task_repository(request: Request) -> DownloadTaskRepository:
    return SQLAlchemyTaskRepository(request.app.state.database.session_factory)


def get_message_publisher(request: Request) -> MessagePublisher:
    return request.app.state.publisher
