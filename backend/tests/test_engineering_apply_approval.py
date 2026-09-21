from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.contracts.engineering_change_proposal import (
    EngineeringChangeBaseState,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_apply_approval import (
    DEFAULT_ENGINEERING_APPLY_APPROVAL_TTL,
    DEFAULT_MAX_ENGINEERING_APPLY_APPROVAL_RECORDS,
    EngineeringApplyApprovalService,
    EngineeringApplyApprovalStore,
    EngineeringApplyDigestMismatchError,
    EngineeringApplyExpiredError,
    EngineeringApplyNotApprovedError,
    EngineeringApplyNotPendingError,
    EngineeringApplyProposalInvalidError,
    EngineeringApplyStoreFullError,
    EngineeringApplyWorkspaceMismatchError,
)


def _workspace_ids():
    values = list(WorkspaceId)
    assert values
    return values


def _scope(index: int = 0) -> WorkspaceScope:
    values = _workspace_ids()
    value = values[index % len(values)]
    try:
        return WorkspaceScope(workspace_id=value)
    except TypeError:
        return WorkspaceScope(value)


def _proposal(
    scope: WorkspaceScope,
    *,
    content: str = "hello D108\n",
) -> EngineeringChangeProposal:
    return EngineeringChangeProposal(
        workspace_scope=scope,
        operation=EngineeringChangeOperation.CREATE_TEXT,
        relative_path="notes/d108.txt",
        base_state=EngineeringChangeBaseState.ABSENT,
        base_content=None,
        base_sha256=None,
        base_size_bytes=None,
        proposed_content=content,
    )


def test_d108_defaults_are_bounded() -> None:
    assert DEFAULT_ENGINEERING_APPLY_APPROVAL_TTL == timedelta(minutes=10)
    assert DEFAULT_MAX_ENGINEERING_APPLY_APPROVAL_RECORDS == 128


def test_d108_propose_retains_exact_server_snapshot() -> None:
    scope = _scope()
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    proposal = _proposal(scope)

    outcome = service.propose(proposal)

    assert outcome.status == "pending"
    assert outcome.reason_code == "owner_decision_required"
    assert outcome.proposal.approval_id == "approval-1"
    assert outcome.proposal.proposal == proposal
    assert outcome.proposal.proposal is not proposal
    assert outcome.proposal.proposal_digest == proposal.proposal_digest
    assert store.record_count == 1


def test_d108_approve_is_separate_from_execution() -> None:
    scope = _scope()
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    proposal = _proposal(scope)
    pending = service.propose(proposal).proposal

    decision = service.approve(
        pending.approval_id,
        pending.proposal_digest,
    )

    assert decision.decision == "approved"
    assert decision.reason_code == "owner_approved"
    assert decision.approved is not None
    assert decision.approved.proposal == proposal

    approved = store.get_approved(
        pending.approval_id,
        pending.proposal_digest,
        workspace_scope=scope,
    )
    assert approved == decision.approved


def test_d108_deny_is_terminal_for_approval_phase() -> None:
    scope = _scope()
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    pending = service.propose(_proposal(scope)).proposal

    decision = service.deny(
        pending.approval_id,
        pending.proposal_digest,
    )

    assert decision.decision == "denied"
    assert decision.approved is None

    with pytest.raises(EngineeringApplyNotPendingError):
        service.approve(
            pending.approval_id,
            pending.proposal_digest,
        )

    with pytest.raises(EngineeringApplyNotApprovedError):
        store.get_approved(
            pending.approval_id,
            pending.proposal_digest,
            workspace_scope=scope,
        )


def test_d108_pending_digest_mismatch_consumes_ticket() -> None:
    scope = _scope()
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    pending = service.propose(_proposal(scope)).proposal

    with pytest.raises(EngineeringApplyDigestMismatchError):
        service.approve(
            pending.approval_id,
            "0" * 64,
        )

    assert store.record_count == 0

    with pytest.raises(EngineeringApplyNotPendingError):
        service.approve(
            pending.approval_id,
            pending.proposal_digest,
        )


def test_d108_replay_approve_fails_closed() -> None:
    scope = _scope()
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    pending = service.propose(_proposal(scope)).proposal

    service.approve(
        pending.approval_id,
        pending.proposal_digest,
    )

    with pytest.raises(EngineeringApplyNotPendingError):
        service.approve(
            pending.approval_id,
            pending.proposal_digest,
        )


def test_d108_expired_pending_cannot_be_approved() -> None:
    scope = _scope()
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    current = [now]

    store = EngineeringApplyApprovalStore(
        ttl=timedelta(minutes=10),
        clock=lambda: current[0],
        approval_id_factory=lambda: "approval-1",
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )
    pending = service.propose(_proposal(scope)).proposal

    current[0] = now + timedelta(minutes=10)

    with pytest.raises(EngineeringApplyExpiredError):
        service.approve(
            pending.approval_id,
            pending.proposal_digest,
        )


def test_d108_store_capacity_fails_closed() -> None:
    scope = _scope()
    ids = iter(("approval-1", "approval-2"))
    store = EngineeringApplyApprovalStore(
        max_records=1,
        approval_id_factory=lambda: next(ids),
    )
    service = EngineeringApplyApprovalService(
        store=store,
        workspace_scope=scope,
    )

    service.propose(_proposal(scope, content="first\n"))

    with pytest.raises(EngineeringApplyStoreFullError):
        service.propose(_proposal(scope, content="second\n"))


def test_d108_cross_workspace_registration_fails_closed() -> None:
    values = _workspace_ids()
    if len(values) < 2:
        pytest.skip("WorkspaceId has fewer than two values.")

    scope_a = _scope(0)
    scope_b = _scope(1)
    service = EngineeringApplyApprovalService(
        store=EngineeringApplyApprovalStore(),
        workspace_scope=scope_a,
    )

    with pytest.raises(EngineeringApplyWorkspaceMismatchError):
        service.propose(_proposal(scope_b))


def test_d108_tampered_proposal_digest_is_rejected() -> None:
    scope = _scope()
    proposal = _proposal(scope)
    object.__setattr__(proposal, "proposal_digest", "0" * 64)

    service = EngineeringApplyApprovalService(
        store=EngineeringApplyApprovalStore(),
        workspace_scope=scope,
    )

    with pytest.raises(EngineeringApplyProposalInvalidError):
        service.propose(proposal)
