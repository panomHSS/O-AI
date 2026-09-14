"""Central D34 AI capability/model discovery over the D31 adapter registry."""

from __future__ import annotations

from collections.abc import Iterable

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_REASON_SOURCE_MISSING,
    AI_DISCOVERY_STATUS_UNAVAILABLE,
    AIAdapterDiscovery,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_discovery_sources import AIModelDiscoverySource


class AICapabilityModelDiscovery:
    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        sources: Iterable[AIModelDiscoverySource],
    ) -> None:
        self._registry = registry
        source_map: dict[str, AIModelDiscoverySource] = {}
        for source in sources:
            if not isinstance(source, AIModelDiscoverySource):
                raise TypeError("D34 source must satisfy AIModelDiscoverySource.")
            adapter_id = source.adapter_id
            if not isinstance(adapter_id, str) or not adapter_id or adapter_id != adapter_id.strip():
                raise ValueError("D34 source adapter ID must be non-empty and trimmed.")
            if adapter_id in source_map:
                raise ValueError(f"Duplicate D34 discovery source: {adapter_id}.")
            if registry.resolve_ai(adapter_id) is None:
                raise ValueError(f"D34 discovery source is not a registered AI adapter: {adapter_id}.")
            source_map[adapter_id] = source
        self._sources = source_map

    @property
    def source_adapter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._sources))

    def discover(self, adapter_id: str) -> AIAdapterDiscovery:
        if self._registry.resolve_ai(adapter_id) is None:
            raise KeyError(f"Unknown registered AI adapter: {adapter_id}.")
        source = self._sources.get(adapter_id)
        if source is None:
            return AIAdapterDiscovery(
                adapter_id=adapter_id,
                status=AI_DISCOVERY_STATUS_UNAVAILABLE,
                configured_model_id=None,
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
                models=(),
                reason_code=AI_DISCOVERY_REASON_SOURCE_MISSING,
            )
        return source.discover()

    def discover_all(self) -> tuple[AIAdapterDiscovery, ...]:
        return tuple(self.discover(adapter_id) for adapter_id in self._registry.ai_adapter_ids)
