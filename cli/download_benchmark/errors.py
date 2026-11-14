"""Exceptions raised by the download benchmark."""

from __future__ import annotations


class BenchmarkError(Exception):
    """Base class for all benchmark errors."""


class InvalidURLError(BenchmarkError):
    """Raised when the target URL is malformed or unsupported."""


class NoSuccessfulRequestsError(BenchmarkError):
    """Raised when none of the benchmark requests succeeded."""
