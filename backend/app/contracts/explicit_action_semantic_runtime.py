"""D177 immutable explicit action semantic runtime orchestration outcome."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)


D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION = (
    "o-ai.explicit-action-semantic-runtime.v1"
)

ExplicitActionSemanticRuntimeStatus: TypeAlias = Literal[
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
_DOWNSTREAM = frozenset(
    {
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


@dataclass(frozen=True, slots=True)
class ExplicitActionSemanticRuntimeOutcome:
    """D177 orchestration result only; never inference, approval, or execution."""

    status: ExplicitActionSemanticRuntimeStatus
    reason_code: str
    production: ExplicitActionSemanticDraftProductionOutcome
    runtime: StructuredActionSemanticRuntimeOutcome | None = None
    contract_version: str = D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("explicit_action_semantic_runtime_status_invalid")
        if not isinstance(
            self.production,
            ExplicitActionSemanticDraftProductionOutcome,
        ):
            raise ValueError("explicit_action_semantic_runtime_production_invalid")
        if (
            self.contract_version
            != D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION
        ):
            raise ValueError("explicit_action_semantic_runtime_version_invalid")

        if self.status == "not_applicable":
            if (
                self.reason_code != "no_explicit_action_directive"
                or self.production.status != "not_applicable"
                or self.runtime is not None
            ):
                raise ValueError(
                    "explicit_action_semantic_runtime_not_applicable_invalid"
                )
            return

        if self.status == "invalid":
            if (
                self.reason_code != "explicit_action_directive_invalid"
                or self.production.status != "invalid"
                or self.runtime is not None
            ):
                raise ValueError("explicit_action_semantic_runtime_invalid_invalid")
            return

        if (
            self.status not in _DOWNSTREAM
            or self.production.status != "semantic_ready"
            or self.production.draft is None
            or not isinstance(self.runtime, StructuredActionSemanticRuntimeOutcome)
            or self.runtime.status != self.status
            or self.runtime.reason_code != self.reason_code
        ):
            raise ValueError("explicit_action_semantic_runtime_downstream_invalid")


__all__ = [
    "D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_CONTRACT_VERSION",
    "ExplicitActionSemanticRuntimeOutcome",
    "ExplicitActionSemanticRuntimeStatus",
]
