"""D88 deterministic Gmail send planning and one-shot execution claim store.

Batch 01 deliberately stops before D36 authorization, credential resolution,
network access, provider execution, or Gmail sending.
"""

from __future__ import annotations

import hmac
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.gmail_send import GMAIL_SEND_OPERATION
from app.contracts.gmail_send_approval import ApprovedGmailSendApproval
from app.contracts.gmail_send_execution import (
    GMAIL_SEND_ADAPTER_ID,
    GmailSendExecutionClaim,
    GmailSendExecutionOutcome,
    gmail_send_execution_parameters,
    gmail_send_request_from_parameters,
    validate_plan_digest,
    validate_sender,
)
from app.services.execution_guard import execution_plan_digest
from app.services.gmail_send_approval import (
    gmail_send_digest,
    gmail_send_preview,
)


DEFAULT_MAX_GMAIL_SEND_EXECUTION_RECORDS = 100


class GmailSendExecutionError(RuntimeError):
    reason_code = "gmail_send_execution_error"


class GmailSendExecutionIntegrityError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_integrity_failed"


class GmailSendExecutionExpiredError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_expired"


class GmailSendExecutionAlreadyClaimedError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_already_claimed"


class GmailSendExecutionStoreFullError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_store_full"


class GmailSendExecutionNotClaimedError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_not_claimed"


class GmailSendExecutionTerminalError(GmailSendExecutionError):
    reason_code = "gmail_send_execution_terminal"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise GmailSendExecutionIntegrityError(
            "Gmail send execution time must be timezone-aware."
        )
    return value.astimezone(timezone.utc)


def build_gmail_send_execution_plan(
    approved: ApprovedGmailSendApproval,
    *,
    sender: str,
) -> tuple[CommandRequest, ExecutionPlanningOutcome, str]:
    """Build and self-check one deterministic private D88 Module plan."""
    if not isinstance(approved, ApprovedGmailSendApproval):
        raise GmailSendExecutionIntegrityError(
            "Gmail send approval snapshot is invalid."
        )

    sender = validate_sender(sender)
    recomputed = gmail_send_digest(approved.request)
    if not hmac.compare_digest(recomputed, approved.send_digest):
        raise GmailSendExecutionIntegrityError(
            "Gmail send approval digest is invalid."
        )
    if gmail_send_preview(approved.request) != approved.preview:
        raise GmailSendExecutionIntegrityError(
            "Gmail send approval preview is invalid."
        )

    parameters = gmail_send_execution_parameters(
        approved.request,
        approved.send_digest,
        sender=sender,
    )
    reconstructed, reconstructed_digest, reconstructed_sender = (
        gmail_send_request_from_parameters(parameters)
    )
    if (
        reconstructed != approved.request
        or not hmac.compare_digest(
            reconstructed_digest,
            approved.send_digest,
        )
        or reconstructed_sender != sender
    ):
        raise GmailSendExecutionIntegrityError(
            "Gmail send execution projection is not exact."
        )

    command = CommandRequest(
        request_id=approved.approval_id,
        command="module.execute",
        arguments={
            "adapter_id": GMAIL_SEND_ADAPTER_ID,
            "operation": GMAIL_SEND_OPERATION,
            "parameters": parameters,
        },
    )
    plan = ExecutionPlan(
        request_id=approved.approval_id,
        adapter_id=GMAIL_SEND_ADAPTER_ID,
        steps=(
            ExecutionStep(
                sequence=1,
                operation=GMAIL_SEND_OPERATION,
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
        reason_code="gmail_send_execution_planned",
    )
    plan_digest = execution_plan_digest(plan)
    if hmac.compare_digest(plan_digest, approved.send_digest):
        raise GmailSendExecutionIntegrityError(
            "Send digest and execution-plan digest domains must remain distinct."
        )
    return command, planning, plan_digest


@dataclass(slots=True)
class _GmailSendExecutionRecord:
    claim: GmailSendExecutionClaim
    state: Literal["claimed", "succeeded", "failed", "indeterminate"] = "claimed"
    outcome: GmailSendExecutionOutcome | None = None


class GmailSendExecutionClaimStore:
    """Thread-safe bounded one-shot D88 execution claim store."""

    def __init__(
        self,
        *,
        max_records: int = DEFAULT_MAX_GMAIL_SEND_EXECUTION_RECORDS,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
        ):
            raise ValueError("max_records must be a positive integer.")
        self._max_records = max_records
        self._clock = clock
        self._items: dict[str, _GmailSendExecutionRecord] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        with self._lock:
            return len(self._items)

    def claim(
        self,
        approved: ApprovedGmailSendApproval,
        *,
        sender: str,
        plan_digest: str,
    ) -> GmailSendExecutionClaim:
        """Atomically consume one exact approved snapshot for execution."""
        if not isinstance(approved, ApprovedGmailSendApproval):
            raise GmailSendExecutionIntegrityError(
                "Gmail send approval snapshot is invalid."
            )
        sender = validate_sender(sender)
        plan_digest = validate_plan_digest(plan_digest)

        now = _aware_utc(self._clock())
        expires_at = _aware_utc(approved.expires_at)
        if now >= expires_at:
            raise GmailSendExecutionExpiredError(
                "Gmail send approval has expired."
            )

        recomputed_send_digest = gmail_send_digest(approved.request)
        if not hmac.compare_digest(
            recomputed_send_digest,
            approved.send_digest,
        ):
            raise GmailSendExecutionIntegrityError(
                "Gmail send approval digest is invalid."
            )

        _, planning, expected_plan_digest = build_gmail_send_execution_plan(
            approved,
            sender=sender,
        )
        if (
            planning.plan is None
            or not hmac.compare_digest(
                expected_plan_digest,
                plan_digest,
            )
        ):
            raise GmailSendExecutionIntegrityError(
                "Gmail send execution plan digest is invalid."
            )

        claim = GmailSendExecutionClaim(
            approval_id=approved.approval_id,
            send_digest=approved.send_digest,
            plan_digest=plan_digest,
            sender=sender,
        )

        with self._lock:
            # Recheck expiry at the atomic claim point.
            if _aware_utc(self._clock()) >= expires_at:
                raise GmailSendExecutionExpiredError(
                    "Gmail send approval has expired."
                )
            if approved.approval_id in self._items:
                raise GmailSendExecutionAlreadyClaimedError(
                    "Gmail send approval was already claimed."
                )
            if len(self._items) >= self._max_records:
                raise GmailSendExecutionStoreFullError(
                    "Gmail send execution capacity is full."
                )
            self._items[approved.approval_id] = _GmailSendExecutionRecord(
                claim=claim
            )
            return claim

    def complete(
        self,
        claim: GmailSendExecutionClaim,
        outcome: GmailSendExecutionOutcome,
    ) -> GmailSendExecutionOutcome:
        """Record one terminal result; never releases execution authority."""
        if not isinstance(claim, GmailSendExecutionClaim):
            raise GmailSendExecutionIntegrityError(
                "Gmail send execution claim is invalid."
            )
        if not isinstance(outcome, GmailSendExecutionOutcome):
            raise GmailSendExecutionIntegrityError(
                "Gmail send execution outcome is invalid."
            )
        if (
            outcome.approval_id != claim.approval_id
            or not hmac.compare_digest(
                outcome.send_digest,
                claim.send_digest,
            )
        ):
            raise GmailSendExecutionIntegrityError(
                "Gmail send execution outcome does not match the claim."
            )

        with self._lock:
            record = self._items.get(claim.approval_id)
            if record is None:
                raise GmailSendExecutionNotClaimedError(
                    "Gmail send execution was not claimed."
                )
            if record.claim != claim:
                raise GmailSendExecutionIntegrityError(
                    "Gmail send execution claim changed."
                )
            if record.state != "claimed" or record.outcome is not None:
                raise GmailSendExecutionTerminalError(
                    "Gmail send execution is already terminal."
                )
            record.state = outcome.status
            record.outcome = outcome
            return outcome

    def state(
        self,
        approval_id: str,
    ) -> Literal["claimed", "succeeded", "failed", "indeterminate"]:
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise GmailSendExecutionNotClaimedError(
                    "Gmail send execution was not claimed."
                )
            return record.state


__all__ = [
    "DEFAULT_MAX_GMAIL_SEND_EXECUTION_RECORDS",
    "GmailSendExecutionAlreadyClaimedError",
    "GmailSendExecutionClaimStore",
    "GmailSendExecutionError",
    "GmailSendExecutionExpiredError",
    "GmailSendExecutionIntegrityError",
    "GmailSendExecutionNotClaimedError",
    "GmailSendExecutionStoreFullError",
    "GmailSendExecutionTerminalError",
    "build_gmail_send_execution_plan",
]
