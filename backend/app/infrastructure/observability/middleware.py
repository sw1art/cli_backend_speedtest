"""ASGI middleware that records HTTP request metrics."""

from __future__ import annotations

import time

from .metrics import HTTP_DURATION, HTTP_REQUESTS


async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    # Use the matched route template (e.g. /api/v1/tasks/{task_id}) instead of
    # the raw path to avoid unbounded cardinality from UUIDs.
    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path

    HTTP_REQUESTS.labels(method=request.method, path=path, status=str(response.status_code)).inc()
    HTTP_DURATION.labels(method=request.method, path=path).observe(duration)
    return response
