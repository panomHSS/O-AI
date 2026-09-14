"""Immutable D39 contracts for safe execution observability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol, TypeAlias, runtime_checkable

from app.contracts.execution_planning import ExecutionTargetKind


EXECUTION_AUDIT_CONTRACT_VERSION = "1"

AuditStage: TypeAlias = Literal["planning", "authorization", "execution"]
AuditAction: TypeAlias = Literal["started", "completed"]
AuditStatus: TypeAlias = Literal[
    "planned",
    "rejected",
    "unavailable",
    "authorized",
    "blocked",
    "started",
    "succeeded",
    "failed",
]

_STAGES = frozenset({"planning", "authorization", "execution"})
_ACTIONS = frozenset({"started", "completed"})
_STATUSES = frozenset(
    {
        "planned",
        "rejected",
        "unavailable",
        "authorized",
        "blocked",
        "started",
        "succeeded",
        "failed",
    }
)
_TARGET_KINDS = frozenset({"ai", "tool", "module"})
_HEX = frozenset("0123456789abcdef")


def _validate_text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _validate_optional_text(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    return _validate_text(value, label=label)


def _validate_digest(value: str | None) -> str | None:
    if value is None:
        return None
    _validate_text(value, label="plan_digest")
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise ValueError("plan_digest must be a lowercase SHA-256 hex digest.")
    return value


@dataclass(frozen=True, slots=True)
class ExecutionAuditEvent:
    """One allowlisted observation about planning, authorization, or execution."""

    request_id: str
    stage: AuditStage
    action: AuditAction
    status: AuditStatus
    occurred_at: datetime
    target_kind: ExecutionTargetKind | None = None
    adapter_id: str | None = None
    reason_code: str | None = None
    plan_digest: str | None = None
    contract_version: str = EXECUTION_AUDIT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _validate_text(self.request_id, label="request_id"),
        )
        if self.stage not in _STAGES:
            raise ValueError(f"Unsupported audit stage: {self.stage!r}.")
        if self.action not in _ACTIONS:
            raise ValueError(f"Unsupported audit action: {self.action!r}.")
        if self.status not in _STATUSES:
            raise ValueError(f"Unsupported audit status: {self.status!r}.")
        if self.target_kind is not None and self.target_kind not in _TARGET_KINDS:
            raise ValueError(f"Unsupported target_kind: {self.target_kind!r}.")
        object.__setattr__(
            self,
            "adapter_id",
            _validate_optional_text(self.adapter_id, label="adapter_id"),
        )
        object.__setattr__(
            self,
            "reason_code",
            _validate_optional_text(self.reason_code, label="reason_code"),
        )
        object.__setattr__(
            self,
            "plan_digest",
            _validate_digest(self.plan_digest),
        )
        if not isinstance(self.occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime.")
        offset = self.occurred_at.utcoffset()
        if offset is None or offset != timedelta(0):
            raise ValueError("occurred_at must be timezone-aware UTC.")
        if self.contract_version != EXECUTION_AUDIT_CONTRACT_VERSION:
            raise ValueError("Unsupported execution audit contract version.")

        if self.stage in {"planning", "authorization"} and self.action != "completed":
            raise ValueError(
                "planning and authorization audit events must be completed actions."
            )
        if self.stage == "execution":
            if self.action == "started" and self.status != "started":
                raise ValueError(
                    "execution started events require status='started'."
                )
            if self.action == "completed" and self.status == "started":
                raise ValueError(
                    "execution completed events cannot use status='started'."
                )


@runtime_checkable
class AuditSink(Protocol):
    """Destination for immutable, allowlisted execution audit events."""

    def record(self, event: ExecutionAuditEvent) -> None:
        ...
