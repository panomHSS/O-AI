"""AI Adapter Contract v1.

This boundary is additive. The existing ``ChatProvider`` string contract remains
the active compatibility path for chat until a separately approved migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable


AI_ADAPTER_CONTRACT_VERSION = "1"


@dataclass(frozen=True, slots=True)
class AIRequest:
    """Provider-neutral input for a future AI adapter."""

    content: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AIResult:
    """Provider-neutral output returned by an AI adapter."""

    content: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class AIAdapter(Protocol):
    """Versioned protocol implemented by future AI provider adapters."""

    @property
    def adapter_id(self) -> str:
        """Return the stable identifier for this adapter implementation."""
        ...

    @property
    def contract_version(self) -> str:
        """Return the adapter contract version implemented by this adapter."""
        ...

    def generate(self, request: AIRequest) -> AIResult:
        """Generate one result without exposing provider-specific types."""
        ...
