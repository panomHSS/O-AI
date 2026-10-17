"""D147 immutable Trusted Experience Lifecycle V1 contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import COGNITIVE_REVISION_COUNT_MAX
from app.contracts.cognitive_experience import CognitiveExperienceCandidateArtifact
from app.contracts.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackAssessment,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId

D147_REFERENCE_BASELINE = "0415696cb3b5595514d2728a8f32f08dc751acc9"
D147_CONTRACT_VERSION = "1"
D147_SAMPLE_SCOPE = "trusted_experience_lifecycle_records"
D147_COUNTER_MAX = 9_223_372_036_854_775_807

CognitiveTrustedExperienceEligibility: TypeAlias = Literal[
    "eligible_for_owner_review",
    "ineligible",
    "invalid_evidence",
]
CognitiveTrustedExperienceEligibilityReason: TypeAlias = Literal[
    "verified_success",
    "bounded_insufficiency",
    "adverse_outcome",
    "invalid_evidence",
]

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_FIELDS = (
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "execution_authority",
    "configuration_authority",
    "rollout_authority",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


def _identifier(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    if len(value.encode("utf-8")) > 512:
        raise ValueError(code)
    return value


def compute_cognitive_trusted_experience_proposal_fingerprint(
    *,
    workspace_id: WorkspaceId,
    source_candidate_fingerprint: str,
    source_feedback_fingerprint: str,
    interaction_intent: str,
    cognitive_intent: str,
    authoritative_ai_task_kind: AITaskKind,
    observed_confidence_class: str,
    authorized_adapter_id: str | None,
    authorized_model_id: str | None,
    authorized_profile_id: str | None,
    source_revision_count: int,
) -> str:
    """Hash only the frozen D147 privacy-minimized proposal projection."""

    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("trusted_experience_workspace_invalid")
    for value, code in (
        (source_candidate_fingerprint, "trusted_experience_candidate_fingerprint_invalid"),
        (source_feedback_fingerprint, "trusted_experience_feedback_fingerprint_invalid"),
    ):
        if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
            raise ValueError(code)
    if type(interaction_intent) is not str or not interaction_intent:
        raise ValueError("trusted_experience_interaction_intent_invalid")
    if type(cognitive_intent) is not str or not cognitive_intent:
        raise ValueError("trusted_experience_cognitive_intent_invalid")
    if not isinstance(authoritative_ai_task_kind, AITaskKind):
        raise ValueError("trusted_experience_task_kind_invalid")
    if type(observed_confidence_class) is not str or not observed_confidence_class:
        raise ValueError("trusted_experience_confidence_invalid")
    adapter = _identifier(
        authorized_adapter_id,
        code="trusted_experience_adapter_id_invalid",
    )
    model = _identifier(
        authorized_model_id,
        code="trusted_experience_model_id_invalid",
    )
    profile = _identifier(
        authorized_profile_id,
        code="trusted_experience_profile_id_invalid",
    )
    if (
        type(source_revision_count) is not int
        or isinstance(source_revision_count, bool)
        or not 0 <= source_revision_count <= COGNITIVE_REVISION_COUNT_MAX
    ):
        raise ValueError("trusted_experience_source_revision_invalid")

    payload = {
        "authoritative_ai_task_kind": authoritative_ai_task_kind.value,
        "authorized_adapter_id": adapter,
        "authorized_model_id": model,
        "authorized_profile_id": profile,
        "cognitive_intent": cognitive_intent,
        "contract_version": D147_CONTRACT_VERSION,
        "interaction_intent": interaction_intent,
        "lesson_code": "verified_success",
        "observed_confidence_class": observed_confidence_class,
        "quality_classification": "verified_success",
        "quality_reason_code": "verified_success",
        "source_candidate_fingerprint": source_candidate_fingerprint,
        "source_feedback_fingerprint": source_feedback_fingerprint,
        "source_revision_count": source_revision_count,
        "workspace_id": workspace_id.value,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceProposal:
    """One safe, eligible D147 proposal. Persistence never implies trust."""

    workspace_id: WorkspaceId
    source_candidate_fingerprint: str
    source_feedback_fingerprint: str
    interaction_intent: str
    cognitive_intent: str
    authoritative_ai_task_kind: AITaskKind
    observed_confidence_class: str
    authorized_adapter_id: str | None
    authorized_model_id: str | None
    authorized_profile_id: str | None
    source_revision_count: int
    proposal_fingerprint: str

    contract_version: Literal["1"] = D147_CONTRACT_VERSION
    quality_classification: Literal["verified_success"] = "verified_success"
    quality_reason_code: Literal["verified_success"] = "verified_success"
    lesson_code: Literal["verified_success"] = "verified_success"

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D147_CONTRACT_VERSION:
            raise ValueError("trusted_experience_contract_version_invalid")
        expected = compute_cognitive_trusted_experience_proposal_fingerprint(
            workspace_id=self.workspace_id,
            source_candidate_fingerprint=self.source_candidate_fingerprint,
            source_feedback_fingerprint=self.source_feedback_fingerprint,
            interaction_intent=self.interaction_intent,
            cognitive_intent=self.cognitive_intent,
            authoritative_ai_task_kind=self.authoritative_ai_task_kind,
            observed_confidence_class=self.observed_confidence_class,
            authorized_adapter_id=self.authorized_adapter_id,
            authorized_model_id=self.authorized_model_id,
            authorized_profile_id=self.authorized_profile_id,
            source_revision_count=self.source_revision_count,
        )
        if self.proposal_fingerprint != expected:
            raise ValueError("trusted_experience_proposal_fingerprint_mismatch")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"trusted_experience_{name}_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveTrustedExperienceEligibilityAssessment:
    """Deterministic trust eligibility only; never the trust decision."""

    eligibility: CognitiveTrustedExperienceEligibility
    reason_code: CognitiveTrustedExperienceEligibilityReason
    proposal: CognitiveTrustedExperienceProposal | None

    contract_version: Literal["1"] = D147_CONTRACT_VERSION
    reference_baseline: str = D147_REFERENCE_BASELINE

    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_trust: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D147_CONTRACT_VERSION:
            raise ValueError("trusted_experience_contract_version_invalid")
        if self.reference_baseline != D147_REFERENCE_BASELINE:
            raise ValueError("trusted_experience_baseline_invalid")
        if self.eligibility not in {
            "eligible_for_owner_review",
            "ineligible",
            "invalid_evidence",
        }:
            raise ValueError("trusted_experience_eligibility_invalid")
        if self.eligibility == "eligible_for_owner_review":
            if self.reason_code != "verified_success" or not isinstance(
                self.proposal, CognitiveTrustedExperienceProposal
            ):
                raise ValueError("trusted_experience_eligible_projection_invalid")
        else:
            if self.proposal is not None:
                raise ValueError("trusted_experience_ineligible_projection_invalid")
            if self.eligibility == "ineligible" and self.reason_code not in {
                "bounded_insufficiency",
                "adverse_outcome",
            }:
                raise ValueError("trusted_experience_ineligible_reason_invalid")
            if self.eligibility == "invalid_evidence" and self.reason_code != "invalid_evidence":
                raise ValueError("trusted_experience_invalid_reason_invalid")
        for name in _AUTHORITY_FIELDS:
            if getattr(self, name) is not False:
                raise ValueError(f"trusted_experience_{name}_invalid")


def evaluate_cognitive_trusted_experience_eligibility(
    *,
    candidate: object,
    feedback: object,
) -> CognitiveTrustedExperienceEligibilityAssessment:
    """Evaluate exact D134 + D146 evidence without persistence authority."""

    if (
        type(candidate) is not CognitiveExperienceCandidateArtifact
        or not isinstance(feedback, CognitiveOutcomeQualityFeedbackAssessment)
    ):
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )
    try:
        candidate.__post_init__()
        feedback.__post_init__()
    except Exception:
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )

    if feedback.classification == "invalid_evidence":
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )
    if feedback.source_candidate_fingerprint != candidate.candidate_fingerprint:
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )
    if feedback.classification != "verified_success":
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="ineligible",
            reason_code=feedback.classification,
            proposal=None,
        )

    try:
        if (
            feedback.reason_code != "verified_success"
            or candidate.lesson_code != "verified_success"
            or candidate.interaction_intent is None
            or candidate.cognitive_intent is None
            or candidate.authoritative_ai_task_kind is None
            or candidate.observed_confidence_class is None
            or feedback.feedback_fingerprint is None
        ):
            raise ValueError("trusted_experience_verified_success_projection_invalid")
        proposal_fingerprint = compute_cognitive_trusted_experience_proposal_fingerprint(
            workspace_id=candidate.envelope.workspace_id,
            source_candidate_fingerprint=candidate.candidate_fingerprint,
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            interaction_intent=candidate.interaction_intent,
            cognitive_intent=candidate.cognitive_intent,
            authoritative_ai_task_kind=candidate.authoritative_ai_task_kind,
            observed_confidence_class=candidate.observed_confidence_class,
            authorized_adapter_id=candidate.authorized_adapter_id,
            authorized_model_id=candidate.authorized_model_id,
            authorized_profile_id=candidate.authorized_profile_id,
            source_revision_count=candidate.revision_count,
        )
        proposal = CognitiveTrustedExperienceProposal(
            workspace_id=candidate.envelope.workspace_id,
            source_candidate_fingerprint=candidate.candidate_fingerprint,
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            interaction_intent=candidate.interaction_intent,
            cognitive_intent=candidate.cognitive_intent,
            authoritative_ai_task_kind=candidate.authoritative_ai_task_kind,
            observed_confidence_class=candidate.observed_confidence_class,
            authorized_adapter_id=candidate.authorized_adapter_id,
            authorized_model_id=candidate.authorized_model_id,
            authorized_profile_id=candidate.authorized_profile_id,
            source_revision_count=candidate.revision_count,
            proposal_fingerprint=proposal_fingerprint,
        )
    except Exception:
        return CognitiveTrustedExperienceEligibilityAssessment(
            eligibility="invalid_evidence",
            reason_code="invalid_evidence",
            proposal=None,
        )

    return CognitiveTrustedExperienceEligibilityAssessment(
        eligibility="eligible_for_owner_review",
        reason_code="verified_success",
        proposal=proposal,
    )


__all__ = [
    "D147_CONTRACT_VERSION",
    "D147_COUNTER_MAX",
    "D147_REFERENCE_BASELINE",
    "D147_SAMPLE_SCOPE",
    "CognitiveTrustedExperienceEligibility",
    "CognitiveTrustedExperienceEligibilityAssessment",
    "CognitiveTrustedExperienceEligibilityReason",
    "CognitiveTrustedExperienceProposal",
    "compute_cognitive_trusted_experience_proposal_fingerprint",
    "evaluate_cognitive_trusted_experience_eligibility",
]
