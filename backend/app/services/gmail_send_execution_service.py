"""D88 owner-controlled Gmail send execution orchestration.

Authority order is fixed:
D87 approved snapshot -> D36 authorization -> D88 atomic claim ->
credential resolution inside the private ModuleAdapter -> at most one provider
attempt -> terminal succeeded/failed/indeterminate outcome.

No retry, resend, claim release, Chat routing, or Automation routing exists here.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts.command import Result
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.gmail_send_execution import (
    GmailSendExecutionOutcome,
    validate_send_digest,
    validate_sender,
)
from app.services.execution_guard import ExecutionGuard
from app.services.gmail_send_approval import (
    GmailSendApprovalDigestMismatchError,
    GmailSendApprovalError,
    GmailSendApprovalExpiredError,
    GmailSendApprovalNotApprovedError,
    GmailSendApprovalStore,
)
from app.services.gmail_send_execution import (
    GmailSendExecutionClaimStore,
    GmailSendExecutionError,
    GmailSendExecutionExpiredError,
    build_gmail_send_execution_plan,
)
from app.services.module_runtime import ModuleRuntime


class GmailSendExecutionNotApprovedError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_not_approved"


class GmailSendExecutionDigestMismatchError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_digest_mismatch"


class GmailSendExecutionAuthorizationError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_authorization_failed"


class GmailSendExecutionSenderNotConfiguredError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_sender_not_configured"


class GmailSendExecutionDisabledError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_disabled"


class GmailSendExecutionService:
    """Execute one exact approved Gmail send with one-shot authority."""

    def __init__(
        self,
        *,
        approval_store: GmailSendApprovalStore,
        execution_store: GmailSendExecutionClaimStore,
        guard: ExecutionGuard,
        runtime: ModuleRuntime,
        sender: str | None,
        enabled: bool,
    ) -> None:
        if not isinstance(approval_store, GmailSendApprovalStore):
            raise TypeError("approval_store must be a GmailSendApprovalStore.")
        if not isinstance(execution_store, GmailSendExecutionClaimStore):
            raise TypeError(
                "execution_store must be a GmailSendExecutionClaimStore."
            )
        if not isinstance(guard, ExecutionGuard):
            raise TypeError("guard must be an ExecutionGuard.")
        if not isinstance(runtime, ModuleRuntime):
            raise TypeError("runtime must be a ModuleRuntime.")
        if type(enabled) is not bool:
            raise TypeError("enabled must be bool.")

        self._approval_store = approval_store
        self._execution_store = execution_store
        self._guard = guard
        self._runtime = runtime
        self._sender = sender
        self._enabled = enabled

    def execute(
        self,
        approval_id: str,
        send_digest: str,
    ) -> GmailSendExecutionOutcome:
        if not self._enabled:
            raise GmailSendExecutionDisabledError(
                "Gmail send execution is disabled."
            )

        try:
            sender = validate_sender(self._sender)
        except (TypeError, ValueError):
            raise GmailSendExecutionSenderNotConfiguredError(
                "Gmail send sender is not configured."
            ) from None

        if (
            not isinstance(approval_id, str)
            or not approval_id
            or approval_id != approval_id.strip()
        ):
            raise GmailSendExecutionNotApprovedError(
                "Gmail send approval is not approved."
            )

        try:
            send_digest = validate_send_digest(send_digest)
        except (TypeError, ValueError):
            raise GmailSendExecutionDigestMismatchError(
                "Gmail send digest does not match."
            ) from None

        try:
            approved = self._approval_store.get_approved(
                approval_id,
                send_digest,
            )
        except GmailSendApprovalExpiredError:
            raise GmailSendExecutionExpiredError(
                "Gmail send approval has expired."
            ) from None
        except GmailSendApprovalDigestMismatchError:
            raise GmailSendExecutionDigestMismatchError(
                "Gmail send digest does not match."
            ) from None
        except GmailSendApprovalNotApprovedError:
            raise GmailSendExecutionNotApprovedError(
                "Gmail send approval is not approved."
            ) from None
        except GmailSendApprovalError:
            raise GmailSendExecutionNotApprovedError(
                "Gmail send approval is not approved."
            ) from None

        command, planning, plan_digest = build_gmail_send_execution_plan(
            approved,
            sender=sender,
        )
        evidence = OwnerApprovalEvidence(
            request_id=approved.approval_id,
            plan_digest=plan_digest,
            decision="approved",
        )
        authorization = self._guard.authorize(
            command,
            planning,
            evidence,
        )
        if authorization.status != "authorized":
            raise GmailSendExecutionAuthorizationError(
                "Gmail send execution authorization failed."
            )

        claim = self._execution_store.claim(
            approved,
            sender=sender,
            plan_digest=plan_digest,
        )

        result = self._runtime.execute(command, authorization)
        outcome = self._to_outcome(
            approval_id=approved.approval_id,
            send_digest=approved.send_digest,
            result=result,
        )
        self._execution_store.complete(claim, outcome)
        return outcome

    @staticmethod
    def _to_outcome(
        *,
        approval_id: str,
        send_digest: str,
        result: object,
    ) -> GmailSendExecutionOutcome:
        if not isinstance(result, Result):
            return GmailSendExecutionOutcome(
                approval_id=approval_id,
                send_digest=send_digest,
                status="failed",
                reason_code="gmail_send_execution_error",
                provider_attempted=False,
            )

        attempted = (
            result.output.get("provider_attempted")
            if isinstance(result.output, Mapping)
            else False
        )
        provider_attempted = attempted if type(attempted) is bool else False

        if result.status == "succeeded":
            message_id = (
                result.output.get("message_id")
                if isinstance(result.output, Mapping)
                else None
            )
            try:
                return GmailSendExecutionOutcome(
                    approval_id=approval_id,
                    send_digest=send_digest,
                    status="succeeded",
                    reason_code="gmail_send_succeeded",
                    provider_attempted=True,
                    message_id=message_id,  # type: ignore[arg-type]
                )
            except (TypeError, ValueError):
                return GmailSendExecutionOutcome(
                    approval_id=approval_id,
                    send_digest=send_digest,
                    status="indeterminate",
                    reason_code="gmail_send_indeterminate",
                    provider_attempted=True,
                )

        if (
            result.error == "gmail_send_indeterminate"
            or (
                provider_attempted
                and result.error
                not in {
                    "gmail_send_provider_rejected",
                    "gmail_send_rate_limited",
                }
            )
        ):
            return GmailSendExecutionOutcome(
                approval_id=approval_id,
                send_digest=send_digest,
                status="indeterminate",
                reason_code="gmail_send_indeterminate",
                provider_attempted=True,
            )

        safe_reason = (
            result.error
            if result.error
            in {
                "gmail_send_credential_unavailable",
                "gmail_send_invalid_request",
                "gmail_send_provider_rejected",
                "gmail_send_rate_limited",
                "gmail_send_execution_parameters_invalid",
            }
            else "gmail_send_execution_error"
        )
        return GmailSendExecutionOutcome(
            approval_id=approval_id,
            send_digest=send_digest,
            status="failed",
            reason_code=safe_reason,
            provider_attempted=provider_attempted,
        )


__all__ = [
    "GmailSendExecutionAuthorizationError",
    "GmailSendExecutionDigestMismatchError",
    "GmailSendExecutionDisabledError",
    "GmailSendExecutionNotApprovedError",
    "GmailSendExecutionSenderNotConfiguredError",
    "GmailSendExecutionService",
]
