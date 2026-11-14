"""Core download-benchmark logic.

This module is intentionally free of CLI, logging, and presentation concerns so
it can be unit-tested in isolation. The public entry point is
:class:`DownloadBenchmarker`, backed by the small data containers
:class:`RequestResult` and :class:`BenchmarkSummary`.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

import httpx

from .errors import InvalidURLError

DEFAULT_REQUESTS = 10
DEFAULT_TIMEOUT_SECONDS = 30.0
ALLOWED_SCHEMES = ("http", "https")


@dataclass(frozen=True)
class RequestResult:
    """Outcome of a single HTTP request."""

    index: int
    elapsed_seconds: float
    bytes_downloaded: int
    status_code: Optional[int]
    success: bool
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Aggregate statistics over the requests that have run so far.

    Averages, totals and speed are computed over *successful* (2xx) requests
    only. Failed requests are reported individually but excluded from the
    aggregate numbers.
    """

    url: str
    requested: int
    results: List[RequestResult] = field(default_factory=list)

    @property
    def successful_results(self) -> List[RequestResult]:
        return [r for r in self.results if r.success]

    @property
    def successful(self) -> int:
        return len(self.successful_results)

    @property
    def failed(self) -> int:
        return self.requested - self.successful

    @property
    def total_bytes(self) -> int:
        return sum(r.bytes_downloaded for r in self.successful_results)

    @property
    def total_time(self) -> float:
        """Total time spent on successful requests, in seconds."""
        return sum(r.elapsed_seconds for r in self.successful_results)

    @property
    def average_time(self) -> Optional[float]:
        """Average per-request time over successful requests, in seconds."""
        if not self.successful_results:
            return None
        return self.total_time / self.successful

    @property
    def average_speed(self) -> Optional[float]:
        """Average download speed over successful requests, in bytes/second."""
        if self.total_time <= 0 or not self.successful_results:
            return None
        return self.total_bytes / self.total_time

    @property
    def min_time(self) -> Optional[float]:
        if not self.successful_results:
            return None
        return min(r.elapsed_seconds for r in self.successful_results)

    @property
    def max_time(self) -> Optional[float]:
        if not self.successful_results:
            return None
        return max(r.elapsed_seconds for r in self.successful_results)

    @property
    def median_time(self) -> Optional[float]:
        if not self.successful_results:
            return None
        return statistics.median(r.elapsed_seconds for r in self.successful_results)

    @property
    def p95_time(self) -> Optional[float]:
        return _percentile([r.elapsed_seconds for r in self.successful_results], 0.95)

    @property
    def stddev_time(self) -> Optional[float]:
        if len(self.successful_results) < 2:
            return None
        return statistics.stdev(r.elapsed_seconds for r in self.successful_results)


def validate_url(url: str) -> str:
    """Validate and normalise a target URL.

    Only ``http`` and ``https`` URLs that contain a host are accepted.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidURLError("URL must be a non-empty string.")
    candidate = url.strip()
    try:
        parsed = httpx.URL(candidate)
    except httpx.InvalidURL as exc:
        raise InvalidURLError(f"Malformed URL: {exc}") from exc
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Unsupported scheme '{parsed.scheme}'. Use {' or '.join(ALLOWED_SCHEMES)}."
        )
    if not parsed.host:
        raise InvalidURLError(f"URL must contain a host: '{candidate}'.")
    return str(parsed)


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection timeout"
    if isinstance(exc, httpx.ReadTimeout):
        return "read timeout"
    if isinstance(exc, httpx.ConnectError):
        return f"connection error: {exc}"
    if isinstance(exc, httpx.TooManyRedirects):
        return "too many redirects"
    if isinstance(exc, httpx.InvalidURL):
        return f"invalid URL: {exc}"
    return f"{type(exc).__name__}: {exc}"


def _percentile(values: List[float], p: float) -> Optional[float]:
    """Return the ``p``-th percentile (0.0-1.0) using linear interpolation."""
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return ordered[int(k)]
    weight = k - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


class DownloadBenchmarker:
    """Performs sequential HTTP GET requests and reports per-request timing."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._timeout = timeout
        self._client = client

    def iter_results(self, url: str, requests: int = DEFAULT_REQUESTS) -> Iterator[RequestResult]:
        """Yield one :class:`RequestResult` per request, in order.

        The HTTP client is opened once and reused across the sequence, then
        closed when the generator finishes.
        """
        target = validate_url(url)
        if requests < 1:
            raise ValueError("requests must be at least 1")

        owns_client = self._client is None
        client = self._client
        if owns_client:
            client = httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "download-benchmark"},
            )
        try:
            for index in range(1, requests + 1):
                yield self._perform(client, target, index)
        finally:
            if owns_client:
                client.close()

    def run(self, url: str, requests: int = DEFAULT_REQUESTS) -> BenchmarkSummary:
        """Run a full benchmark and return the aggregate summary."""
        target = validate_url(url)
        if requests < 1:
            raise ValueError("requests must be at least 1")
        summary = BenchmarkSummary(url=target, requested=requests)
        for result in self.iter_results(target, requests):
            summary.results.append(result)
        return summary

    def _perform(self, client: httpx.Client, url: str, index: int) -> RequestResult:
        start = time.perf_counter()
        try:
            # Request uncompressed content (Accept-Encoding: identity) so that
            # ``len(body)`` equals the bytes actually transferred over the wire
            # rather than a decompressed payload.
            response = client.get(url, headers={"Accept-Encoding": "identity"})
            body = response.content  # force a full read of the response body
            elapsed = time.perf_counter() - start
            success = 200 <= response.status_code < 300
            error = None if success else f"HTTP {response.status_code}"
            return RequestResult(
                index=index,
                elapsed_seconds=elapsed,
                bytes_downloaded=len(body),
                status_code=response.status_code,
                success=success,
                error=error,
            )
        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - start
            return RequestResult(
                index=index,
                elapsed_seconds=elapsed,
                bytes_downloaded=0,
                status_code=None,
                success=False,
                error=_describe_error(exc),
            )
