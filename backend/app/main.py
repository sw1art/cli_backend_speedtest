"""FastAPI application factory and composition root."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI

from .core.config import Settings, get_settings
from .core.logging import setup_logging
from .infrastructure.database.database import Database
from .infrastructure.messaging.rabbitmq_client import (
    RabbitMQClient,
    UnavailableMessagePublisher,
)
from .presentation.api.router import api_router


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(settings.database_url)
        app.state.database = database

        mq = RabbitMQClient(
            settings.rabbitmq_url,
            settings.rabbitmq_queue,
            settings.rabbitmq_retry_queue,
        )
        try:
            await mq.connect()
            app.state.publisher = mq
        except Exception:
            # Keep the API available even if the broker is temporarily down.
            app.state.publisher = UnavailableMessagePublisher()
        app.state.mq = mq

        yield

        try:
            await mq.close()
        except Exception:
            pass
        await database.disconnect()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(api_router)
    return app


app = create_app()
