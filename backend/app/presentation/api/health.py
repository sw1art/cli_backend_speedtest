"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe: always 200 while the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe: 200 only when the database and broker are reachable."""
    database = getattr(request.app.state, "database", None)
    db_ok = False
    if database is not None:
        try:
            async with database.session_factory() as session:
                await session.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

    mq = getattr(request.app.state, "mq", None)
    broker_ok = mq is not None and bool(getattr(mq, "is_connected", lambda: False)())

    healthy = db_ok and broker_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "broker": "ok" if broker_ok else "unavailable",
        },
    )
