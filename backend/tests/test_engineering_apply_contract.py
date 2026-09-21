from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from app.contracts.engineering_apply import (
    ENGINEERING_APPLY_CONTRACT_VERSION,
    ApprovedEngineeringApplyApproval,
    EngineeringApplyApprovalDecisionOutcome,
    EngineeringApplyApprovalProposal,
    EngineeringApplyApprovalProposalOutcome,
    EngineeringApplyTerminalOutcome,
    PendingEngineeringApplyApproval,
)
from app.contracts.engineering_change_proposal import (
    EngineeringChangeBaseState,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope


def _scope(index: int = 0) -> WorkspaceScope:
    values = list(WorkspaceId)
    assert values
    value = values[index % len(values)]
    try:
        return WorkspaceScope(workspace_id=value)
    except TypeError:
        return WorkspaceScope(value)


def _proposal(scope: WorkspaceScope) -> EngineeringChangeProposal:
    return EngineeringChangeProposal(
        workspace_scope=scope,
        operation=EngineeringChangeOperation.CREATE_TEXT,
        relative_path="notes/d108.txt",
        base_state=EngineeringChangeBaseState.ABSENT,
        base_content=None,
        base_sha256=None,
        base_size_bytes=None,
        proposed_content="approved content\n",
    )


def test_d108_contract_version_and_immutability() -> None:
    scope = _scope()
    proposal = _proposal(scope)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    pending = PendingEngineeringApplyApproval(
        approval_id="approval-1",
        workspace_scope=scope,
        proposal=proposal,
        proposal_digest=proposal.proposal_digest,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )

    assert pending.contract_version == ENGINEERING_APPLY_CONTRACT_VERSION

    with pytest.raises(dataclasses.FrozenInstanceError):
        pending.approval_id = "changed"  # type: ignore[misc]


def test_d108_approved_contract_binds_exact_proposal() -> None:
    scope = _scope()
    proposal = _proposal(scope)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    approved = ApprovedEngineeringApplyApproval(
        approval_id="approval-1",
        workspace_scope=scope,
        proposal=proposal,
        proposal_digest=proposal.proposal_digest,
        created_at=now,
        approved_at=now + timedelta(minutes=1),
        expires_at=now + timedelta(minutes=10),
    )

    assert approved.proposal is proposal
    assert approved.proposal_digest == proposal.proposal_digest


def test_d108_review_and_decision_contracts_are_bounded() -> None:
    scope = _scope()
    proposal = _proposal(scope)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    review = EngineeringApplyApprovalProposal(
        approval_id="approval-1",
        proposal=proposal,
        proposal_digest=proposal.proposal_digest,
        expires_at=now + timedelta(minutes=10),
    )
    outcome = EngineeringApplyApprovalProposalOutcome(
        status="pending",
        reason_code="owner_decision_required",
        proposal=review,
    )

    assert outcome.status == "pending"
    assert outcome.proposal.proposal.relative_path == "notes/d108.txt"

    denied = EngineeringApplyApprovalDecisionOutcome(
        approval_id="approval-1",
        decision="denied",
        reason_code="owner_denied",
        proposal_digest=proposal.proposal_digest,
        expires_at=now + timedelta(minutes=10),
    )
    assert denied.approved is None


@pytest.mark.parametrize(
    "status",
    ["applied", "stale", "failed", "indeterminate"],
)
def test_d108_terminal_outcome_exact_statuses(status: str) -> None:
    scope = _scope()
    proposal = _proposal(scope)
    outcome = EngineeringApplyTerminalOutcome(
        approval_id="approval-1",
        proposal_digest=proposal.proposal_digest,
        status=status,  # type: ignore[arg-type]
        reason_code="test_terminal",
    )
    assert outcome.status == status


def test_d108_contract_rejects_digest_substitution() -> None:
    scope = _scope()
    proposal = _proposal(scope)
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="engineering_apply_digest_mismatch"):
        PendingEngineeringApplyApproval(
            approval_id="approval-1",
            workspace_scope=scope,
            proposal=proposal,
            proposal_digest="0" * 64,
            created_at=now,
            expires_at=now + timedelta(minutes=10),
        )
