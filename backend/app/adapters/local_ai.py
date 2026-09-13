"""D26 Local AI adapter with no cloud fallback behavior."""

from __future__ import annotations

from typing import Protocol

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import (
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

    def start_inference_session(self) -> InferenceTelemetrySession:
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
        model: str,
        timeout_seconds: float,
        context_length: int,
        telemetry_provider: InferenceTelemetryProvider | None = None,
    ) -> None:
        self._runtime_client = runtime_client
        self._enabled = enabled
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._context_length = context_length
        self._telemetry_provider = telemetry_provider

    def generate(self, request: AIRequest) -> AIResult:
        """Generate locally after fail-closed runtime and model checks."""
        self._require_available()
        telemetry_session = self._start_telemetry_session()
        try:
            try:
                content = self._runtime_client.generate(
                    model=self._model,
                    prompt=request.content,
                    timeout_seconds=self._timeout_seconds,
                    context_length=self._context_length,
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

    def _require_available(self) -> None:
        if not self._enabled:
            raise LocalAIUnavailableError("Local AI is disabled.")
        try:
            runtime_online = self._runtime_client.is_runtime_available()
            model_available = (
                self._runtime_client.is_model_available(self._model)
                if runtime_online
                else False
            )
        except Exception as error:
            raise LocalAIUnavailableError("Local AI runtime is unavailable.") from error

        if not runtime_online:
            raise LocalAIUnavailableError("Local AI runtime is unavailable.")
        if not model_available:
            raise LocalAIUnavailableError("Local AI model is unavailable.")

    def _start_telemetry_session(self) -> InferenceTelemetrySession | None:
        if self._telemetry_provider is None:
            return None
        try:
            return self._telemetry_provider.start_inference_session()
        except Exception:
            return None
