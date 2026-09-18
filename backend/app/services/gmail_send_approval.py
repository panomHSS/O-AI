"""D87 Gmail send proposal, digest, preview, and owner approval boundary."""

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

from app.contracts.gmail_send import GmailSendRequest
from app.contracts.gmail_send_approval import (
    ApprovedGmailSendApproval,
    GmailSendApprovalDecisionOutcome,
    GmailSendApprovalProposal,
    GmailSendApprovalProposalOutcome,
    GmailSendPreview,
    PendingGmailSendApproval,
)


DEFAULT_GMAIL_SEND_APPROVAL_TTL = timedelta(minutes=10)
DEFAULT_MAX_GMAIL_SEND_APPROVAL_RECORDS = 100


class GmailSendApprovalError(RuntimeError):
    """Base class for safe D87 approval-boundary errors."""

    reason_code = "gmail_send_approval_error"


class GmailSendApprovalNotPendingError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_not_pending"


class GmailSendApprovalNotApprovedError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_not_approved"


class GmailSendApprovalExpiredError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_expired"


class GmailSendApprovalDigestMismatchError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_digest_mismatch"


class GmailSendApprovalStoreFullError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_store_full"


class GmailSendApprovalProposalInvalidError(GmailSendApprovalError):
    reason_code = "gmail_send_approval_proposal_invalid"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_approval_id() -> str:
    return secrets.token_urlsafe(32)


def gmail_send_projection(request: GmailSendRequest) -> dict[str, object]:
    """Return the exact provider-neutral canonical D86 request projection."""
    if not isinstance(request, GmailSendRequest):
        raise GmailSendApprovalProposalInvalidError(
            "Unsupported D86 Gmail send request."
        )
    return {
        "contract_version": request.contract_version,
        "operation": request.operation,
        "message": {
            "recipient": request.message.recipient,
            "subject": request.message.subject,
            "body": request.message.body,
        },
    }


def gmail_send_digest(request: GmailSendRequest) -> str:
    """Bind owner approval to one deterministic canonical D86 request."""
    projection = gmail_send_projection(request)
    try:
        serialized = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GmailSendApprovalProposalInvalidError(
            "Gmail send request cannot be canonicalized."
        ) from error
    return hashlib.sha256(serialized).hexdigest()


def gmail_send_preview(request: GmailSendRequest) -> GmailSendPreview:
    """Build an exact owner preview without provider/network access."""
    if not isinstance(request, GmailSendRequest):
        raise GmailSendApprovalProposalInvalidError(
            "Unsupported D86 Gmail send request."
        )
    return GmailSendPreview(
        contract_version=request.contract_version,
        operation=request.operation,
        recipient=request.message.recipient,
        subject=request.message.subject,
        body=request.message.body,
    )


@dataclass(slots=True)
class _GmailSendApprovalRecord:
    pending: PendingGmailSendApproval
    state: Literal["pending", "approved", "denied"] = "pending"
    approved: ApprovedGmailSendApproval | None = None


class GmailSendApprovalStore:
    """Thread-safe bounded process-local D87 approval record store."""

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_GMAIL_SEND_APPROVAL_TTL,
        max_records: int = DEFAULT_MAX_GMAIL_SEND_APPROVAL_RECORDS,
        clock: Callable[[], datetime] = _utcnow,
        approval_id_factory: Callable[[], str] = _new_approval_id,
    ) -> None:
        if not isinstance(ttl, timedelta) or ttl.total_seconds() <= 0:
            raise ValueError("ttl must be a positive timedelta.")
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
        ):
            raise ValueError("max_records must be a positive integer.")
        self._ttl = ttl
        self._max_records = max_records
        self._clock = clock
        self._approval_id_factory = approval_id_factory
        self._items: dict[str, _GmailSendApprovalRecord] = {}
        self._lock = threading.Lock()

    @property
    def record_count(self) -> int:
        now = self._clock()
        with self._lock:
            self._cleanup_expired(now)
            return len(self._items)

    def create(
        self,
        *,
        request: GmailSendRequest,
        send_digest: str,
        preview: GmailSendPreview,
    ) -> PendingGmailSendApproval:
        now = self._clock()
        with self._lock:
            self._cleanup_expired(now)
            if len(self._items) >= self._max_records:
                raise GmailSendApprovalStoreFullError(
                    "Gmail send approval capacity is full."
                )

            approval_id: str | None = None
            for _ in range(4):
                candidate = self._approval_id_factory()
                if (
                    isinstance(candidate, str)
                    and candidate
                    and candidate == candidate.strip()
                    and candidate not in self._items
                ):
                    approval_id = candidate
                    break
            if approval_id is None:
                raise GmailSendApprovalProposalInvalidError(
                    "Could not allocate a Gmail send approval ID."
                )

            pending = PendingGmailSendApproval(
                approval_id=approval_id,
                request=request,
                send_digest=send_digest,
                preview=preview,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._items[approval_id] = _GmailSendApprovalRecord(
                pending=pending
            )
            return pending

    def approve(
        self,
        approval_id: str,
        send_digest: str,
    ) -> ApprovedGmailSendApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                send_digest,
                now,
            )
            approved = ApprovedGmailSendApproval(
                approval_id=record.pending.approval_id,
                request=record.pending.request,
                send_digest=record.pending.send_digest,
                preview=record.pending.preview,
                approved_at=now,
                expires_at=record.pending.expires_at,
            )
            record.state = "approved"
            record.approved = approved
            return approved

    def deny(
        self,
        approval_id: str,
        send_digest: str,
    ) -> PendingGmailSendApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                send_digest,
                now,
            )
            record.state = "denied"
            return record.pending

    def get_approved(
        self,
        approval_id: str,
        send_digest: str,
    ) -> ApprovedGmailSendApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise GmailSendApprovalNotApprovedError(
                    "Gmail send approval is not approved."
                )
            if now >= record.pending.expires_at:
                self._items.pop(approval_id, None)
                raise GmailSendApprovalExpiredError(
                    "Gmail send approval has expired."
                )
            if not hmac.compare_digest(
                record.pending.send_digest,
                send_digest,
            ):
                raise GmailSendApprovalDigestMismatchError(
                    "Gmail send digest does not match."
                )
            if record.state != "approved" or record.approved is None:
                raise GmailSendApprovalNotApprovedError(
                    "Gmail send approval is not approved."
                )
            return record.approved

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _pending_record(
        self,
        approval_id: str,
        send_digest: str,
        now: datetime,
    ) -> _GmailSendApprovalRecord:
        record = self._items.get(approval_id)
        if record is None:
            raise GmailSendApprovalNotPendingError(
                "Gmail send approval is not pending."
            )
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise GmailSendApprovalExpiredError(
                "Gmail send approval has expired."
            )
        if record.state != "pending":
            raise GmailSendApprovalNotPendingError(
                "Gmail send approval is not pending."
            )
        if not hmac.compare_digest(
            record.pending.send_digest,
            send_digest,
        ):
            self._items.pop(approval_id, None)
            raise GmailSendApprovalDigestMismatchError(
                "Gmail send digest does not match."
            )
        return record

    def _cleanup_expired(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, record in self._items.items()
            if now >= record.pending.expires_at
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


class GmailSendApprovalService:
    """Create/decide owner approval snapshots; never send Gmail."""

    def __init__(self, *, store: GmailSendApprovalStore) -> None:
        if not isinstance(store, GmailSendApprovalStore):
            raise TypeError("store must be a GmailSendApprovalStore.")
        self._store = store

    def propose(
        self,
        request: GmailSendRequest,
    ) -> GmailSendApprovalProposalOutcome:
        preview = gmail_send_preview(request)
        digest = gmail_send_digest(request)
        pending = self._store.create(
            request=request,
            send_digest=digest,
            preview=preview,
        )
        return GmailSendApprovalProposalOutcome(
            status="pending",
            reason_code="owner_decision_required",
            proposal=GmailSendApprovalProposal(
                approval_id=pending.approval_id,
                send_digest=pending.send_digest,
                preview=pending.preview,
                expires_at=pending.expires_at,
            ),
        )

    def approve(
        self,
        approval_id: str,
        send_digest: str,
    ) -> GmailSendApprovalDecisionOutcome:
        approved = self._store.approve(
            approval_id,
            send_digest,
        )
        return GmailSendApprovalDecisionOutcome(
            approval_id=approved.approval_id,
            decision="approved",
            reason_code="owner_approved",
            send_digest=approved.send_digest,
            preview=approved.preview,
            expires_at=approved.expires_at,
            approved=approved,
        )

    def deny(
        self,
        approval_id: str,
        send_digest: str,
    ) -> GmailSendApprovalDecisionOutcome:
        pending = self._store.deny(
            approval_id,
            send_digest,
        )
        return GmailSendApprovalDecisionOutcome(
            approval_id=pending.approval_id,
            decision="denied",
            reason_code="owner_denied",
            send_digest=pending.send_digest,
            preview=pending.preview,
            expires_at=pending.expires_at,
        )


__all__ = [
    "DEFAULT_GMAIL_SEND_APPROVAL_TTL",
    "DEFAULT_MAX_GMAIL_SEND_APPROVAL_RECORDS",
    "GmailSendApprovalDigestMismatchError",
    "GmailSendApprovalError",
    "GmailSendApprovalExpiredError",
    "GmailSendApprovalNotApprovedError",
    "GmailSendApprovalNotPendingError",
    "GmailSendApprovalProposalInvalidError",
    "GmailSendApprovalService",
    "GmailSendApprovalStore",
    "GmailSendApprovalStoreFullError",
    "gmail_send_digest",
    "gmail_send_preview",
    "gmail_send_projection",
]
