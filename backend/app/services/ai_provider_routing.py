"""Immutable D32 policy for AI provider route enablement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIProviderRoutingPolicy:
    """Describe which registered AI adapters are eligible for routing."""

    default_adapter_id: str
    enabled_adapter_ids: frozenset[str]

    def __post_init__(self) -> None:
        default_adapter_id = self._validated_adapter_id(
            self.default_adapter_id,
            field_name="default_adapter_id",
        )
        enabled_adapter_ids = frozenset(self.enabled_adapter_ids)
        for adapter_id in enabled_adapter_ids:
            self._validated_adapter_id(
                adapter_id,
                field_name="enabled_adapter_ids",
            )

        object.__setattr__(self, "default_adapter_id", default_adapter_id)
        object.__setattr__(self, "enabled_adapter_ids", enabled_adapter_ids)

    @staticmethod
    def _validated_adapter_id(adapter_id: object, *, field_name: str) -> str:
        if (
            not isinstance(adapter_id, str)
            or not adapter_id
            or adapter_id != adapter_id.strip()
        ):
            raise ValueError(
                f"D32 {field_name} entries must be non-empty trimmed strings."
            )
        return adapter_id
