"""Domain service: URL validation rules (no framework dependencies)."""
from __future__ import annotations

from urllib.parse import urlsplit

from ..exceptions import InvalidURL

ALLOWED_SCHEMES = ("http", "https")


def validate_url(url: str) -> str:
    """Validate a target URL.

    Only ``http`` and ``https`` URLs that contain a host are accepted.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidURL("URL must be a non-empty string.")
    candidate = url.strip()
    try:
        parts = urlsplit(candidate)
    except ValueError as exc:
        raise InvalidURL(f"Malformed URL: {exc}") from exc
    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidURL(
            f"Unsupported scheme '{parts.scheme}'. Use {' or '.join(ALLOWED_SCHEMES)}."
        )
    if not parts.hostname:
        raise InvalidURL(f"URL must contain a host: '{candidate}'.")
    return candidate
