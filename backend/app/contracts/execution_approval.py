"""D45 immutable contracts for one-time owner execution approval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping, TypeAlias

from app.contracts.capability_permission import (
    CapabilityDataClass,
    CapabilityEffect,
    ExecutableTargetKind,
)
from app.contracts.command import CommandRequest
from app.contracts.execution_integration import ExecutionIntegrationOutcome


ApprovalProposalStatus: TypeAlias = Literal[
    "pending",
    "rejected",
    "unavailable",
]
OwnerDecision: TypeAlias = Literal["approved", "denied"]

_PROPOSAL_STATUSES = frozenset({"pending", "rejected", "unavailable"})
_OWNER_DECISIONS = frozenset({"approved", "denied"})


def _text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


@dataclass(frozen=True, slots=True)
class PendingExecutionApproval:
    """One process-local, single-use approval ticket."""

    approval_id: str
    request: CommandRequest
    plan_digest: str
    target_kind: ExecutableTargetKind
    capability_id: str
    effect: CapabilityEffect
    data_class: CapabilityDataClass
    owner_approval_required: bool
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        if not isinstance(self.request, CommandRequest):
            raise TypeError("request must be a CommandRequest.")
        _text(self.plan_digest, label="plan_digest")
        if len(self.plan_digest) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.plan_digest
        ):
            raise ValueError(
                "plan_digest must be a lowercase SHA-256 hex digest."
            )
        if self.target_kind not in {"tool", "module"}:
            raise ValueError("target_kind must be tool or module.")
        _text(self.capability_id, label="capability_id")
        if type(self.owner_approval_required) is not bool:
            raise ValueError(
                "owner_approval_required must be an exact bool."
            )
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("approval timestamps must be timezone-aware.")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at.")


@dataclass(frozen=True, slots=True)
class ExecutionApprovalProposal:
    """Owner-reviewable exact plan projection."""

    approval_id: str
    request_id: str
    target_kind: ExecutableTargetKind
    adapter_id: str
    operation: str
    parameters: Mapping[str, object]
    capability_id: str
    effect: CapabilityEffect
    data_class: CapabilityDataClass
    owner_approval_required: bool
    plan_digest: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ExecutionApprovalProposalOutcome:
    """Proposal result; only pending outcomes carry an approval ticket."""

    request_id: str
    status: ApprovalProposalStatus
    target_kind: ExecutableTargetKind
    reason_code: str
    proposal: ExecutionApprovalProposal | None = None

    def __post_init__(self) -> None:
        _text(self.request_id, label="request_id")
        if self.status not in _PROPOSAL_STATUSES:
            raise ValueError(
                f"Unsupported approval proposal status: {self.status!r}."
            )
        if self.target_kind not in {"tool", "module"}:
            raise ValueError("target_kind must be tool or module.")
        _text(self.reason_code, label="reason_code")
        if self.status == "pending":
            if self.proposal is None:
                raise ValueError(
                    "pending approval proposals require proposal data."
                )
        elif self.proposal is not None:
            raise ValueError(
                "non-pending approval outcomes must not carry proposal data."
            )


@dataclass(frozen=True, slots=True)
class ExecutionApprovalDecisionOutcome:
    """One consumed owner decision and its frozen-lane execution outcome."""

    approval_id: str
    decision: OwnerDecision
    execution: ExecutionIntegrationOutcome

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        if self.decision not in _OWNER_DECISIONS:
            raise ValueError(
                f"Unsupported owner decision: {self.decision!r}."
            )
        if not isinstance(self.execution, ExecutionIntegrationOutcome):
            raise TypeError(
                "execution must be an ExecutionIntegrationOutcome."
            )
