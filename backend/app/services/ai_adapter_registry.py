"""Compatibility view over the D31 unified adapter registry for AI adapters."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.ai import AIAdapter
from app.services.adapter_registry import AdapterRegistry


class AIAdapterRegistry:
    """Preserve the D29 AI-only registry surface over the D31 registry."""

    def __init__(
        self,
        adapters: Iterable[AIAdapter] | None = None,
        *,
        registry: AdapterRegistry | None = None,
    ) -> None:
        if registry is not None and adapters is not None:
            raise ValueError("Provide adapters or registry, not both.")
        self._registry = registry or AdapterRegistry(adapters or ())

    @property
    def adapter_ids(self) -> tuple[str, ...]:
        """Return registered AI adapter IDs in deterministic order."""
        return self._registry.ai_adapter_ids

    def resolve(self, adapter_id: str) -> AIAdapter | None:
        """Return a registered AI adapter without selection or invocation."""
        return self._registry.resolve_ai(adapter_id)
