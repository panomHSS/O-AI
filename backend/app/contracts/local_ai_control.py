"""Immutable D103 Local AI configured-model control contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

LOCAL_AI_CONTROL_CONTRACT_VERSION = "1"
LocalAIControlOperation: TypeAlias = Literal[
    "load_configured_model", "unload_configured_model"
]
LocalAIControlDecision: TypeAlias = Literal["approved", "denied"]
_OPERATIONS = frozenset({"load_configured_model", "unload_configured_model"})
_DECISIONS = frozenset({"approved", "denied"})


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string.")
    return value


def _digest(value: object) -> str:
    digest = _text(value, label="control_digest")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("control_digest must be lowercase SHA-256 hex.")
    return digest


def _aware(value: object, *, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware.")
    return value


def _bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be an exact bool.")
    return value


@dataclass(frozen=True, slots=True)
class LocalAIControlPreview:
    contract_version: Literal["1"]
    operation: LocalAIControlOperation
    backend_id: str
    configured_model_id: str
    expected_loaded_state: bool
    desired_loaded_state: bool

    def __post_init__(self) -> None:
        if self.contract_version != LOCAL_AI_CONTROL_CONTRACT_VERSION:
            raise ValueError("Unsupported Local AI control contract version.")
        if self.operation not in _OPERATIONS:
            raise ValueError("Unsupported Local AI control operation.")
        object.__setattr__(self, "backend_id", _text(self.backend_id, label="backend_id"))
        object.__setattr__(
            self,
            "configured_model_id",
            _text(self.configured_model_id, label="configured_model_id"),
        )
        expected = _bool(self.expected_loaded_state, label="expected_loaded_state")
        desired = _bool(self.desired_loaded_state, label="desired_loaded_state")
        if self.operation == "load_configured_model":
            if expected is not False or desired is not True:
                raise ValueError("Load requires False -> True.")
        elif expected is not True or desired is not False:
            raise ValueError("Unload requires True -> False.")


@dataclass(frozen=True, slots=True)
class PendingLocalAIControlApproval:
    approval_id: str
    control_digest: str
    preview: LocalAIControlPreview
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        _digest(self.control_digest)
        if not isinstance(self.preview, LocalAIControlPreview):
            raise TypeError("preview must be LocalAIControlPreview.")
        created = _aware(self.created_at, label="created_at")
        expires = _aware(self.expires_at, label="expires_at")
        if expires <= created:
            raise ValueError("expires_at must be later than created_at.")


@dataclass(frozen=True, slots=True)
class ApprovedLocalAIControlApproval:
    approval_id: str
    control_digest: str
    preview: LocalAIControlPreview
    approved_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        _digest(self.control_digest)
        if not isinstance(self.preview, LocalAIControlPreview):
            raise TypeError("preview must be LocalAIControlPreview.")
        approved = _aware(self.approved_at, label="approved_at")
        expires = _aware(self.expires_at, label="expires_at")
        if expires <= approved:
            raise ValueError("expires_at must be later than approved_at.")


@dataclass(frozen=True, slots=True)
class LocalAIControlProposal:
    approval_id: str
    control_digest: str
    preview: LocalAIControlPreview
    expires_at: datetime

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        _digest(self.control_digest)
        if not isinstance(self.preview, LocalAIControlPreview):
            raise TypeError("preview must be LocalAIControlPreview.")
        _aware(self.expires_at, label="expires_at")


@dataclass(frozen=True, slots=True)
class LocalAIControlProposalOutcome:
    status: Literal["pending"]
    reason_code: str
    proposal: LocalAIControlProposal

    def __post_init__(self) -> None:
        if self.status != "pending":
            raise ValueError("proposal status must be pending.")
        _text(self.reason_code, label="reason_code")
        if not isinstance(self.proposal, LocalAIControlProposal):
            raise TypeError("proposal must be LocalAIControlProposal.")


@dataclass(frozen=True, slots=True)
class LocalAIControlDecisionOutcome:
    approval_id: str
    decision: LocalAIControlDecision
    reason_code: str
    control_digest: str
    preview: LocalAIControlPreview
    expires_at: datetime
    approved: ApprovedLocalAIControlApproval | None = None

    def __post_init__(self) -> None:
        _text(self.approval_id, label="approval_id")
        if self.decision not in _DECISIONS:
            raise ValueError("decision must be approved or denied.")
        _text(self.reason_code, label="reason_code")
        _digest(self.control_digest)
        if not isinstance(self.preview, LocalAIControlPreview):
            raise TypeError("preview must be LocalAIControlPreview.")
        _aware(self.expires_at, label="expires_at")
        if self.decision == "approved" and self.approved is None:
            raise ValueError("approved decision requires approved snapshot.")
        if self.decision == "denied" and self.approved is not None:
            raise ValueError("denied decision must not carry approved snapshot.")
