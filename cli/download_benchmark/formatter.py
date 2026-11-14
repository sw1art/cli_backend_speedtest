"""Human-readable and JSON formatting for benchmark results.

Units are decimal (SI): 1 KB = 1000 B, 1 MB = 1000 KB, and so on. Speeds are
reported in bytes-per-second formatted with the same prefixes, e.g. ``MB/s``.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .benchmark import BenchmarkSummary, RequestResult

_SIZES = ["B", "KB", "MB", "GB", "TB", "PB"]


def human_size(num_bytes: float) -> str:
    """Format a byte count using decimal (SI) units, e.g. ``2.50 MB``."""
    value = float(num_bytes)
    for unit in _SIZES:
        if value < 1000.0 or unit == _SIZES[-1]:
            if unit == "B":
                return f"{int(round(value))} B"
            return f"{value:.2f} {unit}"
        value /= 1000.0
    return f"{value:.2f} PB"  # unreachable, kept for completeness


def human_duration(seconds: float) -> str:
    return f"{seconds:.2f} sec"


def human_speed(bytes_per_second: float) -> str:
    return f"{human_size(bytes_per_second)}/s"


def format_result(result: RequestResult) -> str:
    if result.success:
        return (
            f"Request {result.index}: {human_duration(result.elapsed_seconds)}"
            f" | {human_size(result.bytes_downloaded)}"
        )
    if result.status_code is not None:
        return (
            f"Request {result.index}: {human_duration(result.elapsed_seconds)}"
            f" | HTTP {result.status_code} ({human_size(result.bytes_downloaded)})"
        )
    return (
        f"Request {result.index}: {human_duration(result.elapsed_seconds)}"
        f" | ERROR: {result.error or 'unknown error'}"
    )


def render_header(summary: BenchmarkSummary) -> str:
    return "\n".join(
        [
            "========== DOWNLOAD BENCHMARK ==========",
            "",
            f"URL: {summary.url}",
            f"Requests: {summary.requested}",
            "",
        ]
    )


def render_results(summary: BenchmarkSummary) -> str:
    return "\n".join(format_result(r) for r in summary.results)


def render_footer(summary: BenchmarkSummary) -> str:
    lines = ["----------------------------------------"]
    if summary.average_time is not None:
        lines.append(f"Average request time: {human_duration(summary.average_time)}")
        lines.append(
            f"Latency (min/median/p95/max): {human_duration(summary.min_time)} / "
            f"{human_duration(summary.median_time)} / {human_duration(summary.p95_time)} / "
            f"{human_duration(summary.max_time)}"
        )
        lines.append(f"Total downloaded: {human_size(summary.total_bytes)}")
        lines.append(f"Average speed: {human_speed(summary.average_speed)}")
    else:
        lines.append("No successful requests to summarise.")
    lines.append("========================================")
    return "\n".join(lines)


def render_report(summary: BenchmarkSummary) -> str:
    return "\n".join([render_header(summary), render_results(summary), "", render_footer(summary)])


def to_dict(summary: BenchmarkSummary) -> Dict[str, Any]:
    return {
        "url": summary.url,
        "requested": summary.requested,
        "successful": summary.successful,
        "failed": summary.failed,
        "total_bytes": summary.total_bytes,
        "total_time_seconds": round(summary.total_time, 6),
        "average_time_seconds": (
            round(summary.average_time, 6) if summary.average_time is not None else None
        ),
        "min_time_seconds": (round(summary.min_time, 6) if summary.min_time is not None else None),
        "median_time_seconds": (
            round(summary.median_time, 6) if summary.median_time is not None else None
        ),
        "p95_time_seconds": (round(summary.p95_time, 6) if summary.p95_time is not None else None),
        "max_time_seconds": (round(summary.max_time, 6) if summary.max_time is not None else None),
        "stddev_time_seconds": (
            round(summary.stddev_time, 6) if summary.stddev_time is not None else None
        ),
        "average_speed_bytes_per_second": (
            round(summary.average_speed, 2) if summary.average_speed is not None else None
        ),
        "results": [
            {
                "index": r.index,
                "elapsed_seconds": round(r.elapsed_seconds, 6),
                "bytes": r.bytes_downloaded,
                "status_code": r.status_code,
                "success": r.success,
                "error": r.error,
            }
            for r in summary.results
        ],
    }


def render_json(summary: BenchmarkSummary) -> str:
    return json.dumps(to_dict(summary), indent=2)
