"""D175 immutable structured action semantic runtime orchestration outcome."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageOutcome,
)


D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION = (
    "o-ai.structured-action-semantic-runtime.v1"
)

StructuredActionSemanticRuntimeStatus: TypeAlias = Literal[
    "not_applicable",
    "lineage_unavailable",
    "needs_clarification",
    "unsupported",
    "intent_rejected",
    "prepared_for_owner_review",
    "approval_unavailable",
]

_STATUSES = frozenset(
    {
        "not_applicable",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)
_DOWNSTREAM = frozenset(
    {
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
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
        raise ValueError("structured_action_semantic_runtime_reason_invalid")
    return value


@dataclass(frozen=True, slots=True)
class StructuredActionSemanticRuntimeOutcome:
    """D175 orchestration result only; never inference, approval, or execution."""

    status: StructuredActionSemanticRuntimeStatus
    reason_code: str
    lineage: StructuredActionSemanticLineageOutcome
    runtime: StructuredActionCandidateRuntimeOutcome | None = None
    contract_version: str = (
        D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_semantic_runtime_status_invalid")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if not isinstance(self.lineage, StructuredActionSemanticLineageOutcome):
            raise ValueError("structured_action_semantic_runtime_lineage_invalid")
        if (
            self.contract_version
            != D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION
        ):
            raise ValueError("structured_action_semantic_runtime_version_invalid")

        if self.status == "not_applicable":
            if (
                self.reason_code != "no_structured_action_semantic_draft"
                or self.lineage.status != "not_applicable"
                or self.runtime is not None
            ):
                raise ValueError(
                    "structured_action_semantic_runtime_not_applicable_invalid"
                )
            return

        if self.status == "lineage_unavailable":
            if (
                self.reason_code != "current_cognitive_publication_unavailable"
                or self.lineage.status != "lineage_unavailable"
                or self.runtime is not None
            ):
                raise ValueError(
                    "structured_action_semantic_runtime_lineage_unavailable_invalid"
                )
            return

        if (
            self.status not in _DOWNSTREAM
            or self.lineage.status != "semantic_ready"
            or self.lineage.semantic is None
            or not isinstance(self.runtime, StructuredActionCandidateRuntimeOutcome)
            or self.runtime.status != self.status
            or self.runtime.reason_code != self.reason_code
        ):
            raise ValueError(
                "structured_action_semantic_runtime_downstream_invalid"
            )


__all__ = [
    "D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION",
    "StructuredActionSemanticRuntimeOutcome",
    "StructuredActionSemanticRuntimeStatus",
]
