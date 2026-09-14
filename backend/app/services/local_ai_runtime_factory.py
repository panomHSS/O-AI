"""Fail-closed D33 factory for replaceable Local AI runtime backends."""

from __future__ import annotations

from app.adapters.ollama_runtime import OllamaRuntimeClient
from app.contracts.local_ai_runtime import (
    LOCAL_AI_RUNTIME_OLLAMA,
    LocalAIRuntimeClient,
)


class LocalAIRuntimeConfigurationError(ValueError):
    """Raised when Local AI runtime composition is not explicitly supported."""


class LocalAIRuntimeFactory:
    """Create a configured provider-neutral runtime client without probing it."""

    def create(
        self,
        *,
        backend_id: str,
        base_url: str,
    ) -> LocalAIRuntimeClient:
        if (
            not isinstance(backend_id, str)
            or not backend_id
            or backend_id != backend_id.strip()
        ):
            raise LocalAIRuntimeConfigurationError(
                "Local AI backend ID must be a non-empty trimmed string."
            )
        if (
            not isinstance(base_url, str)
            or not base_url
            or base_url != base_url.strip()
        ):
            raise LocalAIRuntimeConfigurationError(
                "Local AI base URL must be a non-empty trimmed string."
            )

        if backend_id == LOCAL_AI_RUNTIME_OLLAMA:
            return OllamaRuntimeClient(base_url=base_url)

        raise LocalAIRuntimeConfigurationError(
            f"Unsupported Local AI runtime backend: {backend_id!r}."
        )