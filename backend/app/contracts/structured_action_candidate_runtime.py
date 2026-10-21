"""D173 immutable structured action candidate runtime outcome."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
)
from app.contracts.structured_action_intent_proposal import StructuredActionIntentProposal
from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)

D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION = (
    "o-ai.structured-action-candidate-runtime.v1"
)
StructuredActionCandidateRuntimeStatus: TypeAlias = Literal[
    "no_action_semantics",
    "needs_clarification",
    "unsupported",
    "intent_rejected",
    "prepared_for_owner_review",
    "approval_unavailable",
]
_STATUSES = frozenset({
    "no_action_semantics", "needs_clarification", "unsupported",
    "intent_rejected", "prepared_for_owner_review", "approval_unavailable",
})
_DOWNSTREAM = frozenset({
    "intent_rejected", "prepared_for_owner_review", "approval_unavailable",
})


def _reason(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 1024
        or any(unicodedata.category(c) == "Cc" for c in value)
    ):
        raise ValueError("structured_action_candidate_runtime_reason_invalid")
    return value


@dataclass(frozen=True, slots=True)
class StructuredActionCandidateRuntimeOutcome:
    """D173 orchestration result only; never approval or execution authority."""

    status: StructuredActionCandidateRuntimeStatus
    reason_code: str
    production: StructuredActionCandidateProductionOutcome
    proposal: StructuredActionIntentProposal | None = None
    runtime: StructuredActionProposalRuntimeOutcome | None = None
    contract_version: str = D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_candidate_runtime_status_invalid")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if not isinstance(self.production, StructuredActionCandidateProductionOutcome):
            raise ValueError("structured_action_candidate_runtime_production_invalid")
        if self.contract_version != D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION:
            raise ValueError("structured_action_candidate_runtime_contract_version_invalid")

        if self.status == "no_action_semantics":
            if (
                self.reason_code != "no_structured_action_semantics"
                or self.production.status != "not_applicable"
                or self.proposal is not None
                or self.runtime is not None
            ):
                raise ValueError("structured_action_candidate_runtime_no_semantics_invalid")
            return
        if self.status == "unsupported":
            if (
                self.reason_code != "structured_action_semantic_unsupported"
                or self.production.status != "unsupported"
                or self.proposal is not None
                or self.runtime is not None
            ):
                raise ValueError("structured_action_candidate_runtime_unsupported_invalid")
            return
        if self.status == "needs_clarification":
            if (
                self.reason_code != "structured_action_information_missing"
                or self.production.status != "needs_clarification"
                or self.production.candidate is None
                or not isinstance(self.proposal, StructuredActionIntentProposal)
                or self.proposal.status != "needs_clarification"
                or self.proposal.reason_code != "structured_action_information_missing"
                or self.runtime is not None
            ):
                raise ValueError("structured_action_candidate_runtime_clarification_invalid")
            return
        if (
            self.status not in _DOWNSTREAM
            or self.production.status != "candidate_ready"
            or self.production.candidate is None
            or not isinstance(self.proposal, StructuredActionIntentProposal)
            or self.proposal.status != "proposal_ready"
            or not isinstance(self.runtime, StructuredActionProposalRuntimeOutcome)
            or self.runtime.status != self.status
            or self.runtime.reason_code != self.reason_code
        ):
            raise ValueError("structured_action_candidate_runtime_downstream_invalid")


__all__ = [
    "D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_CONTRACT_VERSION",
    "StructuredActionCandidateRuntimeOutcome",
    "StructuredActionCandidateRuntimeStatus",
]
