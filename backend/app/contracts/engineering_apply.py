"""D108 Controlled Engineering Apply contracts.

These contracts bind owner approval to one exact immutable D107 proposal.
They do not themselves grant filesystem mutation, Tool execution, shell/process,
Git, network, credential, connector, or AI-provider authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from app.contracts.engineering_change_proposal import EngineeringChangeProposal
from app.contracts.workspace import WorkspaceScope


ENGINEERING_APPLY_CONTRACT_VERSION = "d108.v1"

EngineeringApplyLifecycleState: TypeAlias = Literal[
    "pending",
    "approved",
    "denied",
    "claimed",
    "applied",
    "stale",
    "failed",
    "indeterminate",
]
EngineeringApplyDecision: TypeAlias = Literal["approved", "denied"]
EngineeringApplyTerminalStatus: TypeAlias = Literal[
    "applied",
    "stale",
    "failed",
    "indeterminate",
]

_HEX = frozenset("0123456789abcdef")


def _validate_text(value: object, *, code: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    return value


def _validate_sha256(value: object, *, code: str) -> str:
    value = _validate_text(value, code=code)
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError(code)
    return value


def validate_engineering_apply_digest(value: object) -> str:
    return _validate_sha256(
        value,
        code="engineering_apply_digest_mismatch",
    )


def validate_engineering_apply_plan_digest(value: object) -> str:
    return _validate_sha256(
        value,
        code="engineering_apply_plan_integrity_failed",
    )


def _validate_workspace(value: object) -> WorkspaceScope:
    if not isinstance(value, WorkspaceScope):
        raise ValueError("engineering_apply_workspace_mismatch")
    return value


def _validate_proposal(value: object) -> EngineeringChangeProposal:
    if not isinstance(value, EngineeringChangeProposal):
        raise ValueError("engineering_apply_proposal_invalid")
    return value


def _validate_aware(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(code)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class PendingEngineeringApplyApproval:
    """One server-held pending D108 approval snapshot."""

    approval_id: str
    workspace_scope: WorkspaceScope
    proposal: EngineeringChangeProposal
    proposal_digest: str
    created_at: datetime
    expires_at: datetime
    contract_version: str = ENGINEERING_APPLY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        _validate_workspace(self.workspace_scope)
        _validate_proposal(self.proposal)
        validate_engineering_apply_digest(self.proposal_digest)

        if self.proposal.workspace_scope != self.workspace_scope:
            raise ValueError("engineering_apply_workspace_mismatch")
        if self.proposal.proposal_digest != self.proposal_digest:
            raise ValueError("engineering_apply_digest_mismatch")

        created_at = _validate_aware(
            self.created_at,
            code="engineering_apply_request_invalid",
        )
        expires_at = _validate_aware(
            self.expires_at,
            code="engineering_apply_request_invalid",
        )
        if expires_at <= created_at:
            raise ValueError("engineering_apply_request_invalid")
        if self.contract_version != ENGINEERING_APPLY_CONTRACT_VERSION:
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class ApprovedEngineeringApplyApproval:
    """One exact owner-approved D107 proposal snapshot."""

    approval_id: str
    workspace_scope: WorkspaceScope
    proposal: EngineeringChangeProposal
    proposal_digest: str
    created_at: datetime
    approved_at: datetime
    expires_at: datetime
    contract_version: str = ENGINEERING_APPLY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        _validate_workspace(self.workspace_scope)
        _validate_proposal(self.proposal)
        validate_engineering_apply_digest(self.proposal_digest)

        if self.proposal.workspace_scope != self.workspace_scope:
            raise ValueError("engineering_apply_workspace_mismatch")
        if self.proposal.proposal_digest != self.proposal_digest:
            raise ValueError("engineering_apply_digest_mismatch")

        created_at = _validate_aware(
            self.created_at,
            code="engineering_apply_request_invalid",
        )
        approved_at = _validate_aware(
            self.approved_at,
            code="engineering_apply_request_invalid",
        )
        expires_at = _validate_aware(
            self.expires_at,
            code="engineering_apply_request_invalid",
        )
        if not (created_at <= approved_at < expires_at):
            raise ValueError("engineering_apply_request_invalid")
        if self.contract_version != ENGINEERING_APPLY_CONTRACT_VERSION:
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringApplyApprovalProposal:
    """Owner-review correlation for one exact server-held proposal."""

    approval_id: str
    proposal: EngineeringChangeProposal
    proposal_digest: str
    expires_at: datetime
    contract_version: str = ENGINEERING_APPLY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        _validate_proposal(self.proposal)
        validate_engineering_apply_digest(self.proposal_digest)
        if self.proposal.proposal_digest != self.proposal_digest:
            raise ValueError("engineering_apply_digest_mismatch")
        _validate_aware(
            self.expires_at,
            code="engineering_apply_request_invalid",
        )
        if self.contract_version != ENGINEERING_APPLY_CONTRACT_VERSION:
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringApplyApprovalProposalOutcome:
    """Result of registering one D107 proposal for owner decision."""

    status: Literal["pending"]
    reason_code: str
    proposal: EngineeringApplyApprovalProposal

    def __post_init__(self) -> None:
        if self.status != "pending":
            raise ValueError("engineering_apply_request_invalid")
        _validate_text(
            self.reason_code,
            code="engineering_apply_request_invalid",
        )
        if not isinstance(self.proposal, EngineeringApplyApprovalProposal):
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringApplyApprovalDecisionOutcome:
    """Result of an explicit structured owner decision."""

    approval_id: str
    decision: EngineeringApplyDecision
    reason_code: str
    proposal_digest: str
    expires_at: datetime
    approved: ApprovedEngineeringApplyApproval | None = None

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        if self.decision not in {"approved", "denied"}:
            raise ValueError("engineering_apply_request_invalid")
        _validate_text(
            self.reason_code,
            code="engineering_apply_request_invalid",
        )
        validate_engineering_apply_digest(self.proposal_digest)
        _validate_aware(
            self.expires_at,
            code="engineering_apply_request_invalid",
        )
        if self.decision == "approved":
            if not isinstance(self.approved, ApprovedEngineeringApplyApproval):
                raise ValueError("engineering_apply_request_invalid")
            if self.approved.approval_id != self.approval_id:
                raise ValueError("engineering_apply_request_invalid")
            if self.approved.proposal_digest != self.proposal_digest:
                raise ValueError("engineering_apply_digest_mismatch")
        elif self.approved is not None:
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringApplyExecutionClaim:
    """One atomic one-shot D108 apply claim bound to one exact plan."""

    approval_id: str
    proposal_digest: str
    plan_digest: str
    contract_version: str = ENGINEERING_APPLY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        validate_engineering_apply_digest(self.proposal_digest)
        validate_engineering_apply_plan_digest(self.plan_digest)
        if self.proposal_digest == self.plan_digest:
            raise ValueError("engineering_apply_plan_integrity_failed")
        if self.contract_version != ENGINEERING_APPLY_CONTRACT_VERSION:
            raise ValueError("engineering_apply_request_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringApplyTerminalOutcome:
    """Provider-neutral terminal D108 apply result."""

    approval_id: str
    proposal_digest: str
    status: EngineeringApplyTerminalStatus
    reason_code: str

    def __post_init__(self) -> None:
        _validate_text(
            self.approval_id,
            code="engineering_apply_request_invalid",
        )
        validate_engineering_apply_digest(self.proposal_digest)
        if self.status not in {
            "applied",
            "stale",
            "failed",
            "indeterminate",
        }:
            raise ValueError("engineering_apply_request_invalid")
        _validate_text(
            self.reason_code,
            code="engineering_apply_request_invalid",
        )


__all__ = [
    "ENGINEERING_APPLY_CONTRACT_VERSION",
    "ApprovedEngineeringApplyApproval",
    "EngineeringApplyApprovalDecisionOutcome",
    "EngineeringApplyApprovalProposal",
    "EngineeringApplyApprovalProposalOutcome",
    "EngineeringApplyDecision",
    "EngineeringApplyExecutionClaim",
    "EngineeringApplyLifecycleState",
    "EngineeringApplyTerminalOutcome",
    "EngineeringApplyTerminalStatus",
    "PendingEngineeringApplyApproval",
    "validate_engineering_apply_digest",
    "validate_engineering_apply_plan_digest",
]
