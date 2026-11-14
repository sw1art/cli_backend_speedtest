"""Domain-layer exceptions."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-layer errors."""


class InvalidURL(DomainError):
    """Raised when a URL is malformed or unsupported."""


class UnsafeURL(DomainError):
    """Raised when a URL is rejected by the SSRF guard."""


class InvalidTaskStatusTransition(DomainError):
    """Raised when an illegal task status transition is attempted."""
