"""Async HTTP client adapter implemented with httpx."""

from __future__ import annotations

import time
from typing import Optional

import httpx

from ...application.interfaces.http_client import HttpClient
from ...domain.value_objects.benchmark import RequestResult


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection timeout"
    if isinstance(exc, httpx.ReadTimeout):
        return "read timeout"
    if isinstance(exc, httpx.ConnectError):
        return f"connection error: {exc}"
    if isinstance(exc, httpx.TooManyRedirects):
        return "too many redirects"
    return f"{type(exc).__name__}: {exc}"


class HttpxHttpClient(HttpClient):
    """Performs downloads with a single reusable ``httpx.AsyncClient``.

    Connection errors and HTTP 4xx/5xx are captured as :class:`RequestResult`
    values with ``success=False`` rather than raised, so a single failed request
    does not abort the whole benchmark.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._timeout = timeout
        self._transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            )
        return self._client

    async def download(self, url: str, index: int) -> RequestResult:
        client = self._get_client()
        start = time.perf_counter()
        try:
            response = await client.get(url)
            body = await response.aread()
            elapsed = time.perf_counter() - start
            success = 200 <= response.status_code < 300
            return RequestResult(
                index=index,
                elapsed_seconds=elapsed,
                bytes_downloaded=len(body),
                status_code=response.status_code,
                success=success,
                error_message=None if success else f"HTTP {response.status_code}",
            )
        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - start
            return RequestResult(
                index=index,
                elapsed_seconds=elapsed,
                bytes_downloaded=0,
                status_code=None,
                success=False,
                error_message=_describe_error(exc),
            )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
