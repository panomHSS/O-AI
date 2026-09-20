"""Immutable D102 Local AI runtime/model visibility contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


LOCAL_AI_VISIBILITY_CONTRACT_VERSION = "1"

LocalAIRuntimeVisibilityStatus: TypeAlias = Literal[
    "disabled",
    "online",
    "offline",
    "unavailable",
]
LocalAIModelDiscoveryVisibilityStatus: TypeAlias = Literal[
    "not_checked",
    "available",
    "unavailable",
    "unsupported",
]

LOCAL_AI_RUNTIME_VISIBILITY_STATUSES = frozenset(
    {"disabled", "online", "offline", "unavailable"}
)
LOCAL_AI_MODEL_DISCOVERY_VISIBILITY_STATUSES = frozenset(
    {"not_checked", "available", "unavailable", "unsupported"}
)
LOCAL_AI_VISIBILITY_REASON_CODES = frozenset(
    {
        "local_ai_disabled",
        "runtime_online",
        "runtime_offline",
        "runtime_unavailable",
        "models_discovered",
        "model_discovery_unavailable",
        "model_discovery_unsupported",
        "configured_model_missing",
    }
)


def _trimmed_identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _optional_strict_bool(value: object, *, label: str) -> bool | None:
    if value is None or type(value) is bool:
        return value
    raise ValueError(f"{label} must be a boolean or None.")


@dataclass(frozen=True, slots=True)
class LocalAIRuntimeVisibility:
    """Read-only owner visibility; never routing or execution authority."""

    enabled: bool
    backend_id: str
    runtime_status: LocalAIRuntimeVisibilityStatus
    configured_model_id: str
    configured_model_installed: bool | None
    configured_model_loaded: bool | None
    model_discovery_status: LocalAIModelDiscoveryVisibilityStatus
    installed_models: tuple[str, ...]
    reason_code: str
    contract_version: str = LOCAL_AI_VISIBILITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != LOCAL_AI_VISIBILITY_CONTRACT_VERSION:
            raise ValueError("Unsupported Local AI visibility contract version.")
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be a boolean.")

        object.__setattr__(
            self,
            "backend_id",
            _trimmed_identifier(self.backend_id, label="backend_id"),
        )
        object.__setattr__(
            self,
            "configured_model_id",
            _trimmed_identifier(
                self.configured_model_id,
                label="configured_model_id",
            ),
        )

        if self.runtime_status not in LOCAL_AI_RUNTIME_VISIBILITY_STATUSES:
            raise ValueError("Unsupported Local AI runtime visibility status.")
        if (
            self.model_discovery_status
            not in LOCAL_AI_MODEL_DISCOVERY_VISIBILITY_STATUSES
        ):
            raise ValueError("Unsupported Local AI model discovery visibility status.")

        object.__setattr__(
            self,
            "configured_model_installed",
            _optional_strict_bool(
                self.configured_model_installed,
                label="configured_model_installed",
            ),
        )
        object.__setattr__(
            self,
            "configured_model_loaded",
            _optional_strict_bool(
                self.configured_model_loaded,
                label="configured_model_loaded",
            ),
        )

        if not isinstance(self.installed_models, tuple):
            raise TypeError("installed_models must be a tuple.")
        models = tuple(
            _trimmed_identifier(model, label="installed model ID")
            for model in self.installed_models
        )
        if len(set(models)) != len(models):
            raise ValueError("installed_models must not contain duplicates.")
        object.__setattr__(self, "installed_models", tuple(sorted(models)))

        reason_code = _trimmed_identifier(
            self.reason_code,
            label="reason_code",
        )
        if reason_code not in LOCAL_AI_VISIBILITY_REASON_CODES:
            raise ValueError("Unsupported Local AI visibility reason code.")
        object.__setattr__(self, "reason_code", reason_code)

        self._validate_state_consistency()

    def _validate_state_consistency(self) -> None:
        if not self.enabled:
            if self.runtime_status != "disabled":
                raise ValueError("Disabled Local AI requires disabled runtime status.")
            if self.model_discovery_status != "not_checked":
                raise ValueError("Disabled Local AI must not report model discovery.")
            if self.installed_models:
                raise ValueError("Disabled Local AI must not expose discovered models.")
            if self.configured_model_installed is not None:
                raise ValueError("Disabled Local AI cannot assert model installation.")
            if self.configured_model_loaded is not None:
                raise ValueError("Disabled Local AI cannot assert model loaded state.")
            if self.reason_code != "local_ai_disabled":
                raise ValueError("Disabled Local AI requires local_ai_disabled reason.")
            return

        if self.runtime_status == "disabled":
            raise ValueError("Enabled Local AI cannot report disabled runtime status.")

        if self.runtime_status in {"offline", "unavailable"}:
            if self.model_discovery_status != "not_checked":
                raise ValueError(
                    "Offline/unavailable runtime must not report model discovery."
                )
            if self.installed_models:
                raise ValueError(
                    "Offline/unavailable runtime must not expose discovered models."
                )
            if self.configured_model_installed is not None:
                raise ValueError(
                    "Offline/unavailable runtime cannot assert model installation."
                )
            if self.configured_model_loaded is not None:
                raise ValueError(
                    "Offline/unavailable runtime cannot assert model loaded state."
                )

        if self.model_discovery_status != "available" and self.installed_models:
            raise ValueError(
                "installed_models are authoritative only when discovery is available."
            )

        if self.model_discovery_status == "available":
            expected_installed = self.configured_model_id in self.installed_models
            if self.configured_model_installed is not expected_installed:
                raise ValueError(
                    "configured_model_installed must match discovered model IDs."
                )

        if self.configured_model_loaded is True:
            if self.configured_model_installed is not True:
                raise ValueError(
                    "A loaded configured model must also be installed."
                )
