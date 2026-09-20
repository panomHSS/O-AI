"""D103 provider-neutral exact configured-model control service."""

from __future__ import annotations

from app.contracts.local_ai_control import LocalAIControlOperation
from app.contracts.local_ai_runtime import LocalAIModelControlProvider


class LocalAIModelControlError(RuntimeError):
    """Base class for safe D103 control-service errors."""

    reason_code = "local_ai_model_control_error"


class LocalAIModelControlUnsupportedError(LocalAIModelControlError):
    """Raised when the configured runtime lacks explicit control capability."""

    reason_code = "local_ai_model_control_unsupported"


class LocalAIModelControlOperationInvalidError(LocalAIModelControlError):
    """Raised when a caller requests an operation outside the frozen D103 set."""

    reason_code = "local_ai_model_control_operation_invalid"


class LocalAIModelControlService:
    """Dispatch one exact configured-model control mutation with no fallback."""

    def __init__(
        self,
        *,
        provider: object,
        configured_model_id: str,
    ) -> None:
        if (
            not isinstance(configured_model_id, str)
            or not configured_model_id
            or configured_model_id != configured_model_id.strip()
        ):
            raise ValueError(
                "configured_model_id must be a non-empty trimmed string."
            )
        if not isinstance(provider, LocalAIModelControlProvider):
            raise LocalAIModelControlUnsupportedError(
                "Configured Local AI runtime does not support model control."
            )
        self._provider = provider
        self._configured_model_id = configured_model_id

    @property
    def configured_model_id(self) -> str:
        return self._configured_model_id

    def dispatch(self, operation: LocalAIControlOperation) -> None:
        """Perform at most one exact provider mutation attempt; never retry."""
        if operation == "load_configured_model":
            self._provider.load_model(self._configured_model_id)
            return
        if operation == "unload_configured_model":
            self._provider.unload_model(self._configured_model_id)
            return
        raise LocalAIModelControlOperationInvalidError(
            "Unsupported Local AI model control operation."
        )


__all__ = [
    "LocalAIModelControlError",
    "LocalAIModelControlOperationInvalidError",
    "LocalAIModelControlService",
    "LocalAIModelControlUnsupportedError",
]
