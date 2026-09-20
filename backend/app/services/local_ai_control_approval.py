"""D103 configured-model control proposal, digest, approval, and claim boundary."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.contracts.local_ai_control import (
    ApprovedLocalAIControlApproval,
    LOCAL_AI_CONTROL_CONTRACT_VERSION,
    LocalAIControlDecisionOutcome,
    LocalAIControlOperation,
    LocalAIControlPreview,
    LocalAIControlProposal,
    LocalAIControlProposalOutcome,
    PendingLocalAIControlApproval,
)

DEFAULT_LOCAL_AI_CONTROL_APPROVAL_TTL = timedelta(minutes=10)
DEFAULT_MAX_LOCAL_AI_CONTROL_APPROVAL_RECORDS = 128


class LocalAIControlApprovalError(RuntimeError):
    reason_code = "local_ai_control_approval_error"


class LocalAIControlApprovalNotPendingError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_not_pending"


class LocalAIControlApprovalNotApprovedError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_not_approved"


class LocalAIControlApprovalAlreadyClaimedError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_already_claimed"


class LocalAIControlApprovalExpiredError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_expired"


class LocalAIControlApprovalDigestMismatchError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_digest_mismatch"


class LocalAIControlApprovalStoreFullError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_store_full"


class LocalAIControlApprovalProposalInvalidError(LocalAIControlApprovalError):
    reason_code = "local_ai_control_approval_proposal_invalid"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_approval_id() -> str:
    return secrets.token_urlsafe(32)


def local_ai_control_preview(
    *,
    operation: LocalAIControlOperation,
    backend_id: str,
    configured_model_id: str,
    expected_loaded_state: bool,
) -> LocalAIControlPreview:
    if operation == "load_configured_model":
        desired = True
    elif operation == "unload_configured_model":
        desired = False
    else:
        raise LocalAIControlApprovalProposalInvalidError("Unsupported operation.")
    try:
        return LocalAIControlPreview(
            contract_version=LOCAL_AI_CONTROL_CONTRACT_VERSION,
            operation=operation,
            backend_id=backend_id,
            configured_model_id=configured_model_id,
            expected_loaded_state=expected_loaded_state,
            desired_loaded_state=desired,
        )
    except (TypeError, ValueError) as error:
        raise LocalAIControlApprovalProposalInvalidError("Invalid control preview.") from error


def local_ai_control_projection(preview: LocalAIControlPreview) -> dict[str, object]:
    if not isinstance(preview, LocalAIControlPreview):
        raise LocalAIControlApprovalProposalInvalidError("Invalid control preview.")
    return {
        "contract_version": preview.contract_version,
        "operation": preview.operation,
        "backend_id": preview.backend_id,
        "configured_model_id": preview.configured_model_id,
        "expected_loaded_state": preview.expected_loaded_state,
        "desired_loaded_state": preview.desired_loaded_state,
    }


def local_ai_control_digest(preview: LocalAIControlPreview) -> str:
    payload = json.dumps(
        local_ai_control_projection(preview),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(slots=True)
class _Record:
    pending: PendingLocalAIControlApproval
    state: Literal["pending", "approved", "denied", "claimed"] = "pending"
    approved: ApprovedLocalAIControlApproval | None = None


class LocalAIControlApprovalStore:
    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_LOCAL_AI_CONTROL_APPROVAL_TTL,
        max_records: int = DEFAULT_MAX_LOCAL_AI_CONTROL_APPROVAL_RECORDS,
        clock: Callable[[], datetime] = _utcnow,
        approval_id_factory: Callable[[], str] = _new_approval_id,
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive.")
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1:
            raise ValueError("max_records must be positive integer.")
        self._ttl = ttl
        self._max_records = max_records
        self._clock = clock
        self._approval_id_factory = approval_id_factory
        self._items: dict[str, _Record] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def create(self, *, preview: LocalAIControlPreview, control_digest: str) -> PendingLocalAIControlApproval:
        now = self._clock()
        with self._lock:
            self._cleanup(now)
            if len(self._items) >= self._max_records:
                raise LocalAIControlApprovalStoreFullError("Control approval store is full.")
            approval_id = None
            for _ in range(4):
                candidate = self._approval_id_factory()
                if isinstance(candidate, str) and candidate and candidate == candidate.strip() and candidate not in self._items:
                    approval_id = candidate
                    break
            if approval_id is None:
                raise LocalAIControlApprovalProposalInvalidError("Could not allocate approval ID.")
            pending = PendingLocalAIControlApproval(
                approval_id=approval_id,
                control_digest=control_digest,
                preview=preview,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._items[approval_id] = _Record(pending=pending)
            return pending

    def approve(self, approval_id: str, control_digest: str) -> ApprovedLocalAIControlApproval:
        now = self._clock()
        with self._lock:
            record = self._pending(approval_id, control_digest, now)
            approved = ApprovedLocalAIControlApproval(
                approval_id=record.pending.approval_id,
                control_digest=record.pending.control_digest,
                preview=record.pending.preview,
                approved_at=now,
                expires_at=record.pending.expires_at,
            )
            record.state = "approved"
            record.approved = approved
            return approved

    def deny(self, approval_id: str, control_digest: str) -> PendingLocalAIControlApproval:
        now = self._clock()
        with self._lock:
            record = self._pending(approval_id, control_digest, now)
            record.state = "denied"
            return record.pending

    def get_approved(self, approval_id: str, control_digest: str) -> ApprovedLocalAIControlApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise LocalAIControlApprovalNotApprovedError("Approval is not approved.")
            self._validate_live(record, approval_id, control_digest, now)
            if record.state != "approved" or record.approved is None:
                raise LocalAIControlApprovalNotApprovedError("Approval is not approved.")
            return record.approved

    def claim_approved(self, approval_id: str, control_digest: str) -> ApprovedLocalAIControlApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise LocalAIControlApprovalNotApprovedError("Approval is not approved.")
            self._validate_live(record, approval_id, control_digest, now)
            if record.state == "claimed":
                raise LocalAIControlApprovalAlreadyClaimedError("Approval already claimed.")
            if record.state != "approved" or record.approved is None:
                raise LocalAIControlApprovalNotApprovedError("Approval is not approved.")
            record.state = "claimed"
            return record.approved

    def _pending(self, approval_id: str, control_digest: str, now: datetime) -> _Record:
        record = self._items.get(approval_id)
        if record is None:
            raise LocalAIControlApprovalNotPendingError("Approval is not pending.")
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise LocalAIControlApprovalExpiredError("Approval expired.")
        if record.state != "pending":
            raise LocalAIControlApprovalNotPendingError("Approval is not pending.")
        if not hmac.compare_digest(record.pending.control_digest, control_digest):
            self._items.pop(approval_id, None)
            raise LocalAIControlApprovalDigestMismatchError("Control digest mismatch.")
        return record

    def _validate_live(self, record: _Record, approval_id: str, control_digest: str, now: datetime) -> None:
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise LocalAIControlApprovalExpiredError("Approval expired.")
        if not hmac.compare_digest(record.pending.control_digest, control_digest):
            raise LocalAIControlApprovalDigestMismatchError("Control digest mismatch.")

    def _cleanup(self, now: datetime) -> None:
        expired = [key for key, record in self._items.items() if now >= record.pending.expires_at]
        for key in expired:
            self._items.pop(key, None)


class LocalAIControlApprovalService:
    def __init__(self, *, store: LocalAIControlApprovalStore) -> None:
        if not isinstance(store, LocalAIControlApprovalStore):
            raise TypeError("store must be LocalAIControlApprovalStore.")
        self._store = store

    def propose(self, preview: LocalAIControlPreview) -> LocalAIControlProposalOutcome:
        digest = local_ai_control_digest(preview)
        pending = self._store.create(preview=preview, control_digest=digest)
        return LocalAIControlProposalOutcome(
            status="pending",
            reason_code="owner_decision_required",
            proposal=LocalAIControlProposal(
                approval_id=pending.approval_id,
                control_digest=pending.control_digest,
                preview=pending.preview,
                expires_at=pending.expires_at,
            ),
        )

    def approve(self, approval_id: str, control_digest: str) -> LocalAIControlDecisionOutcome:
        approved = self._store.approve(approval_id, control_digest)
        return LocalAIControlDecisionOutcome(
            approval_id=approved.approval_id,
            decision="approved",
            reason_code="owner_approved",
            control_digest=approved.control_digest,
            preview=approved.preview,
            expires_at=approved.expires_at,
            approved=approved,
        )

    def deny(self, approval_id: str, control_digest: str) -> LocalAIControlDecisionOutcome:
        pending = self._store.deny(approval_id, control_digest)
        return LocalAIControlDecisionOutcome(
            approval_id=pending.approval_id,
            decision="denied",
            reason_code="owner_denied",
            control_digest=pending.control_digest,
            preview=pending.preview,
            expires_at=pending.expires_at,
        )
