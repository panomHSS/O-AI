"""D46 immutable contracts for deterministic Chat -> Action bridging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, TypeAlias
from uuid import UUID

from app.contracts.capability_permission import ExecutableTargetKind
from app.contracts.execution_approval import ExecutionApprovalProposalOutcome


ChatActionStatus: TypeAlias = Literal[
    "pending_approval",
    "rejected",
    "unavailable",
]

_CHAT_ACTION_STATUSES = frozenset(
    {"pending_approval", "rejected", "unavailable"}
)


@dataclass(frozen=True, slots=True)
class ChatActionDirective:
    """One deterministic mapping from explicit chat syntax to a D45 proposal."""

    target_kind: ExecutableTargetKind
    adapter_id: str
    operation: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    requires_project_context: bool = False

    def __post_init__(self) -> None:
        if self.target_kind not in {"tool", "module"}:
            raise ValueError("target_kind must be tool or module.")
        for label, value in (
            ("adapter_id", self.adapter_id),
            ("operation", self.operation),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise ValueError(
                    f"{label} must be a non-empty trimmed string."
                )
        if type(self.requires_project_context) is not bool:
            raise ValueError(
                "requires_project_context must be an exact bool."
            )


@dataclass(frozen=True, slots=True)
class ChatActionBridgeOutcome:
    """Presentation-neutral result of handling one explicit action chat turn."""

    reply: str
    conversation_id: UUID
    status: ChatActionStatus
    reason_code: str
    approval: ExecutionApprovalProposalOutcome | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.reply, str)
            or not self.reply
            or self.reply != self.reply.strip()
        ):
            raise ValueError("reply must be a non-empty trimmed string.")
        if not isinstance(self.conversation_id, UUID):
            raise TypeError("conversation_id must be a UUID.")
        if self.status not in _CHAT_ACTION_STATUSES:
            raise ValueError(
                f"Unsupported chat action status: {self.status!r}."
            )
        if (
            not isinstance(self.reason_code, str)
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError(
                "reason_code must be a non-empty trimmed string."
            )
        if self.status == "pending_approval":
            if (
                self.approval is None
                or self.approval.status != "pending"
                or self.approval.proposal is None
            ):
                raise ValueError(
                    "pending_approval requires a pending D45 proposal."
                )
        elif self.approval is not None:
            raise ValueError(
                "non-pending chat actions must not expose approval data."
            )
