"""Immutable D36 contracts for plan-bound execution authorization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.command import ExecutionPlan
from app.contracts.execution_planning import ExecutionTargetKind


ApprovalDecision: TypeAlias = Literal["approved", "denied"]
AuthorizationStatus: TypeAlias = Literal["authorized", "blocked", "rejected"]

_APPROVAL_DECISIONS = frozenset({"approved", "denied"})
_AUTHORIZATION_STATUSES = frozenset({"authorized", "blocked", "rejected"})
_TARGET_KINDS = frozenset({"ai", "tool", "module"})
_HEX = frozenset("0123456789abcdef")


def _validate_text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _validate_digest(value: str, *, label: str) -> str:
    _validate_text(value, label=label)
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest.")
    return value


@dataclass(frozen=True, slots=True)
class OwnerApprovalEvidence:
    """Trusted owner decision bound to one exact proposed execution plan."""

    request_id: str
    plan_digest: str
    decision: ApprovalDecision

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _validate_text(self.request_id, label="request_id"),
        )
        object.__setattr__(
            self,
            "plan_digest",
            _validate_digest(self.plan_digest, label="plan_digest"),
        )
        if self.decision not in _APPROVAL_DECISIONS:
            raise ValueError(f"Unsupported approval decision: {self.decision!r}.")


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    """Guard result; only authorized outcomes may carry an execution-ready plan."""

    request_id: str
    status: AuthorizationStatus
    target_kind: ExecutionTargetKind | None
    source_plan_digest: str | None
    execution_plan: ExecutionPlan | None
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _validate_text(self.request_id, label="request_id"),
        )
        if self.status not in _AUTHORIZATION_STATUSES:
            raise ValueError(
                f"Unsupported authorization status: {self.status!r}."
            )
        if self.target_kind is not None and self.target_kind not in _TARGET_KINDS:
            raise ValueError(f"Unsupported target_kind: {self.target_kind!r}.")
        if self.source_plan_digest is not None:
            object.__setattr__(
                self,
                "source_plan_digest",
                _validate_digest(
                    self.source_plan_digest,
                    label="source_plan_digest",
                ),
            )
        object.__setattr__(
            self,
            "reason_code",
            _validate_text(self.reason_code, label="reason_code"),
        )

        if self.status == "authorized":
            if self.target_kind is None:
                raise ValueError(
                    "authorized outcomes require a target_kind."
                )
            if self.source_plan_digest is None:
                raise ValueError(
                    "authorized outcomes require a source plan digest."
                )
            if self.execution_plan is None:
                raise ValueError(
                    "authorized outcomes require an execution-ready plan."
                )
            if self.execution_plan.request_id != self.request_id:
                raise ValueError(
                    "authorization request_id must match execution plan request_id."
                )
            if self.execution_plan.owner_approval_required:
                raise ValueError(
                    "authorized execution plans must not remain approval-gated."
                )
        elif self.execution_plan is not None:
            raise ValueError(
                "blocked/rejected authorizations must not include an execution plan."
            )
