"""D73 Calendar write proposal, preview, digest, and owner approval boundary."""

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

from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventPatch,
    GoogleCalendarUpdateEventRequest,
)
from app.contracts.google_calendar_write_approval import (
    ApprovedCalendarWriteApproval,
    CalendarWriteApprovalDecisionOutcome,
    CalendarWriteApprovalProposal,
    CalendarWriteApprovalProposalOutcome,
    CalendarWritePreview,
    CalendarWriteRequest,
    PendingCalendarWriteApproval,
)


DEFAULT_CALENDAR_WRITE_APPROVAL_TTL = timedelta(minutes=10)
DEFAULT_MAX_CALENDAR_WRITE_APPROVAL_RECORDS = 100


class CalendarWriteApprovalError(RuntimeError):
    """Base class for safe D73 approval-boundary errors."""

    reason_code = "calendar_write_approval_error"


class CalendarWriteApprovalNotPendingError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_not_pending"


class CalendarWriteApprovalNotApprovedError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_not_approved"


class CalendarWriteApprovalAlreadyClaimedError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_already_claimed"


class CalendarWriteApprovalExpiredError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_expired"


class CalendarWriteApprovalDigestMismatchError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_digest_mismatch"


class CalendarWriteApprovalStoreFullError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_store_full"


class CalendarWriteApprovalProposalInvalidError(CalendarWriteApprovalError):
    reason_code = "calendar_write_approval_proposal_invalid"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_approval_id() -> str:
    return secrets.token_urlsafe(32)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")


def _patch_projection(
    changes: GoogleCalendarEventPatch,
) -> dict[str, object]:
    projection: dict[str, object] = {}
    if changes.summary is not None:
        projection["summary"] = changes.summary
    if changes.start is not None:
        projection["start"] = _iso(changes.start)
        projection["end"] = _iso(changes.end)  # type: ignore[arg-type]
    if changes.description is not None:
        projection["description"] = changes.description
    if changes.location is not None:
        projection["location"] = changes.location
    return projection


def calendar_write_projection(
    request: CalendarWriteRequest,
) -> dict[str, object]:
    """Return the exact provider-neutral canonical D72 request projection."""
    if isinstance(request, GoogleCalendarCreateEventRequest):
        event: dict[str, object] = {
            "calendar_id": request.event.calendar_id,
            "summary": request.event.summary,
            "start": _iso(request.event.start),
            "end": _iso(request.event.end),
        }
        if request.event.description is not None:
            event["description"] = request.event.description
        if request.event.location is not None:
            event["location"] = request.event.location
        return {
            "contract_version": request.contract_version,
            "operation": request.operation,
            "event": event,
        }

    if isinstance(request, GoogleCalendarUpdateEventRequest):
        return {
            "contract_version": request.contract_version,
            "operation": request.operation,
            "target": {
                "calendar_id": request.target.calendar_id,
                "event_id": request.target.event_id,
            },
            "changes": _patch_projection(request.changes),
        }

    if isinstance(request, GoogleCalendarDeleteEventRequest):
        return {
            "contract_version": request.contract_version,
            "operation": request.operation,
            "target": {
                "calendar_id": request.target.calendar_id,
                "event_id": request.target.event_id,
            },
        }

    raise CalendarWriteApprovalProposalInvalidError(
        "Unsupported D72 Calendar write request."
    )


def calendar_write_digest(request: CalendarWriteRequest) -> str:
    """Bind an approval to one deterministic canonical D72 request."""
    projection = calendar_write_projection(request)
    try:
        serialized = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CalendarWriteApprovalProposalInvalidError(
            "Calendar write request cannot be canonicalized."
        ) from error
    return hashlib.sha256(serialized).hexdigest()


def calendar_write_preview(
    request: CalendarWriteRequest,
) -> CalendarWritePreview:
    """Build a deterministic owner preview without provider/network access."""
    if isinstance(request, GoogleCalendarCreateEventRequest):
        changed = ["summary", "start", "end"]
        if request.event.description is not None:
            changed.append("description")
        if request.event.location is not None:
            changed.append("location")
        return CalendarWritePreview(
            contract_version=request.contract_version,
            operation=request.operation,
            calendar_id=request.event.calendar_id,
            summary=request.event.summary,
            start=_iso(request.event.start),
            end=_iso(request.event.end),
            description=request.event.description,
            location=request.event.location,
            changed_fields=tuple(changed),
        )

    if isinstance(request, GoogleCalendarUpdateEventRequest):
        changed: list[str] = []
        changes = request.changes
        if changes.summary is not None:
            changed.append("summary")
        if changes.start is not None:
            changed.extend(("start", "end"))
        if changes.description is not None:
            changed.append("description")
        if changes.location is not None:
            changed.append("location")
        return CalendarWritePreview(
            contract_version=request.contract_version,
            operation=request.operation,
            calendar_id=request.target.calendar_id,
            event_id=request.target.event_id,
            summary=changes.summary,
            start=(
                _iso(changes.start)
                if changes.start is not None
                else None
            ),
            end=(
                _iso(changes.end)
                if changes.end is not None
                else None
            ),
            description=changes.description,
            location=changes.location,
            changed_fields=tuple(changed),
        )

    if isinstance(request, GoogleCalendarDeleteEventRequest):
        return CalendarWritePreview(
            contract_version=request.contract_version,
            operation=request.operation,
            calendar_id=request.target.calendar_id,
            event_id=request.target.event_id,
        )

    raise CalendarWriteApprovalProposalInvalidError(
        "Unsupported D72 Calendar write request."
    )


@dataclass(slots=True)
class _CalendarWriteApprovalRecord:
    pending: PendingCalendarWriteApproval
    state: Literal["pending", "approved", "claimed", "denied"] = "pending"
    approved: ApprovedCalendarWriteApproval | None = None


class CalendarWriteApprovalStore:
    """Thread-safe bounded process-local D73 approval record store."""

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_CALENDAR_WRITE_APPROVAL_TTL,
        max_records: int = DEFAULT_MAX_CALENDAR_WRITE_APPROVAL_RECORDS,
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
        self._items: dict[str, _CalendarWriteApprovalRecord] = {}
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
        request: CalendarWriteRequest,
        write_digest: str,
        preview: CalendarWritePreview,
    ) -> PendingCalendarWriteApproval:
        now = self._clock()
        with self._lock:
            self._cleanup_expired(now)
            if len(self._items) >= self._max_records:
                raise CalendarWriteApprovalStoreFullError(
                    "Calendar write approval capacity is full."
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
                raise CalendarWriteApprovalProposalInvalidError(
                    "Could not allocate a Calendar write approval ID."
                )

            pending = PendingCalendarWriteApproval(
                approval_id=approval_id,
                request=request,
                write_digest=write_digest,
                preview=preview,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._items[approval_id] = _CalendarWriteApprovalRecord(
                pending=pending
            )
            return pending

    def approve(
        self,
        approval_id: str,
        write_digest: str,
    ) -> ApprovedCalendarWriteApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                write_digest,
                now,
            )
            approved = ApprovedCalendarWriteApproval(
                approval_id=record.pending.approval_id,
                request=record.pending.request,
                write_digest=record.pending.write_digest,
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
        write_digest: str,
    ) -> PendingCalendarWriteApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                write_digest,
                now,
            )
            record.state = "denied"
            return record.pending

    def get_approved(
        self,
        approval_id: str,
        write_digest: str,
    ) -> ApprovedCalendarWriteApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise CalendarWriteApprovalNotApprovedError(
                    "Calendar write approval is not approved."
                )
            if now >= record.pending.expires_at:
                self._items.pop(approval_id, None)
                raise CalendarWriteApprovalExpiredError(
                    "Calendar write approval has expired."
                )
            if not hmac.compare_digest(
                record.pending.write_digest,
                write_digest,
            ):
                raise CalendarWriteApprovalDigestMismatchError(
                    "Calendar write digest does not match."
                )
            if record.state != "approved" or record.approved is None:
                raise CalendarWriteApprovalNotApprovedError(
                    "Calendar write approval is not approved."
                )
            return record.approved

    def claim_approved(
        self,
        approval_id: str,
        write_digest: str,
    ) -> ApprovedCalendarWriteApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise CalendarWriteApprovalNotApprovedError(
                    "Calendar write approval is not approved."
                )
            if now >= record.pending.expires_at:
                self._items.pop(approval_id, None)
                raise CalendarWriteApprovalExpiredError(
                    "Calendar write approval has expired."
                )
            if not hmac.compare_digest(
                record.pending.write_digest,
                write_digest,
            ):
                raise CalendarWriteApprovalDigestMismatchError(
                    "Calendar write digest does not match."
                )
            if record.state == "claimed":
                raise CalendarWriteApprovalAlreadyClaimedError(
                    "Calendar write approval has already been claimed."
                )
            if record.state != "approved" or record.approved is None:
                raise CalendarWriteApprovalNotApprovedError(
                    "Calendar write approval is not approved."
                )
            record.state = "claimed"
            return record.approved

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _pending_record(
        self,
        approval_id: str,
        write_digest: str,
        now: datetime,
    ) -> _CalendarWriteApprovalRecord:
        record = self._items.get(approval_id)
        if record is None:
            raise CalendarWriteApprovalNotPendingError(
                "Calendar write approval is not pending."
            )
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise CalendarWriteApprovalExpiredError(
                "Calendar write approval has expired."
            )
        if record.state != "pending":
            raise CalendarWriteApprovalNotPendingError(
                "Calendar write approval is not pending."
            )
        if not hmac.compare_digest(
            record.pending.write_digest,
            write_digest,
        ):
            # Fail closed: a mismatched digest consumes the pending ticket.
            self._items.pop(approval_id, None)
            raise CalendarWriteApprovalDigestMismatchError(
                "Calendar write digest does not match."
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


class CalendarWriteApprovalService:
    """Create and decide owner approval snapshots; never execute writes."""

    def __init__(self, *, store: CalendarWriteApprovalStore) -> None:
        if not isinstance(store, CalendarWriteApprovalStore):
            raise TypeError("store must be a CalendarWriteApprovalStore.")
        self._store = store

    def propose(
        self,
        request: CalendarWriteRequest,
    ) -> CalendarWriteApprovalProposalOutcome:
        preview = calendar_write_preview(request)
        digest = calendar_write_digest(request)
        pending = self._store.create(
            request=request,
            write_digest=digest,
            preview=preview,
        )
        return CalendarWriteApprovalProposalOutcome(
            status="pending",
            reason_code="owner_decision_required",
            proposal=CalendarWriteApprovalProposal(
                approval_id=pending.approval_id,
                write_digest=pending.write_digest,
                preview=pending.preview,
                expires_at=pending.expires_at,
            ),
        )

    def approve(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteApprovalDecisionOutcome:
        approved = self._store.approve(
            approval_id,
            write_digest,
        )
        return CalendarWriteApprovalDecisionOutcome(
            approval_id=approved.approval_id,
            decision="approved",
            reason_code="owner_approved",
            write_digest=approved.write_digest,
            preview=approved.preview,
            expires_at=approved.expires_at,
            approved=approved,
        )

    def deny(
        self,
        approval_id: str,
        write_digest: str,
    ) -> CalendarWriteApprovalDecisionOutcome:
        pending = self._store.deny(
            approval_id,
            write_digest,
        )
        return CalendarWriteApprovalDecisionOutcome(
            approval_id=pending.approval_id,
            decision="denied",
            reason_code="owner_denied",
            write_digest=pending.write_digest,
            preview=pending.preview,
            expires_at=pending.expires_at,
        )


__all__ = [
    "CalendarWriteApprovalAlreadyClaimedError",
    "CalendarWriteApprovalDigestMismatchError",
    "CalendarWriteApprovalError",
    "CalendarWriteApprovalExpiredError",
    "CalendarWriteApprovalNotApprovedError",
    "CalendarWriteApprovalNotPendingError",
    "CalendarWriteApprovalProposalInvalidError",
    "CalendarWriteApprovalService",
    "CalendarWriteApprovalStore",
    "CalendarWriteApprovalStoreFullError",
    "DEFAULT_CALENDAR_WRITE_APPROVAL_TTL",
    "DEFAULT_MAX_CALENDAR_WRITE_APPROVAL_RECORDS",
    "calendar_write_digest",
    "calendar_write_preview",
    "calendar_write_projection",
]
