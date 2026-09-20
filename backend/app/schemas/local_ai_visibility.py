"""Public D102 Local AI runtime/model visibility schema."""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, StrictBool

from app.contracts.local_ai_visibility import LocalAIRuntimeVisibility


LocalAIVisibilityReasonCode: TypeAlias = Literal[
    "local_ai_disabled",
    "runtime_online",
    "runtime_offline",
    "runtime_unavailable",
    "models_discovered",
    "model_discovery_unavailable",
    "model_discovery_unsupported",
    "configured_model_missing",
]


class LocalAIRuntimeVisibilityResponse(BaseModel):
    """Allowlisted owner-facing projection of D102 visibility state."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"]
    enabled: StrictBool
    backend_id: str
    runtime_status: Literal["disabled", "online", "offline", "unavailable"]
    configured_model_id: str
    configured_model_installed: StrictBool | None
    configured_model_loaded: StrictBool | None
    model_discovery_status: Literal[
        "not_checked",
        "available",
        "unavailable",
        "unsupported",
    ]
    installed_models: tuple[str, ...]
    reason_code: LocalAIVisibilityReasonCode

    @classmethod
    def from_contract(
        cls,
        visibility: LocalAIRuntimeVisibility,
    ) -> "LocalAIRuntimeVisibilityResponse":
        return cls(
            contract_version=visibility.contract_version,
            enabled=visibility.enabled,
            backend_id=visibility.backend_id,
            runtime_status=visibility.runtime_status,
            configured_model_id=visibility.configured_model_id,
            configured_model_installed=visibility.configured_model_installed,
            configured_model_loaded=visibility.configured_model_loaded,
            model_discovery_status=visibility.model_discovery_status,
            installed_models=visibility.installed_models,
            reason_code=visibility.reason_code,
        )
