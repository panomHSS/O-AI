"""D148 immutable Trusted Experience Retrieval / Evidence Selection V1 contracts."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.cognitive_brain import COGNITIVE_REVISION_COUNT_MAX
from app.contracts.cognitive_input_semantics import (
    CognitiveInteractionIntent,
    CognitiveIntent,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId

D148_REFERENCE_BASELINE = "255ac4916a095b27c8d72b4f99fb2e0b84d829cc"
D148_CONTRACT_VERSION = "1"
D148_MAX_EVIDENCE = 16
D148_SELECTION_POLICY = "exact_task_kind_then_intent_tiers_v1"

CognitiveTrustedExperienceRelevanceTier: TypeAlias = Literal[0, 1, 2, 3]

_INTERACTION_INTENTS = frozenset(
    {
        "chat",
        "action_request",
        "approval_related_input",
        "runtime_status_request",
        "unknown",
    }
)
_COGNITIVE_INTENTS = frozenset(
    {
        "factual_lookup",
        "explanation",
        "comparison",
        "procedure",
        "troubleshooting",
        "summary",
        "general",
    }
)
_CONFIDENCE_CLASSES = frozenset(
    {"sufficient", "limited", "insufficient", "unknown"}
)
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "prompt_mutation_authority",
    "policy_mutation_authority",
    "automatic_learning",
    "automatic_promotion",
)


def _bounded_identifier(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > 512 or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(code)
    return value


def _validate_query_fields(
    *,
    workspace_id: object,
    interaction_intent: object,
    cognitive_intent: object,
    authoritative_ai_task_kind: object,
) -> None:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("trusted_experience_retrieval_workspace_invalid")
    if (
        type(interaction_intent) is not str
        or interaction_intent not in _INTERACTION_INTENTS
    ):
        raise ValueError("trusted_experience_retrieval_interaction_intent_invalid")
    if type(cognitive_intent) is not str or cognitive_intent not in _COGNITIVE_INTENTS:
        raise ValueError("trusted_experience_retrieval_cognitive_intent_invalid")
    if not isinstance(authoritative_ai_task_kind, AITaskKind):
        raise ValueError("trusted_experience_retrieval_task_kind_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceRetrievalQuery:
    """Server-owned structured D148 retrieval query; never behavioral authority."""

    workspace_id: WorkspaceId
    interaction_intent: CognitiveInteractionIntent
    cognitive_intent: CognitiveIntent
    authoritative_ai_task_kind: AITaskKind

    def __post_init__(self) -> None:
        _validate_query_fields(
            workspace_id=self.workspace_id,
            interaction_intent=self.interaction_intent,
            cognitive_intent=self.cognitive_intent,
            authoritative_ai_task_kind=self.authoritative_ai_task_kind,
        )


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceEvidence:
    """One privacy-minimized D148 evidence item projected from a TRUSTED D147 root."""

    trusted_experience_id: UUID
    proposal_fingerprint: str
    interaction_intent: CognitiveInteractionIntent
    cognitive_intent: CognitiveIntent
    authoritative_ai_task_kind: AITaskKind
    observed_confidence_class: str
    authorized_adapter_id: str | None
    authorized_model_id: str | None
    authorized_profile_id: str | None
    source_revision_count: int

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if not isinstance(self.trusted_experience_id, UUID):
            raise ValueError("trusted_experience_evidence_id_invalid")
        if (
            type(self.proposal_fingerprint) is not str
            or _SHA256_HEX.fullmatch(self.proposal_fingerprint) is None
        ):
            raise ValueError("trusted_experience_evidence_fingerprint_invalid")
        _validate_query_fields(
            workspace_id=WorkspaceId.PERSONAL,
            interaction_intent=self.interaction_intent,
            cognitive_intent=self.cognitive_intent,
            authoritative_ai_task_kind=self.authoritative_ai_task_kind,
        )
        if (
            type(self.observed_confidence_class) is not str
            or self.observed_confidence_class not in _CONFIDENCE_CLASSES
        ):
            raise ValueError("trusted_experience_evidence_confidence_invalid")
        _bounded_identifier(
            self.authorized_adapter_id,
            code="trusted_experience_evidence_adapter_invalid",
        )
        _bounded_identifier(
            self.authorized_model_id,
            code="trusted_experience_evidence_model_invalid",
        )
        _bounded_identifier(
            self.authorized_profile_id,
            code="trusted_experience_evidence_profile_invalid",
        )
        if (
            type(self.source_revision_count) is not int
            or isinstance(self.source_revision_count, bool)
            or not 0 <= self.source_revision_count <= COGNITIVE_REVISION_COUNT_MAX
        ):
            raise ValueError("trusted_experience_evidence_revision_invalid")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"trusted_experience_evidence_{name}_invalid")


def compute_cognitive_trusted_experience_evidence_set_fingerprint(
    *,
    query: CognitiveTrustedExperienceRetrievalQuery,
    evidence: Sequence[CognitiveTrustedExperienceEvidence],
) -> str:
    """Hash only frozen query semantics and ordered D147 evidence identities."""

    if type(query) is not CognitiveTrustedExperienceRetrievalQuery:
        raise ValueError("trusted_experience_evidence_query_invalid")
    if isinstance(evidence, (str, bytes, bytearray)) or not isinstance(
        evidence, Sequence
    ):
        raise ValueError("trusted_experience_evidence_items_invalid")
    items = tuple(evidence)
    if len(items) > D148_MAX_EVIDENCE:
        raise ValueError("trusted_experience_evidence_items_invalid")
    for item in items:
        if type(item) is not CognitiveTrustedExperienceEvidence:
            raise ValueError("trusted_experience_evidence_items_invalid")

    payload = {
        "contract_version": D148_CONTRACT_VERSION,
        "workspace_id": query.workspace_id.value,
        "query": {
            "interaction_intent": query.interaction_intent,
            "cognitive_intent": query.cognitive_intent,
            "authoritative_ai_task_kind": query.authoritative_ai_task_kind.value,
        },
        "selection_policy": D148_SELECTION_POLICY,
        "ordered_evidence": [
            {
                "trusted_experience_id": str(item.trusted_experience_id),
                "proposal_fingerprint": item.proposal_fingerprint,
            }
            for item in items
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceEvidenceSet:
    """Bounded D148 read-only evidence selection result."""

    workspace_id: WorkspaceId
    query: CognitiveTrustedExperienceRetrievalQuery
    evidence: tuple[CognitiveTrustedExperienceEvidence, ...]
    selected_count: int
    truncated: bool
    evidence_set_fingerprint: str

    contract_version: Literal["1"] = D148_CONTRACT_VERSION
    reference_baseline: str = D148_REFERENCE_BASELINE
    selection_policy: str = D148_SELECTION_POLICY
    max_evidence: int = D148_MAX_EVIDENCE

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D148_CONTRACT_VERSION:
            raise ValueError("trusted_experience_evidence_contract_version_invalid")
        if self.reference_baseline != D148_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_evidence_baseline_invalid")
        if self.selection_policy != D148_SELECTION_POLICY:
            raise ValueError("trusted_experience_evidence_policy_invalid")
        if self.max_evidence != D148_MAX_EVIDENCE:
            raise ValueError("trusted_experience_evidence_max_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("trusted_experience_evidence_workspace_invalid")
        if type(self.query) is not CognitiveTrustedExperienceRetrievalQuery:
            raise ValueError("trusted_experience_evidence_query_invalid")
        if self.query.workspace_id is not self.workspace_id:
            raise ValueError("trusted_experience_evidence_workspace_mismatch")
        if type(self.evidence) is not tuple or len(self.evidence) > D148_MAX_EVIDENCE:
            raise ValueError("trusted_experience_evidence_items_invalid")
        if any(
            type(item) is not CognitiveTrustedExperienceEvidence
            for item in self.evidence
        ):
            raise ValueError("trusted_experience_evidence_items_invalid")
        ids = tuple(item.trusted_experience_id for item in self.evidence)
        if len(set(ids)) != len(ids):
            raise ValueError("trusted_experience_evidence_duplicate_id")
        if (
            type(self.selected_count) is not int
            or isinstance(self.selected_count, bool)
            or self.selected_count != len(self.evidence)
        ):
            raise ValueError("trusted_experience_evidence_count_invalid")
        if type(self.truncated) is not bool:
            raise ValueError("trusted_experience_evidence_truncated_invalid")
        if self.truncated and self.selected_count != D148_MAX_EVIDENCE:
            raise ValueError("trusted_experience_evidence_truncated_invalid")
        expected = compute_cognitive_trusted_experience_evidence_set_fingerprint(
            query=self.query,
            evidence=self.evidence,
        )
        if self.evidence_set_fingerprint != expected:
            raise ValueError("trusted_experience_evidence_set_fingerprint_mismatch")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"trusted_experience_evidence_{name}_invalid")


__all__ = [
    "D148_CONTRACT_VERSION",
    "D148_MAX_EVIDENCE",
    "D148_REFERENCE_BASELINE",
    "D148_SELECTION_POLICY",
    "CognitiveTrustedExperienceEvidence",
    "CognitiveTrustedExperienceEvidenceSet",
    "CognitiveTrustedExperienceRelevanceTier",
    "CognitiveTrustedExperienceRetrievalQuery",
    "compute_cognitive_trusted_experience_evidence_set_fingerprint",
]
