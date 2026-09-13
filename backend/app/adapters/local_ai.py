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


class MetricsCollector(Protocol):
    """Optional telemetry boundary kept separate from inference behavior."""

    def collect(self) -> object:
        """Collect best-effort host metrics."""
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
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self._runtime_client = runtime_client
        self._enabled = enabled
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._context_length = context_length
        self._metrics_collector = metrics_collector

    def generate(self, request: AIRequest) -> AIResult:
        """Generate locally after fail-closed runtime and model checks."""
        try:
            self._require_available()
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
            self._collect_metrics_safely()

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

    def _collect_metrics_safely(self) -> None:
        if self._metrics_collector is None:
            return
        try:
            self._metrics_collector.collect()
        except Exception:
            return
