"""D179 immutable D178 -> D177 cognitive handoff outcome contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)


D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION = (
    "o-ai.explicit-action-cognitive-handoff.v1"
)

ExplicitActionCognitiveHandoffStatus: TypeAlias = Literal[
    "cognitive_outcome_unavailable",
    "not_applicable",
    "invalid",
    "lineage_unavailable",
    "needs_clarification",
    "unsupported",
    "intent_rejected",
    "prepared_for_owner_review",
    "approval_unavailable",
]

_STATUSES = frozenset(
    {
        "cognitive_outcome_unavailable",
        "not_applicable",
        "invalid",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


@dataclass(frozen=True, slots=True)
class ExplicitActionCognitiveHandoffOutcome:
    """D179 handoff result only; never lineage, approval, or execution authority."""

    status: ExplicitActionCognitiveHandoffStatus
    reason_code: str
    runtime: ExplicitActionSemanticRuntimeOutcome | None = None
    contract_version: str = D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("explicit_action_cognitive_handoff_status_invalid")
        if (
            self.contract_version
            != D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION
        ):
            raise ValueError("explicit_action_cognitive_handoff_version_invalid")

        if self.status == "cognitive_outcome_unavailable":
            if (
                self.reason_code != "cognitive_outcome_unavailable"
                or self.runtime is not None
            ):
                raise ValueError(
                    "explicit_action_cognitive_handoff_unavailable_invalid"
                )
            return

        if not isinstance(self.runtime, ExplicitActionSemanticRuntimeOutcome):
            raise ValueError("explicit_action_cognitive_handoff_runtime_invalid")
        if (
            self.runtime.status != self.status
            or self.runtime.reason_code != self.reason_code
        ):
            raise ValueError("explicit_action_cognitive_handoff_runtime_mismatch")


__all__ = [
    "D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_CONTRACT_VERSION",
    "ExplicitActionCognitiveHandoffOutcome",
    "ExplicitActionCognitiveHandoffStatus",
]
