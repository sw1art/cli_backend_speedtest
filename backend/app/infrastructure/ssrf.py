"""Wiring: build an async SSRF guard closure from application settings."""

from __future__ import annotations

from typing import Awaitable, Callable

from ..core.config import Settings
from ..domain.services.ssrf import assert_safe_url


def build_url_guard(settings: Settings) -> Callable[[str], Awaitable[None]]:
    """Return ``guard(url) -> None`` that raises :class:`UnsafeURL` on bad URLs."""
    allowed_hosts = frozenset(
        h.strip() for h in settings.ssrf_allowed_hosts.split(",") if h.strip()
    )

    async def guard(url: str) -> None:
        if settings.ssrf_guard_enabled:
            await assert_safe_url(
                url,
                allow_private=settings.ssrf_allow_private,
                allowed_hosts=allowed_hosts,
            )

    return guard
