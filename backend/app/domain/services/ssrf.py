"""Domain service: SSRF protection for user-supplied URLs.

Pure, stdlib-only, and async. DNS resolution is injected via ``resolver`` so the
rules are unit-testable without network access.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Awaitable, Callable
from urllib.parse import urlsplit

from ..exceptions import UnsafeURL

ALLOWED_SCHEMES = ("http", "https")


def is_unsafe_address(ip: str) -> bool:
    """Return ``True`` if the IP is not a globally routable unicast address."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return not address.is_global


async def resolve_host(host: str) -> list[str]:
    """Resolve a hostname to a de-duplicated list of IP addresses (async)."""
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


async def assert_safe_url(
    url: str,
    *,
    allow_private: bool = False,
    allowed_hosts: frozenset[str] = frozenset(),
    resolver: Callable[[str], Awaitable[list[str]]] = resolve_host,
) -> str:
    """Raise :class:`UnsafeURL` if the URL is not safe to fetch.

    Safety rules:
    - only ``http``/``https``;
    - hostname must be present;
    - hosts listed in ``allowed_hosts`` are always allowed;
    - when ``allow_private`` is set, private/loopback/link-local addresses are
      allowed (useful for local development);
    - otherwise, literal IPs and every resolved address must be globally
      routable (``ipaddress.is_global``).
    """
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURL(f"Unsupported scheme '{parts.scheme}'. Use {' or '.join(ALLOWED_SCHEMES)}.")
    host = parts.hostname
    if not host:
        raise UnsafeURL("URL must contain a host.")
    if host in allowed_hosts:
        return url
    if allow_private:
        return url

    try:
        ipaddress.ip_address(host)
        is_literal = True
    except ValueError:
        is_literal = False

    if is_literal:
        if is_unsafe_address(host):
            raise UnsafeURL(f"Host '{host}' is not a globally routable address.")
        return url

    try:
        ips = await resolver(host)
    except Exception as exc:
        raise UnsafeURL(f"Could not resolve host '{host}': {exc}") from exc

    for ip in ips:
        if is_unsafe_address(ip):
            raise UnsafeURL(f"Host '{host}' resolves to non-global address '{ip}'.")
    return url
