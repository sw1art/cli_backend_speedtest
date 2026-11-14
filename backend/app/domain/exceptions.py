"""Domain-layer exceptions."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-layer errors."""


class InvalidURL(DomainError):
    """Raised when a URL is malformed or unsupported."""


class InvalidTaskStatusTransition(DomainError):
    """Raised when an illegal task status transition is attempted."""
