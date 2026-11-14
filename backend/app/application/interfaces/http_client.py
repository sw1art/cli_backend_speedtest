"""Port for downloading a URL and measuring per-request statistics."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain.value_objects.benchmark import RequestResult


class HttpClient(ABC):
    @abstractmethod
    async def download(self, url: str, index: int) -> RequestResult:
        """Perform one full download and return its measurement."""
