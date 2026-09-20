"""Read-only D102 Local AI runtime/model visibility service."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.local_ai_runtime import (
    LocalAIModelDiscoveryProvider,
    LocalAIRuntimeClient,
)
from app.contracts.local_ai_visibility import (
    LocalAIModelDiscoveryVisibilityStatus,
    LocalAIRuntimeVisibility,
)
from app.services.local_ai_config import LocalAIAdapterConfig


@dataclass(frozen=True, slots=True)
class LocalAIRuntimeVisibilityService:
    """Observe Local AI state without gaining execution or mutation authority."""

    config: LocalAIAdapterConfig
    runtime_client: LocalAIRuntimeClient | None

    def get_visibility(self) -> LocalAIRuntimeVisibility:
        config = self.config

        if not config.enabled:
            return LocalAIRuntimeVisibility(
                enabled=False,
                backend_id=config.backend_id,
                runtime_status="disabled",
                configured_model_id=config.model,
                configured_model_installed=None,
                configured_model_loaded=None,
                model_discovery_status="not_checked",
                installed_models=(),
                reason_code="local_ai_disabled",
            )

        client = self.runtime_client
        if client is None:
            return self._runtime_unavailable()

        try:
            runtime_available = client.is_runtime_available()
        except Exception:
            return self._runtime_unavailable()

        if type(runtime_available) is not bool:
            return self._runtime_unavailable()
        if not runtime_available:
            return self._runtime_offline()

        if not isinstance(client, LocalAIModelDiscoveryProvider):
            return self._online_without_models(
                discovery_status="unsupported",
                reason_code="model_discovery_unsupported",
            )

        try:
            discovered_models = client.list_models()
            installed_models = self._canonical_models(discovered_models)
        except Exception:
            return self._online_without_models(
                discovery_status="unavailable",
                reason_code="model_discovery_unavailable",
            )

        configured_model_installed = config.model in installed_models
        if not configured_model_installed:
            return LocalAIRuntimeVisibility(
                enabled=True,
                backend_id=config.backend_id,
                runtime_status="online",
                configured_model_id=config.model,
                configured_model_installed=False,
                configured_model_loaded=None,
                model_discovery_status="available",
                installed_models=installed_models,
                reason_code="configured_model_missing",
            )

        configured_model_loaded: bool | None
        try:
            loaded = client.is_model_loaded(config.model)
            configured_model_loaded = loaded if type(loaded) is bool else None
        except Exception:
            configured_model_loaded = None

        return LocalAIRuntimeVisibility(
            enabled=True,
            backend_id=config.backend_id,
            runtime_status="online",
            configured_model_id=config.model,
            configured_model_installed=True,
            configured_model_loaded=configured_model_loaded,
            model_discovery_status="available",
            installed_models=installed_models,
            reason_code="models_discovered",
        )

    def _runtime_offline(self) -> LocalAIRuntimeVisibility:
        return LocalAIRuntimeVisibility(
            enabled=True,
            backend_id=self.config.backend_id,
            runtime_status="offline",
            configured_model_id=self.config.model,
            configured_model_installed=None,
            configured_model_loaded=None,
            model_discovery_status="not_checked",
            installed_models=(),
            reason_code="runtime_offline",
        )

    def _runtime_unavailable(self) -> LocalAIRuntimeVisibility:
        return LocalAIRuntimeVisibility(
            enabled=True,
            backend_id=self.config.backend_id,
            runtime_status="unavailable",
            configured_model_id=self.config.model,
            configured_model_installed=None,
            configured_model_loaded=None,
            model_discovery_status="not_checked",
            installed_models=(),
            reason_code="runtime_unavailable",
        )

    def _online_without_models(
        self,
        *,
        discovery_status: LocalAIModelDiscoveryVisibilityStatus,
        reason_code: str,
    ) -> LocalAIRuntimeVisibility:
        return LocalAIRuntimeVisibility(
            enabled=True,
            backend_id=self.config.backend_id,
            runtime_status="online",
            configured_model_id=self.config.model,
            configured_model_installed=None,
            configured_model_loaded=None,
            model_discovery_status=discovery_status,
            installed_models=(),
            reason_code=reason_code,
        )

    @staticmethod
    def _canonical_models(model_ids: object) -> tuple[str, ...]:
        if not isinstance(model_ids, tuple):
            raise TypeError("Local AI model discovery must return a tuple.")

        validated: list[str] = []
        for model_id in model_ids:
            if (
                not isinstance(model_id, str)
                or not model_id
                or model_id != model_id.strip()
            ):
                raise ValueError("Local AI model discovery returned an invalid model ID.")
            validated.append(model_id)

        if len(set(validated)) != len(validated):
            raise ValueError("Local AI model discovery returned duplicate model IDs.")
        return tuple(sorted(validated))
