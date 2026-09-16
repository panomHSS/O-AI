"""D75 approval-bound private Calendar update/delete authorization and execution."""

from __future__ import annotations

import hmac

from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.google_calendar_update_delete_execution import (
    CalendarDeleteExecutionOutcome,
    CalendarUpdateExecutionOutcome,
    GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
    GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
    calendar_delete_execution_parameters,
    calendar_delete_request_from_parameters,
    calendar_update_execution_parameters,
    calendar_update_request_from_parameters,
)
from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
    GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.google_calendar_write_approval import ApprovedCalendarWriteApproval
from app.services.calendar_write_approval import (
    CalendarWriteApprovalStore,
    calendar_write_digest,
)
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.module_runtime import ModuleRuntime

CALENDAR_UPDATE_ERROR_OPERATION_NOT_ALLOWED = "calendar_update_operation_not_allowed"
CALENDAR_UPDATE_ERROR_APPROVAL_INTEGRITY = "calendar_update_approval_integrity_failed"
CALENDAR_UPDATE_ERROR_AUTHORIZATION = "calendar_update_authorization_failed"
CALENDAR_UPDATE_ERROR_EXECUTION_FAILED = "calendar_update_execution_failed"
CALENDAR_UPDATE_ERROR_INDETERMINATE = "calendar_update_indeterminate"

CALENDAR_DELETE_ERROR_OPERATION_NOT_ALLOWED = "calendar_delete_operation_not_allowed"
CALENDAR_DELETE_ERROR_APPROVAL_INTEGRITY = "calendar_delete_approval_integrity_failed"
CALENDAR_DELETE_ERROR_AUTHORIZATION = "calendar_delete_authorization_failed"
CALENDAR_DELETE_ERROR_EXECUTION_FAILED = "calendar_delete_execution_failed"
CALENDAR_DELETE_ERROR_INDETERMINATE = "calendar_delete_indeterminate"


class CalendarUpdateExecutionError(RuntimeError):
    reason_code = CALENDAR_UPDATE_ERROR_EXECUTION_FAILED


class CalendarUpdateExecutionOperationError(CalendarUpdateExecutionError):
    reason_code = CALENDAR_UPDATE_ERROR_OPERATION_NOT_ALLOWED


class CalendarUpdateExecutionIntegrityError(CalendarUpdateExecutionError):
    reason_code = CALENDAR_UPDATE_ERROR_APPROVAL_INTEGRITY


class CalendarUpdateExecutionAuthorizationError(CalendarUpdateExecutionError):
    reason_code = CALENDAR_UPDATE_ERROR_AUTHORIZATION


class CalendarDeleteExecutionError(RuntimeError):
    reason_code = CALENDAR_DELETE_ERROR_EXECUTION_FAILED


class CalendarDeleteExecutionOperationError(CalendarDeleteExecutionError):
    reason_code = CALENDAR_DELETE_ERROR_OPERATION_NOT_ALLOWED


class CalendarDeleteExecutionIntegrityError(CalendarDeleteExecutionError):
    reason_code = CALENDAR_DELETE_ERROR_APPROVAL_INTEGRITY


class CalendarDeleteExecutionAuthorizationError(CalendarDeleteExecutionError):
    reason_code = CALENDAR_DELETE_ERROR_AUTHORIZATION


def build_calendar_update_execution_plan(
    approved: ApprovedCalendarWriteApproval,
) -> tuple[CommandRequest, ExecutionPlanningOutcome, str]:
    """Build and self-check one deterministic private D75 update plan."""
    if not isinstance(approved, ApprovedCalendarWriteApproval):
        raise CalendarUpdateExecutionIntegrityError(
            "Calendar write approval snapshot is invalid."
        )
    if not isinstance(approved.request, GoogleCalendarUpdateEventRequest):
        raise CalendarUpdateExecutionOperationError(
            "Only D72 update_event approvals are executable in this D75 lane."
        )
    recomputed = calendar_write_digest(approved.request)
    if not hmac.compare_digest(recomputed, approved.write_digest):
        raise CalendarUpdateExecutionIntegrityError(
            "Calendar update approval digest is invalid."
        )
    parameters = calendar_update_execution_parameters(
        approved.request,
        approved.write_digest,
    )
    reconstructed, reconstructed_digest = calendar_update_request_from_parameters(
        parameters
    )
    if (
        reconstructed != approved.request
        or not hmac.compare_digest(reconstructed_digest, approved.write_digest)
    ):
        raise CalendarUpdateExecutionIntegrityError(
            "Calendar update execution projection is not exact."
        )

    command = CommandRequest(
        request_id=approved.approval_id,
        command="module.execute",
        arguments={
            "adapter_id": GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
            "operation": GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
            "parameters": parameters,
        },
    )
    plan = ExecutionPlan(
        request_id=approved.approval_id,
        adapter_id=GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
        steps=(
            ExecutionStep(
                sequence=1,
                operation=GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
                parameters=parameters,
            ),
        ),
        owner_approval_required=True,
    )
    planning = ExecutionPlanningOutcome(
        request_id=approved.approval_id,
        status="planned",
        target_kind="module",
        plan=plan,
        reason_code="calendar_update_execution_planned",
    )
    digest = execution_plan_digest(plan)
    if hmac.compare_digest(digest, approved.write_digest):
        raise CalendarUpdateExecutionIntegrityError(
            "Write digest and execution-plan digest domains must remain distinct."
        )
    return command, planning, digest


def build_calendar_delete_execution_plan(
    approved: ApprovedCalendarWriteApproval,
) -> tuple[CommandRequest, ExecutionPlanningOutcome, str]:
    """Build and self-check one deterministic private D75 delete plan."""
    if not isinstance(approved, ApprovedCalendarWriteApproval):
        raise CalendarDeleteExecutionIntegrityError(
            "Calendar write approval snapshot is invalid."
        )
    if not isinstance(approved.request, GoogleCalendarDeleteEventRequest):
        raise CalendarDeleteExecutionOperationError(
            "Only D72 delete_event approvals are executable in this D75 lane."
        )
    recomputed = calendar_write_digest(approved.request)
    if not hmac.compare_digest(recomputed, approved.write_digest):
        raise CalendarDeleteExecutionIntegrityError(
            "Calendar delete approval digest is invalid."
        )
    parameters = calendar_delete_execution_parameters(
        approved.request,
        approved.write_digest,
    )
    reconstructed, reconstructed_digest = calendar_delete_request_from_parameters(
        parameters
    )
    if (
        reconstructed != approved.request
        or not hmac.compare_digest(reconstructed_digest, approved.write_digest)
    ):
        raise CalendarDeleteExecutionIntegrityError(
            "Calendar delete execution projection is not exact."
        )

    command = CommandRequest(
        request_id=approved.approval_id,
        command="module.execute",
        arguments={
            "adapter_id": GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
            "operation": GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
            "parameters": parameters,
        },
    )
    plan = ExecutionPlan(
        request_id=approved.approval_id,
        adapter_id=GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
        steps=(
            ExecutionStep(
                sequence=1,
                operation=GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
                parameters=parameters,
            ),
        ),
        owner_approval_required=True,
    )
    planning = ExecutionPlanningOutcome(
        request_id=approved.approval_id,
        status="planned",
        target_kind="module",
        plan=plan,
        reason_code="calendar_delete_execution_planned",
    )
    digest = execution_plan_digest(plan)
    if hmac.compare_digest(digest, approved.write_digest):
        raise CalendarDeleteExecutionIntegrityError(
            "Write digest and execution-plan digest domains must remain distinct."
        )
    return command, planning, digest


class CalendarUpdateDeleteExecutionService:
    """Authorize, atomically claim, then execute one exact update or delete."""

    def __init__(
        self,
        *,
        approval_store: CalendarWriteApprovalStore,
        guard: ExecutionGuard,
        runtime: ModuleRuntime,
    ) -> None:
        if not isinstance(approval_store, CalendarWriteApprovalStore):
            raise TypeError("approval_store must be CalendarWriteApprovalStore.")
        if not isinstance(guard, ExecutionGuard):
            raise TypeError("guard must be ExecutionGuard.")
        if not isinstance(runtime, ModuleRuntime):
            raise TypeError("runtime must be ModuleRuntime.")
        self._approval_store = approval_store
        self._guard = guard
        self._runtime = runtime

    def execute_update(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarUpdateExecutionOutcome:
        approved = self._approval_store.get_approved(approval_id, write_digest)
        command, planning, plan_digest = build_calendar_update_execution_plan(
            approved
        )
        evidence = OwnerApprovalEvidence(
            request_id=approved.approval_id,
            plan_digest=plan_digest,
            decision="approved",
        )
        authorization = self._guard.authorize(command, planning, evidence)
        if authorization.status != "authorized":
            raise CalendarUpdateExecutionAuthorizationError(
                "Calendar update authorization failed."
            )
        claimed = self._approval_store.claim_approved(approval_id, write_digest)
        if claimed != approved:
            raise CalendarUpdateExecutionIntegrityError(
                "Claimed Calendar update approval snapshot changed."
            )
        assert isinstance(approved.request, GoogleCalendarUpdateEventRequest)

        result = self._runtime.execute(command, authorization)
        if result.status == "succeeded":
            try:
                target = GoogleCalendarEventTarget(
                    event_id=result.output.get("event_id")  # type: ignore[arg-type]
                )
            except (TypeError, ValueError):
                return self._update_indeterminate(approval_id, write_digest)
            if target != approved.request.target:
                return self._update_indeterminate(approval_id, write_digest)
            return CalendarUpdateExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="succeeded",
                reason_code="calendar_update_succeeded",
                event_id=target.event_id,
            )
        if result.error == CALENDAR_UPDATE_ERROR_INDETERMINATE:
            return self._update_indeterminate(approval_id, write_digest)
        safe_reason = (
            result.error
            if result.error
            in {
                "calendar_update_credential_unavailable",
                "calendar_update_provider_rejected",
                "calendar_update_invalid_request",
                "calendar_update_parameters_invalid",
            }
            else CALENDAR_UPDATE_ERROR_EXECUTION_FAILED
        )
        return CalendarUpdateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="failed",
            reason_code=safe_reason,
        )

    def execute_delete(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarDeleteExecutionOutcome:
        approved = self._approval_store.get_approved(approval_id, write_digest)
        command, planning, plan_digest = build_calendar_delete_execution_plan(
            approved
        )
        evidence = OwnerApprovalEvidence(
            request_id=approved.approval_id,
            plan_digest=plan_digest,
            decision="approved",
        )
        authorization = self._guard.authorize(command, planning, evidence)
        if authorization.status != "authorized":
            raise CalendarDeleteExecutionAuthorizationError(
                "Calendar delete authorization failed."
            )
        claimed = self._approval_store.claim_approved(approval_id, write_digest)
        if claimed != approved:
            raise CalendarDeleteExecutionIntegrityError(
                "Claimed Calendar delete approval snapshot changed."
            )
        assert isinstance(approved.request, GoogleCalendarDeleteEventRequest)

        result = self._runtime.execute(command, authorization)
        if result.status == "succeeded":
            try:
                target = GoogleCalendarEventTarget(
                    event_id=result.output.get("event_id")  # type: ignore[arg-type]
                )
            except (TypeError, ValueError):
                return self._delete_indeterminate(approval_id, write_digest)
            if target != approved.request.target:
                return self._delete_indeterminate(approval_id, write_digest)
            return CalendarDeleteExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="succeeded",
                reason_code="calendar_delete_succeeded",
            )
        if result.error == CALENDAR_DELETE_ERROR_INDETERMINATE:
            return self._delete_indeterminate(approval_id, write_digest)
        safe_reason = (
            result.error
            if result.error
            in {
                "calendar_delete_credential_unavailable",
                "calendar_delete_provider_rejected",
                "calendar_delete_invalid_request",
                "calendar_delete_parameters_invalid",
            }
            else CALENDAR_DELETE_ERROR_EXECUTION_FAILED
        )
        return CalendarDeleteExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="failed",
            reason_code=safe_reason,
        )

    @staticmethod
    def _update_indeterminate(
        approval_id: str,
        write_digest: str,
    ) -> CalendarUpdateExecutionOutcome:
        return CalendarUpdateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code=CALENDAR_UPDATE_ERROR_INDETERMINATE,
        )

    @staticmethod
    def _delete_indeterminate(
        approval_id: str,
        write_digest: str,
    ) -> CalendarDeleteExecutionOutcome:
        return CalendarDeleteExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="indeterminate",
            reason_code=CALENDAR_DELETE_ERROR_INDETERMINATE,
        )


__all__ = [
    "CalendarDeleteExecutionAuthorizationError",
    "CalendarDeleteExecutionError",
    "CalendarDeleteExecutionIntegrityError",
    "CalendarDeleteExecutionOperationError",
    "CalendarUpdateDeleteExecutionService",
    "CalendarUpdateExecutionAuthorizationError",
    "CalendarUpdateExecutionError",
    "CalendarUpdateExecutionIntegrityError",
    "CalendarUpdateExecutionOperationError",
    "build_calendar_delete_execution_plan",
    "build_calendar_update_execution_plan",
]
