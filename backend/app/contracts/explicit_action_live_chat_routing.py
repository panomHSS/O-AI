"""D180 immutable live Chat projection for the D179 cognitive handoff."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.execution_approval import ExecutionApprovalProposalOutcome
from app.contracts.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffOutcome,
)


D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION = (
    "o-ai.explicit-action-live-chat-routing.v1"
)

ExplicitActionLiveChatProjectionStatus: TypeAlias = Literal[
    "pending_approval",
    "rejected",
    "unavailable",
]

_STATUSES = frozenset({"pending_approval", "rejected", "unavailable"})
_REJECTED_HANDOFF_STATUSES = frozenset(
    {
        "not_applicable",
        "invalid",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
    }
)
_UNAVAILABLE_HANDOFF_STATUSES = frozenset(
    {
        "cognitive_outcome_unavailable",
        "lineage_unavailable",
        "approval_unavailable",
    }
)


def _reason(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 1024
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError("explicit_action_live_chat_reason_invalid")
    return value


@dataclass(frozen=True, slots=True)
class ExplicitActionLiveChatProjectionOutcome:
    """Presentation projection only; never permission, approval, or execution."""

    status: ExplicitActionLiveChatProjectionStatus
    reason_code: str
    approval: ExecutionApprovalProposalOutcome | None
    handoff: ExplicitActionCognitiveHandoffOutcome
    contract_version: str = (
        D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("explicit_action_live_chat_status_invalid")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if not isinstance(self.handoff, ExplicitActionCognitiveHandoffOutcome):
            raise ValueError("explicit_action_live_chat_handoff_invalid")
        if (
            self.contract_version
            != D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION
        ):
            raise ValueError("explicit_action_live_chat_version_invalid")
        if self.reason_code != self.handoff.reason_code:
            raise ValueError("explicit_action_live_chat_reason_mismatch")

        if self.status == "pending_approval":
            if (
                self.handoff.status != "prepared_for_owner_review"
                or not isinstance(
                    self.approval,
                    ExecutionApprovalProposalOutcome,
                )
                or self.approval.status != "pending"
                or self.approval.proposal is None
            ):
                raise ValueError(
                    "explicit_action_live_chat_pending_projection_invalid"
                )
            return

        if self.approval is not None:
            raise ValueError(
                "explicit_action_live_chat_nonpending_approval_invalid"
            )

        expected = (
            _REJECTED_HANDOFF_STATUSES
            if self.status == "rejected"
            else _UNAVAILABLE_HANDOFF_STATUSES
        )
        if self.handoff.status not in expected:
            raise ValueError(
                "explicit_action_live_chat_projection_status_mismatch"
            )


__all__ = [
    "D180_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_CONTRACT_VERSION",
    "ExplicitActionLiveChatProjectionOutcome",
    "ExplicitActionLiveChatProjectionStatus",
]
