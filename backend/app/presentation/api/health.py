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
    """Readiness probe: 200 only when the database is reachable."""
    database = getattr(request.app.state, "database", None)
    db_ok = False
    if database is not None:
        try:
            async with database.session_factory() as session:
                await session.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False

    if db_ok:
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
    return JSONResponse(
        status_code=503, content={"status": "degraded", "database": "unavailable"}
    )
