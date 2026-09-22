"""Immutable D34 metadata contracts for AI model/capability discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AI_CAPABILITY_TEXT_GENERATION = "text_generation"
AI_DISCOVERY_STATUS_AVAILABLE = "available"
AI_DISCOVERY_STATUS_UNAVAILABLE = "unavailable"
AI_DISCOVERY_STATUSES = frozenset({AI_DISCOVERY_STATUS_AVAILABLE, AI_DISCOVERY_STATUS_UNAVAILABLE})
AIDiscoveryStatus = Literal["available", "unavailable"]

AI_DISCOVERY_REASON_MODELS_DISCOVERED = "models_discovered"
AI_DISCOVERY_REASON_CONFIGURED_MODEL = "configured_model"
AI_DISCOVERY_REASON_ADAPTER_DISABLED = "adapter_disabled"
AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE = "runtime_unavailable"
AI_DISCOVERY_REASON_CONFIGURED_MODEL_UNAVAILABLE = "configured_model_unavailable"
AI_DISCOVERY_REASON_SOURCE_MISSING = "discovery_source_missing"
AI_DISCOVERY_REASON_MODEL_DISCOVERY_UNSUPPORTED = "model_discovery_unsupported"
AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING = "configured_model_missing"
AI_DISCOVERY_REASON_CLOUD_DISABLED = "cloud_ai_disabled"
AI_DISCOVERY_REASON_CLOUD_CREDENTIAL_MISSING = "cloud_ai_credential_missing"


def _validate_identifier(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _canonical_capability_ids(capability_ids: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(capability_ids, tuple):
        raise TypeError("capability_ids must be a tuple.")
    validated = tuple(_validate_identifier(item, label="capability ID") for item in capability_ids)
    if len(set(validated)) != len(validated):
        raise ValueError("capability_ids must not contain duplicates.")
    return tuple(sorted(validated))


@dataclass(frozen=True, slots=True)
class AIModelDescriptor:
    model_id: str
    capability_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _validate_identifier(self.model_id, label="model_id"))
        object.__setattr__(self, "capability_ids", _canonical_capability_ids(self.capability_ids))


@dataclass(frozen=True, slots=True)
class AIAdapterDiscovery:
    adapter_id: str
    status: AIDiscoveryStatus
    configured_model_id: str | None
    capability_ids: tuple[str, ...]
    models: tuple[AIModelDescriptor, ...]
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _validate_identifier(self.adapter_id, label="adapter_id"))
        if self.status not in AI_DISCOVERY_STATUSES:
            raise ValueError(f"Unsupported AI discovery status: {self.status!r}.")
        if self.configured_model_id is not None:
            object.__setattr__(
                self,
                "configured_model_id",
                _validate_identifier(self.configured_model_id, label="configured_model_id"),
            )
        object.__setattr__(self, "capability_ids", _canonical_capability_ids(self.capability_ids))
        if not isinstance(self.models, tuple):
            raise TypeError("models must be a tuple.")
        if not all(isinstance(model, AIModelDescriptor) for model in self.models):
            raise TypeError("models must contain AIModelDescriptor values.")
        model_ids = tuple(model.model_id for model in self.models)
        if len(set(model_ids)) != len(model_ids):
            raise ValueError("models must not contain duplicate model IDs.")
        object.__setattr__(self, "models", tuple(sorted(self.models, key=lambda model: model.model_id)))
        object.__setattr__(self, "reason_code", _validate_identifier(self.reason_code, label="reason_code"))
