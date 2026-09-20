"""D103 proposal, revalidation, one-time claim, and control execution."""

from __future__ import annotations

from app.contracts.local_ai_control import (
    LocalAIControlDecision,
    LocalAIControlExecutionOutcome,
    LocalAIControlOperation,
    LocalAIControlPreview,
    LocalAIControlProposalOutcome,
)
from app.contracts.local_ai_runtime import LocalAIModelControlProvider
from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_control_approval import (
    LocalAIControlApprovalService,
    LocalAIControlApprovalStore,
    local_ai_control_preview,
)
from app.services.local_ai_model_control import (
    LocalAIModelControlService,
    LocalAIModelControlUnsupportedError,
)
from app.services.local_ai_visibility import LocalAIRuntimeVisibilityService


class LocalAIControlExecutionError(RuntimeError):
    """Safe D103 pre-dispatch failure with one bounded reason code."""

    def __init__(self, reason_code: str) -> None:
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or reason_code != reason_code.strip()
        ):
            raise ValueError("reason_code must be a non-empty trimmed string.")
        self.reason_code = reason_code
        super().__init__("Local AI control request cannot proceed.")


class LocalAIControlExecutionService:
    """Server-owned D103 control orchestration with no retry or fallback."""

    def __init__(
        self,
        *,
        config: LocalAIAdapterConfig,
        runtime_client: object | None,
        visibility_service: LocalAIRuntimeVisibilityService,
        approval_service: LocalAIControlApprovalService,
        approval_store: LocalAIControlApprovalStore,
    ) -> None:
        if not isinstance(config, LocalAIAdapterConfig):
            raise TypeError("config must be LocalAIAdapterConfig.")
        if not isinstance(visibility_service, LocalAIRuntimeVisibilityService):
            raise TypeError(
                "visibility_service must be LocalAIRuntimeVisibilityService."
            )
        if not isinstance(approval_service, LocalAIControlApprovalService):
            raise TypeError(
                "approval_service must be LocalAIControlApprovalService."
            )
        if not isinstance(approval_store, LocalAIControlApprovalStore):
            raise TypeError("approval_store must be LocalAIControlApprovalStore.")
        self._config = config
        self._runtime_client = runtime_client
        self._visibility_service = visibility_service
        self._approval_service = approval_service
        self._approval_store = approval_store

    def propose(
        self,
        operation: LocalAIControlOperation,
    ) -> LocalAIControlProposalOutcome:
        """Create a proposal only from current server-owned configuration/state."""
        loaded = self._validate_environment(operation=operation)
        preview = local_ai_control_preview(
            operation=operation,
            backend_id=self._config.backend_id,
            configured_model_id=self._config.model,
            expected_loaded_state=loaded,
        )
        return self._approval_service.propose(preview)

    def decide(
        self,
        proposal_id: str,
        *,
        decision: LocalAIControlDecision,
        control_digest: str,
    ) -> LocalAIControlExecutionOutcome:
        """Apply one terminal owner decision; approved paths may mutate once."""
        if decision == "denied":
            denied = self._approval_service.deny(
                proposal_id,
                control_digest,
            )
            return LocalAIControlExecutionOutcome(
                approval_id=denied.approval_id,
                decision="denied",
                status="not_executed",
                reason_code="owner_denied",
                control_digest=denied.control_digest,
                preview=denied.preview,
                expires_at=denied.expires_at,
            )
        if decision != "approved":
            raise LocalAIControlExecutionError(
                "local_ai_control_decision_invalid"
            )

        approved = self._approval_service.approve(
            proposal_id,
            control_digest,
        )
        snapshot = approved.preview

        try:
            self._revalidate_approved_snapshot(snapshot)
            control_service = LocalAIModelControlService(
                provider=self._runtime_client,
                configured_model_id=self._config.model,
            )
        except (
            LocalAIControlExecutionError,
            LocalAIModelControlUnsupportedError,
        ) as error:
            reason_code = getattr(
                error,
                "reason_code",
                "local_ai_model_control_unsupported",
            )
            return self._approved_outcome(
                approved,
                status="failed",
                reason_code=reason_code,
            )

        self._approval_store.claim_approved(
            approved.approval_id,
            approved.control_digest,
        )

        try:
            control_service.dispatch(snapshot.operation)
        except Exception:
            # Once dispatch is attempted, provider/network failures may be
            # ambiguous. D103 intentionally performs no automatic retry.
            return self._approved_outcome(
                approved,
                status="indeterminate",
                reason_code="local_ai_control_indeterminate",
            )

        visibility = self._visibility_service.get_visibility()
        if (
            visibility.enabled
            and visibility.backend_id == snapshot.backend_id
            and visibility.configured_model_id
            == snapshot.configured_model_id
            and visibility.runtime_status == "online"
            and visibility.configured_model_installed is True
            and visibility.configured_model_loaded
            is snapshot.desired_loaded_state
        ):
            return self._approved_outcome(
                approved,
                status="succeeded",
                reason_code="local_ai_control_succeeded",
            )

        return self._approved_outcome(
            approved,
            status="indeterminate",
            reason_code="local_ai_control_indeterminate",
        )

    def _validate_environment(
        self,
        *,
        operation: LocalAIControlOperation,
    ) -> bool:
        if operation not in {
            "load_configured_model",
            "unload_configured_model",
        }:
            raise LocalAIControlExecutionError(
                "local_ai_control_operation_invalid"
            )
        if not self._config.enabled:
            raise LocalAIControlExecutionError("local_ai_control_disabled")
        if self._runtime_client is None:
            raise LocalAIControlExecutionError(
                "local_ai_control_runtime_unavailable"
            )
        if not isinstance(
            self._runtime_client,
            LocalAIModelControlProvider,
        ):
            raise LocalAIControlExecutionError(
                "local_ai_model_control_unsupported"
            )

        visibility = self._visibility_service.get_visibility()
        if visibility.runtime_status != "online":
            raise LocalAIControlExecutionError(
                "local_ai_control_runtime_unavailable"
            )
        if (
            visibility.backend_id != self._config.backend_id
            or visibility.configured_model_id != self._config.model
        ):
            raise LocalAIControlExecutionError(
                "local_ai_control_configuration_changed"
            )
        if visibility.configured_model_installed is not True:
            if visibility.configured_model_installed is False:
                raise LocalAIControlExecutionError(
                    "local_ai_control_model_missing"
                )
            raise LocalAIControlExecutionError(
                "local_ai_control_model_state_unavailable"
            )

        loaded = visibility.configured_model_loaded
        if type(loaded) is not bool:
            raise LocalAIControlExecutionError(
                "local_ai_control_loaded_state_unknown"
            )
        expected = operation == "unload_configured_model"
        if loaded is not expected:
            raise LocalAIControlExecutionError(
                "local_ai_control_state_conflict"
            )
        return loaded

    def _revalidate_approved_snapshot(
        self,
        snapshot: LocalAIControlPreview,
    ) -> None:
        if (
            snapshot.backend_id != self._config.backend_id
            or snapshot.configured_model_id != self._config.model
        ):
            raise LocalAIControlExecutionError(
                "local_ai_control_configuration_changed"
            )

        loaded = self._validate_environment(
            operation=snapshot.operation,
        )
        if loaded is not snapshot.expected_loaded_state:
            raise LocalAIControlExecutionError(
                "local_ai_control_state_changed"
            )

    @staticmethod
    def _approved_outcome(
        approved: object,
        *,
        status: str,
        reason_code: str,
    ) -> LocalAIControlExecutionOutcome:
        return LocalAIControlExecutionOutcome(
            approval_id=approved.approval_id,  # type: ignore[attr-defined]
            decision="approved",
            status=status,  # type: ignore[arg-type]
            reason_code=reason_code,
            control_digest=approved.control_digest,  # type: ignore[attr-defined]
            preview=approved.preview,  # type: ignore[attr-defined]
            expires_at=approved.expires_at,  # type: ignore[attr-defined]
        )


__all__ = [
    "LocalAIControlExecutionError",
    "LocalAIControlExecutionService",
]
