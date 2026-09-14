"""Read-only D34 discovery sources for configured AI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AI_DISCOVERY_REASON_ADAPTER_DISABLED,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
    AI_DISCOVERY_REASON_CONFIGURED_MODEL_UNAVAILABLE,
    AI_DISCOVERY_REASON_MODEL_DISCOVERY_UNSUPPORTED,
    AI_DISCOVERY_REASON_MODELS_DISCOVERED,
    AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE,
    AI_DISCOVERY_STATUS_AVAILABLE,
    AI_DISCOVERY_STATUS_UNAVAILABLE,
    AIAdapterDiscovery,
    AIModelDescriptor,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import (
    LocalAIModelDiscoveryProvider,
    LocalAIRuntimeClient,
    LocalAIRuntimeError,
)


@runtime_checkable
class AIModelDiscoverySource(Protocol):
    @property
    def adapter_id(self) -> str:
        ...

    def discover(self) -> AIAdapterDiscovery:
        ...


@dataclass(frozen=True, slots=True)
class ChatGPTConfiguredModelDiscoverySource:
    configured_model_id: str | None
    adapter_id: str = CHATGPT_DEFAULT_ADAPTER_ID

    def discover(self) -> AIAdapterDiscovery:
        model = self.configured_model_id
        if model is None or not isinstance(model, str) or not model.strip():
            return AIAdapterDiscovery(
                adapter_id=self.adapter_id,
                status=AI_DISCOVERY_STATUS_UNAVAILABLE,
                configured_model_id=None,
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
                models=(),
                reason_code=AI_DISCOVERY_REASON_CONFIGURED_MODEL_MISSING,
            )
        if model != model.strip():
            raise ValueError("Configured ChatGPT model must be trimmed.")
        descriptor = AIModelDescriptor(model_id=model, capability_ids=(AI_CAPABILITY_TEXT_GENERATION,))
        return AIAdapterDiscovery(
            adapter_id=self.adapter_id,
            status=AI_DISCOVERY_STATUS_AVAILABLE,
            configured_model_id=model,
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=(descriptor,),
            reason_code=AI_DISCOVERY_REASON_CONFIGURED_MODEL,
        )


@dataclass(frozen=True, slots=True)
class LocalAIModelDiscoverySource:
    enabled: bool
    configured_model_id: str
    runtime_client: LocalAIRuntimeClient
    adapter_id: str = LOCAL_AI_ADAPTER_ID

    def discover(self) -> AIAdapterDiscovery:
        if not self.enabled:
            return self._unavailable(AI_DISCOVERY_REASON_ADAPTER_DISABLED)

        if not isinstance(self.runtime_client, LocalAIModelDiscoveryProvider):
            return self._unavailable(AI_DISCOVERY_REASON_MODEL_DISCOVERY_UNSUPPORTED)

        try:
            if not self.runtime_client.is_runtime_available():
                return self._unavailable(AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE)
            model_ids = self.runtime_client.list_models()
        except LocalAIRuntimeError:
            return self._unavailable(AI_DISCOVERY_REASON_RUNTIME_UNAVAILABLE)

        models = tuple(
            AIModelDescriptor(model_id=model_id, capability_ids=(AI_CAPABILITY_TEXT_GENERATION,))
            for model_id in model_ids
        )
        if not any(model.model_id == self.configured_model_id for model in models):
            return AIAdapterDiscovery(
                adapter_id=self.adapter_id,
                status=AI_DISCOVERY_STATUS_UNAVAILABLE,
                configured_model_id=self.configured_model_id,
                capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
                models=models,
                reason_code=AI_DISCOVERY_REASON_CONFIGURED_MODEL_UNAVAILABLE,
            )

        return AIAdapterDiscovery(
            adapter_id=self.adapter_id,
            status=AI_DISCOVERY_STATUS_AVAILABLE,
            configured_model_id=self.configured_model_id,
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=models,
            reason_code=AI_DISCOVERY_REASON_MODELS_DISCOVERED,
        )

    def _unavailable(self, reason_code: str) -> AIAdapterDiscovery:
        return AIAdapterDiscovery(
            adapter_id=self.adapter_id,
            status=AI_DISCOVERY_STATUS_UNAVAILABLE,
            configured_model_id=self.configured_model_id,
            capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
            models=(),
            reason_code=reason_code,
        )
