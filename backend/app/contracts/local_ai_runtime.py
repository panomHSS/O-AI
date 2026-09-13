"""Provider-neutral contracts for a configured Local AI runtime."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LocalAIRuntimeError(Exception):
    """Base error from a Local AI runtime boundary."""


class LocalAIRuntimeUnavailableError(LocalAIRuntimeError):
    """Raised when the configured Local AI runtime is offline."""


class LocalAIRuntimeTimeoutError(LocalAIRuntimeError):
    """Raised when a Local AI runtime call exceeds its configured timeout."""


class LocalAIRuntimeResponseError(LocalAIRuntimeError):
    """Raised when a Local AI runtime returns a malformed response."""


@runtime_checkable
class LocalAIRuntimeClient(Protocol):
    """Minimal, provider-neutral client surface consumed by LocalAIAdapter."""

    def is_runtime_available(self) -> bool:
        """Return whether the configured runtime can be reached."""
        ...

    def is_model_available(self, model: str) -> bool:
        """Return whether the configured model is installed in the runtime."""
        ...

    def is_model_loaded(self, model: str) -> bool:
        """Return whether the configured model is currently loaded."""
        ...

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        timeout_seconds: float,
        context_length: int,
    ) -> str:
        """Generate text without exposing a runtime-specific response type."""
        ...
