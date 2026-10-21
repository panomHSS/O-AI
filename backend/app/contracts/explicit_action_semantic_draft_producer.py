"""D176 immutable explicit action semantic draft producer contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.structured_action_semantic_lineage import StructuredActionSemanticDraft

D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION = (
    "o-ai.explicit-action-semantic-draft-producer.v1"
)

ExplicitActionSemanticDraftProductionStatus: TypeAlias = Literal[
    "not_applicable",
    "invalid",
    "semantic_ready",
]

_STATUSES = frozenset({"not_applicable", "invalid", "semantic_ready"})
_REASONS = {
    "not_applicable": "no_explicit_action_directive",
    "invalid": "explicit_action_directive_invalid",
    "semantic_ready": "structured_action_semantic_draft_ready",
}


@dataclass(frozen=True, slots=True)
class ExplicitActionSemanticDraftProductionOutcome:
    """D176 parsing result only; never lineage, routing, approval, or execution."""

    status: ExplicitActionSemanticDraftProductionStatus
    reason_code: str
    draft: StructuredActionSemanticDraft | None = None
    contract_version: str = D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("explicit_action_semantic_draft_status_invalid")
        if self.reason_code != _REASONS[self.status]:
            raise ValueError("explicit_action_semantic_draft_reason_invalid")
        if self.contract_version != D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION:
            raise ValueError("explicit_action_semantic_draft_version_invalid")

        if self.status == "semantic_ready":
            if not isinstance(self.draft, StructuredActionSemanticDraft):
                raise ValueError("explicit_action_semantic_draft_required")
            return

        if self.draft is not None:
            raise ValueError("explicit_action_semantic_draft_forbidden")


__all__ = [
    "D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_CONTRACT_VERSION",
    "ExplicitActionSemanticDraftProductionOutcome",
    "ExplicitActionSemanticDraftProductionStatus",
]
