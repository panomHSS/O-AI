"""Provider-neutral contracts for a configured Local AI runtime."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


LOCAL_AI_RUNTIME_OLLAMA = "ollama"
LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY = "local_ai_generation_options_v1"


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
        response_schema: Mapping[str, object] | None = None,
        reasoning_enabled: bool | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate text with optional provider-neutral generation constraints."""
        ...

@runtime_checkable
class LocalAIModelDiscoveryProvider(Protocol):
    """Optional read-only model enumeration; not required for generation."""

    def list_models(self) -> tuple[str, ...]:
        """Return deterministic installed model identifiers without mutation."""
        ...


@runtime_checkable
class LocalAIModelControlProvider(Protocol):
    """Optional mutation boundary for exact configured-model load/unload only."""

    def load_model(self, model_id: str) -> None:
        """Load exactly one model without assistant generation."""
        ...

    def unload_model(self, model_id: str) -> None:
        """Unload exactly one model without assistant generation."""
        ...
