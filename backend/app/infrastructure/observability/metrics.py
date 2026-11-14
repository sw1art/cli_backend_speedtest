"""Prometheus metric definitions."""

from prometheus_client import Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "path", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
)

TASKS_CREATED = Counter("download_tasks_created_total", "Total download tasks created.")
TASKS_COMPLETED = Counter("download_tasks_completed_total", "Total download tasks completed.")
TASKS_FAILED = Counter("download_tasks_failed_total", "Total download tasks failed.")


def render_metrics() -> bytes:
    return generate_latest()
