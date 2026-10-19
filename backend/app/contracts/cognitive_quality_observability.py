"""D156 immutable Longitudinal Cognitive Quality Observability V1 contracts."""
from __future__ import annotations

import hashlib, json, re, unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import COGNITIVE_REVISION_COUNT_MAX, CognitiveTurnState
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId

D156_REFERENCE_BASELINE = "a35465ba018e0f55b4320e02e2eff6c32b8cd7ca"
D156_CONTRACT_VERSION = "1"
D156_TURN_DIGEST_DOMAIN = "o-ai.d156.cognitive-quality.turn.v1"
D156_PROJECTION_FINGERPRINT_VERSION = "o-ai.d156.cognitive-quality.projection.v1"

CognitiveQualityClassification: TypeAlias = Literal["verified_success","bounded_insufficiency","adverse_outcome","invalid_evidence"]
CognitiveQualityReasonCode: TypeAlias = Literal["verified_success","bounded_insufficiency","critic_exhausted","invalid_cognition","terminal_failure","invalid_experience_candidate"]
CognitiveQualityExperienceCohort: TypeAlias = Literal["verification_active","reasoning_active","projected","restricted","no_evidence","unavailable","absent","not_evaluated"]

_VALID_RC = {
    ("verified_success", "verified_success"),
    ("bounded_insufficiency", "bounded_insufficiency"),
    ("critic_exhausted", "adverse_outcome"),
    ("invalid_cognition", "adverse_outcome"),
    ("terminal_failure", "adverse_outcome"),
    ("invalid_experience_candidate", "invalid_evidence"),
}
_VER = {"pass","revise","insufficient_evidence","invalid_cognition"}
_PUB = {"eligible","bounded_insufficiency_only","revision_required","blocked"}
_CONF = {"sufficient","limited","insufficient","unknown"}
_COHORT = {"verification_active","reasoning_active","projected","restricted","no_evidence","unavailable","absent","not_evaluated"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _digest(v: object, code: str) -> str:
    if type(v) is not str or _SHA.fullmatch(v) is None:
        raise ValueError(code)
    return v


def _opt_digest(v: object, code: str) -> str | None:
    return None if v is None else _digest(v, code)


def _opt_id(v: object, code: str) -> str | None:
    if v is None:
        return None
    if type(v) is not str or not v or v != v.strip() or len(v.encode("utf-8")) > 512:
        raise ValueError(code)
    if any(unicodedata.category(ch) == "Cc" for ch in v):
        raise ValueError(code)
    return v


def cognitive_quality_turn_digest(*, workspace_id: WorkspaceId, turn_id: str) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("cognitive_quality_workspace_invalid")
    if type(turn_id) is not str or not turn_id or turn_id != turn_id.strip() or len(turn_id.encode("utf-8")) > 512:
        raise ValueError("cognitive_quality_turn_id_invalid")
    return hashlib.sha256(f"{workspace_id.value}\n{turn_id}\n{D156_TURN_DIGEST_DOMAIN}".encode()).hexdigest()


def compute_cognitive_quality_projection_fingerprint(**kwargs) -> str:
    turn_digest = _digest(kwargs["turn_digest"], "cognitive_quality_turn_digest_invalid")
    workspace_id = kwargs["workspace_id"]
    terminal_state = kwargs["terminal_state"]
    if not isinstance(workspace_id, WorkspaceId): raise ValueError("cognitive_quality_workspace_invalid")
    if terminal_state not in {CognitiveTurnState.COMPLETED,CognitiveTurnState.INSUFFICIENT,CognitiveTurnState.FAILED}: raise ValueError("cognitive_quality_terminal_state_invalid")
    classification = kwargs["quality_classification"]
    reason = kwargs["quality_reason_code"]
    if (reason, classification) not in _VALID_RC: raise ValueError("cognitive_quality_reason_classification_invalid")
    verification_result = kwargs.get("verification_result")
    publication_disposition = kwargs.get("publication_disposition")
    critic_exhausted = kwargs.get("critic_exhausted")
    revision_count = kwargs["revision_count"]
    confidence_class = kwargs.get("confidence_class")
    cohort = kwargs["experience_cohort"]
    task_kind = kwargs.get("authoritative_ai_task_kind")
    if verification_result is not None and verification_result not in _VER: raise ValueError("cognitive_quality_verification_invalid")
    if publication_disposition is not None and publication_disposition not in _PUB: raise ValueError("cognitive_quality_publication_invalid")
    if critic_exhausted is not None and type(critic_exhausted) is not bool: raise ValueError("cognitive_quality_critic_exhausted_invalid")
    if type(revision_count) is not int or not 0 <= revision_count <= COGNITIVE_REVISION_COUNT_MAX: raise ValueError("cognitive_quality_revision_invalid")
    if confidence_class is not None and confidence_class not in _CONF: raise ValueError("cognitive_quality_confidence_invalid")
    if cohort not in _COHORT: raise ValueError("cognitive_quality_cohort_invalid")
    if task_kind is not None and not isinstance(task_kind, AITaskKind): raise ValueError("cognitive_quality_task_kind_invalid")
    for key in ("adapter_id","model_id","profile_id"):
        _opt_id(kwargs.get(key), f"cognitive_quality_{key}_invalid")
    _opt_digest(kwargs.get("source_candidate_fingerprint"), "cognitive_quality_candidate_fingerprint_invalid")
    _opt_digest(kwargs.get("source_feedback_fingerprint"), "cognitive_quality_feedback_fingerprint_invalid")
    payload = {
        "fingerprint_version": D156_PROJECTION_FINGERPRINT_VERSION,
        "turn_digest": turn_digest,
        "workspace_id": workspace_id.value,
        "terminal_state": terminal_state.value,
        "interaction_intent": kwargs.get("interaction_intent"),
        "cognitive_intent": kwargs.get("cognitive_intent"),
        "authoritative_ai_task_kind": task_kind.value if task_kind is not None else None,
        "quality_classification": classification,
        "quality_reason_code": reason,
        "verification_result": verification_result,
        "publication_disposition": publication_disposition,
        "critic_exhausted": critic_exhausted,
        "revision_count": revision_count,
        "confidence_class": confidence_class,
        "experience_cohort": cohort,
        "adapter_id": kwargs.get("adapter_id"),
        "model_id": kwargs.get("model_id"),
        "profile_id": kwargs.get("profile_id"),
        "source_candidate_fingerprint": kwargs.get("source_candidate_fingerprint"),
        "source_feedback_fingerprint": kwargs.get("source_feedback_fingerprint"),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveQualityObservation:
    turn_digest: str
    workspace_id: WorkspaceId
    terminal_state: CognitiveTurnState
    interaction_intent: str | None
    cognitive_intent: str | None
    authoritative_ai_task_kind: AITaskKind | None
    quality_classification: CognitiveQualityClassification
    quality_reason_code: CognitiveQualityReasonCode
    verification_result: str | None
    publication_disposition: str | None
    critic_exhausted: bool | None
    revision_count: int
    confidence_class: str | None
    experience_cohort: CognitiveQualityExperienceCohort
    adapter_id: str | None
    model_id: str | None
    profile_id: str | None
    source_candidate_fingerprint: str | None
    source_feedback_fingerprint: str | None
    projection_fingerprint: str
    occurred_at: datetime
    contract_version: Literal["1"] = D156_CONTRACT_VERSION
    reference_baseline: str = D156_REFERENCE_BASELINE
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    experience_trust_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    context_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    benchmark_promotion_authority: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D156_CONTRACT_VERSION or self.reference_baseline != D156_REFERENCE_BASELINE:
            raise ValueError("cognitive_quality_contract_invalid")
        if not isinstance(self.occurred_at, datetime) or self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("cognitive_quality_occurred_at_invalid")
        expected = compute_cognitive_quality_projection_fingerprint(
            turn_digest=self.turn_digest, workspace_id=self.workspace_id, terminal_state=self.terminal_state,
            interaction_intent=self.interaction_intent, cognitive_intent=self.cognitive_intent,
            authoritative_ai_task_kind=self.authoritative_ai_task_kind, quality_classification=self.quality_classification,
            quality_reason_code=self.quality_reason_code, verification_result=self.verification_result,
            publication_disposition=self.publication_disposition, critic_exhausted=self.critic_exhausted,
            revision_count=self.revision_count, confidence_class=self.confidence_class,
            experience_cohort=self.experience_cohort, adapter_id=self.adapter_id, model_id=self.model_id,
            profile_id=self.profile_id, source_candidate_fingerprint=self.source_candidate_fingerprint,
            source_feedback_fingerprint=self.source_feedback_fingerprint,
        )
        if self.projection_fingerprint != expected:
            raise ValueError("cognitive_quality_projection_fingerprint_invalid")
        for name in ("learning_authority","memory_write_authority","experience_trust_authority","routing_authority","model_selection_authority","prompt_mutation_authority","context_mutation_authority","policy_mutation_authority","execution_authority","benchmark_promotion_authority"):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_quality_{name}_invalid")
