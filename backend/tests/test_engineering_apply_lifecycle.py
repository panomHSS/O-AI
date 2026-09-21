from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.contracts.engineering_apply import (
    EngineeringApplyExecutionClaim,
    EngineeringApplyTerminalOutcome,
)
from app.contracts.engineering_change_proposal import (
    EngineeringChangeBaseState,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_apply_approval import (
    EngineeringApplyAlreadyClaimedError,
    EngineeringApplyApprovalStore,
    EngineeringApplyTerminalError,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


def _proposal() -> EngineeringChangeProposal:
    return EngineeringChangeProposal(
        workspace_scope=PERSONAL,
        operation=EngineeringChangeOperation.CREATE_TEXT,
        relative_path="backend/new.py",
        base_state=EngineeringChangeBaseState.ABSENT,
        base_content=None,
        base_sha256=None,
        base_size_bytes=None,
        proposed_content="value = 2\n",
    )


def _approved_store():
    store = EngineeringApplyApprovalStore(
        approval_id_factory=lambda: "approval-1"
    )
    proposal = _proposal()
    pending = store.create(
        workspace_scope=PERSONAL,
        proposal=proposal,
    )
    approved = store.approve(
        pending.approval_id,
        pending.proposal_digest,
        workspace_scope=PERSONAL,
    )
    return store, approved


def test_d108_claim_is_one_time() -> None:
    store, approved = _approved_store()
    plan_digest = "1" * 64

    claim = store.claim_approved(
        approved.approval_id,
        approved.proposal_digest,
        plan_digest,
        workspace_scope=PERSONAL,
    )

    assert isinstance(claim, EngineeringApplyExecutionClaim)
    assert store.state(approved.approval_id) == "claimed"

    with pytest.raises(EngineeringApplyAlreadyClaimedError):
        store.claim_approved(
            approved.approval_id,
            approved.proposal_digest,
            plan_digest,
            workspace_scope=PERSONAL,
        )


def test_d108_claim_terminal_never_returns_to_approved() -> None:
    store, approved = _approved_store()
    claim = store.claim_approved(
        approved.approval_id,
        approved.proposal_digest,
        "1" * 64,
        workspace_scope=PERSONAL,
    )
    outcome = EngineeringApplyTerminalOutcome(
        approval_id=approved.approval_id,
        proposal_digest=approved.proposal_digest,
        status="indeterminate",
        reason_code="engineering_apply_indeterminate",
    )

    store.complete(claim, outcome)

    assert store.state(approved.approval_id) == "indeterminate"

    with pytest.raises(EngineeringApplyTerminalError):
        store.claim_approved(
            approved.approval_id,
            approved.proposal_digest,
            "2" * 64,
            workspace_scope=PERSONAL,
        )


def test_d108_preclaim_failed_is_terminal() -> None:
    store, approved = _approved_store()
    outcome = EngineeringApplyTerminalOutcome(
        approval_id=approved.approval_id,
        proposal_digest=approved.proposal_digest,
        status="failed",
        reason_code="engineering_apply_authorization_failed",
    )

    store.finish_approved(
        outcome,
        workspace_scope=PERSONAL,
    )

    assert store.state(approved.approval_id) == "failed"

    with pytest.raises(EngineeringApplyTerminalError):
        store.claim_approved(
            approved.approval_id,
            approved.proposal_digest,
            "1" * 64,
            workspace_scope=PERSONAL,
        )
