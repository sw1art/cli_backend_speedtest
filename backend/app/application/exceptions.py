"""Application-layer exceptions."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for application-layer errors."""


class TaskNotFoundError(ApplicationError):
    """Raised when a requested task does not exist."""


class MessagePublishError(ApplicationError):
    """Raised when a task message cannot be published to the queue."""


class InvalidTaskDataError(ApplicationError):
    """Raised when use-case input is invalid."""
