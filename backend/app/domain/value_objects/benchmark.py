"""Value objects describing benchmark results and their statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class RequestResult:
    """Outcome of a single HTTP request within a benchmark task."""

    index: int
    elapsed_seconds: float
    bytes_downloaded: int
    status_code: Optional[int]
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class BenchmarkSummary:
    """Aggregate statistics over a set of request results.

    Totals and averages are computed over *successful* requests only.
    """

    successful: int
    failed: int
    total_bytes: int
    total_time_seconds: float
    average_time_seconds: Optional[float]
    average_speed_bytes_per_second: Optional[float]

    @classmethod
    def from_results(cls, results: Sequence[RequestResult]) -> "BenchmarkSummary":
        successful = [r for r in results if r.success]
        total_bytes = sum(r.bytes_downloaded for r in successful)
        total_time = sum(r.elapsed_seconds for r in successful)
        count = len(successful)
        average_time = total_time / count if count else None
        speed = total_bytes / total_time if total_time > 0 else None
        return cls(
            successful=count,
            failed=len(results) - count,
            total_bytes=total_bytes,
            total_time_seconds=total_time,
            average_time_seconds=average_time,
            average_speed_bytes_per_second=speed,
        )
