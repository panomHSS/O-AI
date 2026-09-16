"""D74 approval-bound private Calendar create authorization and execution."""

from __future__ import annotations

import hmac

from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.google_calendar_create_execution import (
    CalendarCreateExecutionOutcome,
    GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
    calendar_create_execution_parameters,
    calendar_create_request_from_parameters,
)
from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
    GoogleCalendarCreateEventRequest,
    GoogleCalendarEventTarget,
)
from app.contracts.google_calendar_write_approval import ApprovedCalendarWriteApproval
from app.services.calendar_write_approval import CalendarWriteApprovalStore, calendar_write_digest
from app.services.execution_guard import ExecutionGuard, execution_plan_digest
from app.services.module_runtime import ModuleRuntime

CALENDAR_CREATE_ERROR_OPERATION_NOT_ALLOWED = "calendar_create_operation_not_allowed"
CALENDAR_CREATE_ERROR_APPROVAL_INTEGRITY = "calendar_create_approval_integrity_failed"
CALENDAR_CREATE_ERROR_AUTHORIZATION = "calendar_create_authorization_failed"
CALENDAR_CREATE_ERROR_EXECUTION_FAILED = "calendar_create_execution_failed"
CALENDAR_CREATE_ERROR_INDETERMINATE = "calendar_create_indeterminate"


class CalendarCreateExecutionError(RuntimeError):
    reason_code = CALENDAR_CREATE_ERROR_EXECUTION_FAILED


class CalendarCreateExecutionOperationError(CalendarCreateExecutionError):
    reason_code = CALENDAR_CREATE_ERROR_OPERATION_NOT_ALLOWED


class CalendarCreateExecutionIntegrityError(CalendarCreateExecutionError):
    reason_code = CALENDAR_CREATE_ERROR_APPROVAL_INTEGRITY


class CalendarCreateExecutionAuthorizationError(CalendarCreateExecutionError):
    reason_code = CALENDAR_CREATE_ERROR_AUTHORIZATION


def build_calendar_create_execution_plan(
    approved: ApprovedCalendarWriteApproval,
) -> tuple[CommandRequest, ExecutionPlanningOutcome, str]:
    """Build and self-check one deterministic private D74 Module plan."""
    if not isinstance(approved, ApprovedCalendarWriteApproval):
        raise CalendarCreateExecutionIntegrityError("Calendar write approval snapshot is invalid.")
    if not isinstance(approved.request, GoogleCalendarCreateEventRequest):
        raise CalendarCreateExecutionOperationError("Only D72 create_event approvals are executable in D74.")
    recomputed = calendar_write_digest(approved.request)
    if not hmac.compare_digest(recomputed, approved.write_digest):
        raise CalendarCreateExecutionIntegrityError("Calendar write approval digest is invalid.")
    parameters = calendar_create_execution_parameters(approved.request, approved.write_digest)
    reconstructed, reconstructed_digest = calendar_create_request_from_parameters(parameters)
    if reconstructed != approved.request or not hmac.compare_digest(reconstructed_digest, approved.write_digest):
        raise CalendarCreateExecutionIntegrityError("Calendar create execution projection is not exact.")

    command = CommandRequest(
        request_id=approved.approval_id,
        command="module.execute",
        arguments={
            "adapter_id": GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
            "operation": GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
            "parameters": parameters,
        },
    )
    plan = ExecutionPlan(
        request_id=approved.approval_id,
        adapter_id=GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
        steps=(ExecutionStep(sequence=1, operation=GOOGLE_CALENDAR_CREATE_EVENT_OPERATION, parameters=parameters),),
        owner_approval_required=True,
    )
    planning = ExecutionPlanningOutcome(
        request_id=approved.approval_id,
        status="planned",
        target_kind="module",
        plan=plan,
        reason_code="calendar_create_execution_planned",
    )
    digest = execution_plan_digest(plan)
    if hmac.compare_digest(digest, approved.write_digest):
        raise CalendarCreateExecutionIntegrityError("Write digest and execution-plan digest domains must remain distinct.")
    return command, planning, digest


class CalendarCreateExecutionService:
    """Authorize, atomically claim, then execute one exact approved create."""

    def __init__(self, *, approval_store: CalendarWriteApprovalStore, guard: ExecutionGuard, runtime: ModuleRuntime) -> None:
        if not isinstance(approval_store, CalendarWriteApprovalStore):
            raise TypeError("approval_store must be CalendarWriteApprovalStore.")
        if not isinstance(guard, ExecutionGuard):
            raise TypeError("guard must be ExecutionGuard.")
        if not isinstance(runtime, ModuleRuntime):
            raise TypeError("runtime must be ModuleRuntime.")
        self._approval_store = approval_store
        self._guard = guard
        self._runtime = runtime

    def execute_create(self, approval_id: str, write_digest: str) -> CalendarCreateExecutionOutcome:
        approved = self._approval_store.get_approved(approval_id, write_digest)
        command, planning, plan_digest = build_calendar_create_execution_plan(approved)
        evidence = OwnerApprovalEvidence(
            request_id=approved.approval_id,
            plan_digest=plan_digest,
            decision="approved",
        )
        authorization = self._guard.authorize(command, planning, evidence)
        if authorization.status != "authorized":
            raise CalendarCreateExecutionAuthorizationError("Calendar create authorization failed.")
        claimed = self._approval_store.claim_approved(approval_id, write_digest)
        if claimed != approved:
            raise CalendarCreateExecutionIntegrityError("Claimed Calendar approval snapshot changed.")

        result = self._runtime.execute(command, authorization)
        if result.status == "succeeded":
            try:
                target = GoogleCalendarEventTarget(event_id=result.output.get("event_id"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return CalendarCreateExecutionOutcome(
                    approval_id=approval_id,
                    write_digest=write_digest,
                    status="indeterminate",
                    reason_code=CALENDAR_CREATE_ERROR_INDETERMINATE,
                )
            return CalendarCreateExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="succeeded",
                reason_code="calendar_create_succeeded",
                event_id=target.event_id,
            )
        if result.error == CALENDAR_CREATE_ERROR_INDETERMINATE:
            return CalendarCreateExecutionOutcome(
                approval_id=approval_id,
                write_digest=write_digest,
                status="indeterminate",
                reason_code=CALENDAR_CREATE_ERROR_INDETERMINATE,
            )
        safe_reason = result.error if result.error in {
            "calendar_create_credential_unavailable",
            "calendar_create_provider_rejected",
            "calendar_create_invalid_request",
            "calendar_create_parameters_invalid",
        } else CALENDAR_CREATE_ERROR_EXECUTION_FAILED
        return CalendarCreateExecutionOutcome(
            approval_id=approval_id,
            write_digest=write_digest,
            status="failed",
            reason_code=safe_reason,
        )


__all__ = [
    "CalendarCreateExecutionError",
    "CalendarCreateExecutionOperationError",
    "CalendarCreateExecutionIntegrityError",
    "CalendarCreateExecutionAuthorizationError",
    "CalendarCreateExecutionService",
    "build_calendar_create_execution_plan",
]
