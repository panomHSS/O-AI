"""D29 dependency-composed registry for AI Adapter Contract v1."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIAdapter


class AIAdapterRegistry:
    """Validate and resolve registered adapters without invoking them."""

    def __init__(self, adapters: Iterable[AIAdapter]) -> None:
        self._adapters: dict[str, AIAdapter] = {}
        for adapter in adapters:
            if not isinstance(adapter, AIAdapter):
                raise TypeError("D29 adapters must implement AIAdapter Contract v1.")
            if adapter.contract_version != AI_ADAPTER_CONTRACT_VERSION:
                raise ValueError("D29 adapters must implement AI Adapter Contract v1.")
            if adapter.adapter_id in self._adapters:
                raise ValueError("D29 adapter IDs must be unique.")
            self._adapters[adapter.adapter_id] = adapter

    def resolve(self, adapter_id: str) -> AIAdapter | None:
        """Return a registered adapter without provider selection or invocation."""
        return self._adapters.get(adapter_id)
