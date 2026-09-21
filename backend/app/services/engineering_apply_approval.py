"""D108 dedicated Engineering Apply owner-approval and lifecycle store."""

from __future__ import annotations

import hmac
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.contracts.engineering_apply import (
    ApprovedEngineeringApplyApproval,
    EngineeringApplyApprovalDecisionOutcome,
    EngineeringApplyApprovalProposal,
    EngineeringApplyApprovalProposalOutcome,
    EngineeringApplyExecutionClaim,
    EngineeringApplyTerminalOutcome,
    PendingEngineeringApplyApproval,
    validate_engineering_apply_digest,
    validate_engineering_apply_plan_digest,
)
from app.contracts.engineering_change_proposal import (
    ENGINEERING_CHANGE_CONTRACT_VERSION,
    EngineeringChangeProposal,
    engineering_change_digest,
)
from app.contracts.workspace import WorkspaceScope


DEFAULT_ENGINEERING_APPLY_APPROVAL_TTL = timedelta(minutes=10)
DEFAULT_MAX_ENGINEERING_APPLY_APPROVAL_RECORDS = 128


class EngineeringApplyApprovalError(RuntimeError):
    reason_code = "engineering_apply_approval_error"


class EngineeringApplyNotPendingError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_not_pending"


class EngineeringApplyNotApprovedError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_not_approved"


class EngineeringApplyAlreadyClaimedError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_already_claimed"


class EngineeringApplyExpiredError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_expired"


class EngineeringApplyDigestMismatchError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_digest_mismatch"


class EngineeringApplyStoreFullError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_store_full"


class EngineeringApplyProposalInvalidError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_proposal_invalid"


class EngineeringApplyWorkspaceMismatchError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_workspace_mismatch"


class EngineeringApplyTerminalError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_terminal"


class EngineeringApplyClaimIntegrityError(EngineeringApplyApprovalError):
    reason_code = "engineering_apply_plan_integrity_failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_approval_id() -> str:
    return secrets.token_urlsafe(32)


def _same_workspace(
    left: WorkspaceScope,
    right: WorkspaceScope,
) -> bool:
    return left == right


def engineering_apply_proposal_snapshot(
    proposal: EngineeringChangeProposal,
    *,
    workspace_scope: WorkspaceScope,
) -> EngineeringChangeProposal:
    """Rebuild and verify one exact immutable D107 proposal snapshot."""

    if not isinstance(proposal, EngineeringChangeProposal):
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal is invalid."
        )
    if not isinstance(workspace_scope, WorkspaceScope):
        raise EngineeringApplyWorkspaceMismatchError(
            "Engineering apply workspace is invalid."
        )
    if not _same_workspace(proposal.workspace_scope, workspace_scope):
        raise EngineeringApplyWorkspaceMismatchError(
            "Engineering apply workspace does not match proposal."
        )
    if proposal.contract_version != ENGINEERING_CHANGE_CONTRACT_VERSION:
        raise EngineeringApplyProposalInvalidError(
            "Engineering change contract version is invalid."
        )

    try:
        validate_engineering_apply_digest(proposal.proposal_digest)
        projection = proposal.canonical_projection()
        recomputed = engineering_change_digest(projection)
    except (TypeError, ValueError):
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal integrity is invalid."
        ) from None

    if not hmac.compare_digest(recomputed, proposal.proposal_digest):
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal digest is invalid."
        )

    try:
        snapshot = EngineeringChangeProposal(
            workspace_scope=proposal.workspace_scope,
            operation=proposal.operation,
            relative_path=proposal.relative_path,
            base_state=proposal.base_state,
            base_content=proposal.base_content,
            base_sha256=proposal.base_sha256,
            base_size_bytes=proposal.base_size_bytes,
            proposed_content=proposal.proposed_content,
        )
    except (TypeError, ValueError):
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal cannot be reconstructed."
        ) from None

    if snapshot.canonical_projection() != projection:
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal snapshot changed."
        )
    if not hmac.compare_digest(
        snapshot.proposal_digest,
        proposal.proposal_digest,
    ):
        raise EngineeringApplyProposalInvalidError(
            "Engineering change proposal snapshot digest changed."
        )

    return snapshot


@dataclass(slots=True)
class _EngineeringApplyApprovalRecord:
    pending: PendingEngineeringApplyApproval
    state: Literal[
        "pending",
        "approved",
        "denied",
        "claimed",
        "applied",
        "stale",
        "failed",
        "indeterminate",
    ] = "pending"
    approved: ApprovedEngineeringApplyApproval | None = None
    claim: EngineeringApplyExecutionClaim | None = None
    outcome: EngineeringApplyTerminalOutcome | None = None


class EngineeringApplyApprovalStore:
    """Thread-safe bounded process-local D108 approval/apply store."""

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_ENGINEERING_APPLY_APPROVAL_TTL,
        max_records: int = DEFAULT_MAX_ENGINEERING_APPLY_APPROVAL_RECORDS,
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
        self._items: dict[str, _EngineeringApplyApprovalRecord] = {}
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
        workspace_scope: WorkspaceScope,
        proposal: EngineeringChangeProposal,
    ) -> PendingEngineeringApplyApproval:
        snapshot = engineering_apply_proposal_snapshot(
            proposal,
            workspace_scope=workspace_scope,
        )
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime.")

        with self._lock:
            self._cleanup_expired(now)
            if len(self._items) >= self._max_records:
                raise EngineeringApplyStoreFullError(
                    "Engineering apply approval capacity is full."
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
                raise EngineeringApplyProposalInvalidError(
                    "Could not allocate engineering apply approval ID."
                )

            pending = PendingEngineeringApplyApproval(
                approval_id=approval_id,
                workspace_scope=workspace_scope,
                proposal=snapshot,
                proposal_digest=snapshot.proposal_digest,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._items[approval_id] = _EngineeringApplyApprovalRecord(
                pending=pending
            )
            return pending

    def approve(
        self,
        approval_id: str,
        proposal_digest: str,
        *,
        workspace_scope: WorkspaceScope,
    ) -> ApprovedEngineeringApplyApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                proposal_digest,
                workspace_scope=workspace_scope,
                now=now,
            )
            snapshot = engineering_apply_proposal_snapshot(
                record.pending.proposal,
                workspace_scope=workspace_scope,
            )
            approved = ApprovedEngineeringApplyApproval(
                approval_id=record.pending.approval_id,
                workspace_scope=record.pending.workspace_scope,
                proposal=snapshot,
                proposal_digest=record.pending.proposal_digest,
                created_at=record.pending.created_at,
                approved_at=now,
                expires_at=record.pending.expires_at,
            )
            record.state = "approved"
            record.approved = approved
            return approved

    def deny(
        self,
        approval_id: str,
        proposal_digest: str,
        *,
        workspace_scope: WorkspaceScope,
    ) -> PendingEngineeringApplyApproval:
        now = self._clock()
        with self._lock:
            record = self._pending_record(
                approval_id,
                proposal_digest,
                workspace_scope=workspace_scope,
                now=now,
            )
            record.state = "denied"
            return record.pending

    def get_approved(
        self,
        approval_id: str,
        proposal_digest: str,
        *,
        workspace_scope: WorkspaceScope,
    ) -> ApprovedEngineeringApplyApproval:
        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )
            self._validate_live(
                record,
                approval_id,
                proposal_digest,
                workspace_scope=workspace_scope,
                now=now,
            )
            if record.state != "approved" or record.approved is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )

            snapshot = engineering_apply_proposal_snapshot(
                record.approved.proposal,
                workspace_scope=workspace_scope,
            )
            if not hmac.compare_digest(
                snapshot.proposal_digest,
                record.approved.proposal_digest,
            ):
                raise EngineeringApplyProposalInvalidError(
                    "Approved engineering proposal integrity changed."
                )
            return record.approved

    def finish_approved(
        self,
        outcome: EngineeringApplyTerminalOutcome,
        *,
        workspace_scope: WorkspaceScope,
    ) -> EngineeringApplyTerminalOutcome:
        """Make one approved record terminal before any execution claim."""

        if not isinstance(outcome, EngineeringApplyTerminalOutcome):
            raise EngineeringApplyTerminalError(
                "Engineering apply terminal outcome is invalid."
            )
        if outcome.status not in {"stale", "failed"}:
            raise EngineeringApplyTerminalError(
                "Only stale/failed may finish before claim."
            )

        now = self._clock()
        with self._lock:
            record = self._items.get(outcome.approval_id)
            if record is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )
            self._validate_live(
                record,
                outcome.approval_id,
                outcome.proposal_digest,
                workspace_scope=workspace_scope,
                now=now,
            )
            if record.state != "approved" or record.approved is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )
            record.state = outcome.status
            record.outcome = outcome
            return outcome

    def claim_approved(
        self,
        approval_id: str,
        proposal_digest: str,
        plan_digest: str,
        *,
        workspace_scope: WorkspaceScope,
    ) -> EngineeringApplyExecutionClaim:
        """Atomically transition exactly one approved proposal to claimed."""

        try:
            validate_engineering_apply_plan_digest(plan_digest)
        except ValueError:
            raise EngineeringApplyClaimIntegrityError(
                "Engineering apply plan digest is invalid."
            ) from None

        now = self._clock()
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )
            self._validate_live(
                record,
                approval_id,
                proposal_digest,
                workspace_scope=workspace_scope,
                now=now,
            )
            if record.state == "claimed":
                raise EngineeringApplyAlreadyClaimedError(
                    "Engineering apply approval is already claimed."
                )
            if record.state in {
                "denied",
                "applied",
                "stale",
                "failed",
                "indeterminate",
            }:
                raise EngineeringApplyTerminalError(
                    "Engineering apply approval is terminal."
                )
            if record.state != "approved" or record.approved is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is not approved."
                )

            snapshot = engineering_apply_proposal_snapshot(
                record.approved.proposal,
                workspace_scope=workspace_scope,
            )
            if not hmac.compare_digest(
                snapshot.proposal_digest,
                record.approved.proposal_digest,
            ):
                raise EngineeringApplyProposalInvalidError(
                    "Approved engineering proposal integrity changed."
                )

            claim = EngineeringApplyExecutionClaim(
                approval_id=approval_id,
                proposal_digest=proposal_digest,
                plan_digest=plan_digest,
            )
            record.state = "claimed"
            record.claim = claim
            return claim

    def complete(
        self,
        claim: EngineeringApplyExecutionClaim,
        outcome: EngineeringApplyTerminalOutcome,
    ) -> EngineeringApplyTerminalOutcome:
        """Record one post-claim terminal result; never releases authority."""

        if not isinstance(claim, EngineeringApplyExecutionClaim):
            raise EngineeringApplyClaimIntegrityError(
                "Engineering apply claim is invalid."
            )
        if not isinstance(outcome, EngineeringApplyTerminalOutcome):
            raise EngineeringApplyTerminalError(
                "Engineering apply outcome is invalid."
            )
        if outcome.status not in {"applied", "stale", "indeterminate"}:
            raise EngineeringApplyTerminalError(
                "Post-claim outcome must be applied/stale/indeterminate."
            )
        if (
            outcome.approval_id != claim.approval_id
            or not hmac.compare_digest(
                outcome.proposal_digest,
                claim.proposal_digest,
            )
        ):
            raise EngineeringApplyClaimIntegrityError(
                "Engineering apply outcome does not match claim."
            )

        with self._lock:
            record = self._items.get(claim.approval_id)
            if record is None:
                raise EngineeringApplyAlreadyClaimedError(
                    "Engineering apply claim is unavailable."
                )
            if record.claim != claim:
                raise EngineeringApplyClaimIntegrityError(
                    "Engineering apply claim changed."
                )
            if record.state != "claimed" or record.outcome is not None:
                raise EngineeringApplyTerminalError(
                    "Engineering apply lifecycle is already terminal."
                )
            record.state = outcome.status
            record.outcome = outcome
            return outcome

    def state(self, approval_id: str) -> str:
        with self._lock:
            record = self._items.get(approval_id)
            if record is None:
                raise EngineeringApplyNotApprovedError(
                    "Engineering apply approval is unavailable."
                )
            return record.state

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _pending_record(
        self,
        approval_id: str,
        proposal_digest: str,
        *,
        workspace_scope: WorkspaceScope,
        now: datetime,
    ) -> _EngineeringApplyApprovalRecord:
        record = self._items.get(approval_id)
        if record is None:
            raise EngineeringApplyNotPendingError(
                "Engineering apply approval is not pending."
            )
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise EngineeringApplyExpiredError(
                "Engineering apply approval has expired."
            )
        if record.state != "pending":
            raise EngineeringApplyNotPendingError(
                "Engineering apply approval is not pending."
            )
        if not _same_workspace(
            record.pending.workspace_scope,
            workspace_scope,
        ):
            raise EngineeringApplyWorkspaceMismatchError(
                "Engineering apply workspace does not match."
            )
        try:
            validate_engineering_apply_digest(proposal_digest)
        except ValueError:
            self._items.pop(approval_id, None)
            raise EngineeringApplyDigestMismatchError(
                "Engineering apply proposal digest does not match."
            ) from None
        if not hmac.compare_digest(
            record.pending.proposal_digest,
            proposal_digest,
        ):
            self._items.pop(approval_id, None)
            raise EngineeringApplyDigestMismatchError(
                "Engineering apply proposal digest does not match."
            )
        return record

    def _validate_live(
        self,
        record: _EngineeringApplyApprovalRecord,
        approval_id: str,
        proposal_digest: str,
        *,
        workspace_scope: WorkspaceScope,
        now: datetime,
    ) -> None:
        if now >= record.pending.expires_at:
            self._items.pop(approval_id, None)
            raise EngineeringApplyExpiredError(
                "Engineering apply approval has expired."
            )
        if not _same_workspace(
            record.pending.workspace_scope,
            workspace_scope,
        ):
            raise EngineeringApplyWorkspaceMismatchError(
                "Engineering apply workspace does not match."
            )
        try:
            validate_engineering_apply_digest(proposal_digest)
        except ValueError:
            raise EngineeringApplyDigestMismatchError(
                "Engineering apply proposal digest does not match."
            ) from None
        if not hmac.compare_digest(
            record.pending.proposal_digest,
            proposal_digest,
        ):
            raise EngineeringApplyDigestMismatchError(
                "Engineering apply proposal digest does not match."
            )

    def _cleanup_expired(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, record in self._items.items()
            if now >= record.pending.expires_at
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


class EngineeringApplyApprovalService:
    """Register and decide exact D107 proposals; never mutate repository state."""

    def __init__(
        self,
        *,
        store: EngineeringApplyApprovalStore,
        workspace_scope: WorkspaceScope,
    ) -> None:
        if not isinstance(store, EngineeringApplyApprovalStore):
            raise TypeError("store must be EngineeringApplyApprovalStore.")
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_apply_workspace_mismatch")
        self._store = store
        self._workspace_scope = workspace_scope

    def propose(
        self,
        proposal: EngineeringChangeProposal,
    ) -> EngineeringApplyApprovalProposalOutcome:
        pending = self._store.create(
            workspace_scope=self._workspace_scope,
            proposal=proposal,
        )
        return EngineeringApplyApprovalProposalOutcome(
            status="pending",
            reason_code="owner_decision_required",
            proposal=EngineeringApplyApprovalProposal(
                approval_id=pending.approval_id,
                proposal=pending.proposal,
                proposal_digest=pending.proposal_digest,
                expires_at=pending.expires_at,
            ),
        )

    def approve(
        self,
        approval_id: str,
        proposal_digest: str,
    ) -> EngineeringApplyApprovalDecisionOutcome:
        approved = self._store.approve(
            approval_id,
            proposal_digest,
            workspace_scope=self._workspace_scope,
        )
        return EngineeringApplyApprovalDecisionOutcome(
            approval_id=approved.approval_id,
            decision="approved",
            reason_code="owner_approved",
            proposal_digest=approved.proposal_digest,
            expires_at=approved.expires_at,
            approved=approved,
        )

    def deny(
        self,
        approval_id: str,
        proposal_digest: str,
    ) -> EngineeringApplyApprovalDecisionOutcome:
        pending = self._store.deny(
            approval_id,
            proposal_digest,
            workspace_scope=self._workspace_scope,
        )
        return EngineeringApplyApprovalDecisionOutcome(
            approval_id=pending.approval_id,
            decision="denied",
            reason_code="owner_denied",
            proposal_digest=pending.proposal_digest,
            expires_at=pending.expires_at,
        )


__all__ = [
    "DEFAULT_ENGINEERING_APPLY_APPROVAL_TTL",
    "DEFAULT_MAX_ENGINEERING_APPLY_APPROVAL_RECORDS",
    "EngineeringApplyAlreadyClaimedError",
    "EngineeringApplyApprovalError",
    "EngineeringApplyApprovalService",
    "EngineeringApplyApprovalStore",
    "EngineeringApplyClaimIntegrityError",
    "EngineeringApplyDigestMismatchError",
    "EngineeringApplyExpiredError",
    "EngineeringApplyNotApprovedError",
    "EngineeringApplyNotPendingError",
    "EngineeringApplyProposalInvalidError",
    "EngineeringApplyStoreFullError",
    "EngineeringApplyTerminalError",
    "EngineeringApplyWorkspaceMismatchError",
    "engineering_apply_proposal_snapshot",
]
