"""D26 Local AI adapter with no cloud fallback behavior."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
import math

from app.services.local_ai_profile import LocalAIProfileResolver

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import (
    LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY,
    AUTHORIZED_LOCAL_AI_PROFILE_KEY,
    AUTHORIZED_LOCAL_AI_MODEL_KEY,
    LocalAIRuntimeClient,
    LocalAIRuntimeResponseError,
    LocalAIRuntimeTimeoutError,
    LocalAIRuntimeUnavailableError,
)


class LocalAIAdapterError(Exception):
    """Base error for safe, local-only adapter failures."""


class LocalAIUnavailableError(LocalAIAdapterError):
    """Raised when Local AI is disabled, offline, or lacks its configured model."""


class LocalAIResponseError(LocalAIAdapterError):
    """Raised when Local AI cannot return a valid response."""


class InferenceTelemetrySession(Protocol):
    """Best-effort session boundary used around one local inference."""

    def stop(self) -> None:
        """Stop sampling and mark the inference session idle."""
        ...


class InferenceTelemetryProvider(Protocol):
    """Optional telemetry boundary kept separate from inference behavior."""

    def start_inference_session(self, *, model: str) -> InferenceTelemetrySession:
        """Start best-effort telemetry without blocking inference."""
        ...


class LocalAIAdapter:
    """Adapt a configured Local AI runtime to AI Adapter Contract v1."""

    adapter_id = LOCAL_AI_ADAPTER_ID
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        runtime_client: LocalAIRuntimeClient,
        enabled: bool,
        profiles: LocalAIProfileResolver,
        telemetry_provider: InferenceTelemetryProvider | None = None,
    ) -> None:
        self._runtime_client = runtime_client
        self._enabled = enabled
        self._profiles = profiles
        self._telemetry_provider = telemetry_provider

    def generate(self, request: AIRequest) -> AIResult:
        """Generate locally after fail-closed runtime and model checks."""
        if not isinstance(request.metadata, Mapping):
            raise LocalAIResponseError("Local AI authorization binding is invalid.")
        try:
            profile = self._profiles.authorized_profile(
                request.metadata.get(AUTHORIZED_LOCAL_AI_PROFILE_KEY),
                request.metadata.get(AUTHORIZED_LOCAL_AI_MODEL_KEY),
            )
        except ValueError as error:
            raise LocalAIResponseError("Local AI authorization binding is invalid.") from error
        generation_options = self._generation_options(request)
        response_schema, request_reasoning, temperature = generation_options or (None, None, None)
        reasoning = profile.reasoning_enabled
        if request_reasoning is not None:
            if reasoning is not None and request_reasoning is not reasoning:
                raise LocalAIResponseError("Local AI reasoning policy conflicts with request.")
            reasoning = request_reasoning
        self._require_available(profile.model_id)
        telemetry_session = self._start_telemetry_session(profile.model_id)
        try:
            try:
                content = self._runtime_client.generate(
                    model=profile.model_id,
                    prompt=request.content,
                    timeout_seconds=profile.timeout_seconds,
                    context_length=profile.context_length,
                    response_schema=response_schema,
                    reasoning_enabled=reasoning,
                    temperature=temperature,
                )
            except LocalAIRuntimeTimeoutError as error:
                raise LocalAIResponseError("Local AI request timed out.") from error
            except LocalAIRuntimeUnavailableError as error:
                raise LocalAIUnavailableError("Local AI runtime is unavailable.") from error
            except LocalAIRuntimeResponseError as error:
                raise LocalAIResponseError("Local AI returned an invalid response.") from error

            if not isinstance(content, str) or not content.strip():
                raise LocalAIResponseError("Local AI returned an invalid response.")
            return AIResult(content=content.strip())
        finally:
            if telemetry_session is not None:
                try:
                    telemetry_session.stop()
                except Exception:
                    pass

    @staticmethod
    def _generation_options(
        request: AIRequest,
    ) -> tuple[Mapping[str, object] | None, bool | None, float | None] | None:
        if not isinstance(request.metadata, Mapping):
            raise LocalAIResponseError("Local AI generation options are invalid.")

        raw = request.metadata.get(LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY)
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise LocalAIResponseError("Local AI generation options are invalid.")
        if not set(raw) <= {
            "response_schema",
            "reasoning_enabled",
            "temperature",
        }:
            raise LocalAIResponseError("Local AI generation options are invalid.")

        response_schema = raw.get("response_schema")
        reasoning_enabled = raw.get("reasoning_enabled")
        temperature = raw.get("temperature")

        if "response_schema" in raw and (not isinstance(response_schema, Mapping) or not response_schema):
            raise LocalAIResponseError("Local AI generation options are invalid.")
        if "reasoning_enabled" in raw and type(reasoning_enabled) is not bool:
            raise LocalAIResponseError("Local AI generation options are invalid.")
        if "temperature" in raw and (
            type(temperature) not in {int, float}
            or isinstance(temperature, bool)
            or not math.isfinite(temperature)
            or not 0 <= temperature <= 2
        ):
            raise LocalAIResponseError("Local AI generation options are invalid.")

        return response_schema, reasoning_enabled, float(temperature) if temperature is not None else None

    def _require_available(self, model: str) -> None:
        if not self._enabled:
            raise LocalAIUnavailableError("Local AI is disabled.")
        try:
            runtime_online = self._runtime_client.is_runtime_available()
            model_available = (
                self._runtime_client.is_model_available(model)
                if runtime_online
                else False
            )
        except Exception as error:
            raise LocalAIUnavailableError("Local AI runtime is unavailable.") from error

        if not runtime_online:
            raise LocalAIUnavailableError("Local AI runtime is unavailable.")
        if not model_available:
            raise LocalAIUnavailableError("Local AI model is unavailable.")

    def _start_telemetry_session(self, model: str) -> InferenceTelemetrySession | None:
        if self._telemetry_provider is None:
            return None
        try:
            return self._telemetry_provider.start_inference_session(model=model)
        except Exception:
            return None
