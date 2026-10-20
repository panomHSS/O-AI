"""D160 safe read-only Cognitive Quality Investigation Hypothesis / Evidence Review schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticDomain
from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidencePacketStatus,
    CognitiveQualityInvestigationEvidencePrimaryAction,
)
from app.contracts.cognitive_quality_investigation_hypothesis_review import (
    CognitiveQualityInvestigationBlockedHypothesis,
    CognitiveQualityInvestigationHypothesisCandidate,
    CognitiveQualityInvestigationHypothesisKind,
    CognitiveQualityInvestigationHypothesisReview,
    CognitiveQualityInvestigationHypothesisReviewPrimaryAction,
    CognitiveQualityInvestigationHypothesisReviewStatus,
)
from app.contracts.cognitive_quality_investigation_planning import CognitiveQualityInvestigationKind
from app.schemas.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceEntryResponse,
)


class CognitiveQualityInvestigationHypothesisCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    hypothesis_kind: CognitiveQualityInvestigationHypothesisKind
    supporting_evidence: list[CognitiveQualityInvestigationEvidenceEntryResponse]

    @classmethod
    def from_contract(cls, value: CognitiveQualityInvestigationHypothesisCandidate):
        return cls(
            domain=value.domain,
            source_metric=value.source_metric,
            segment_key=value.segment_key,
            investigation_kind=value.investigation_kind,
            hypothesis_kind=value.hypothesis_kind,
            supporting_evidence=[
                CognitiveQualityInvestigationEvidenceEntryResponse.from_contract(item)
                for item in value.supporting_evidence
            ],
        )


class CognitiveQualityInvestigationBlockedHypothesisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    hypothesis_kind: CognitiveQualityInvestigationHypothesisKind
    blocking_dependencies: list[CognitiveQualityInvestigationEvidenceEntryResponse]

    @classmethod
    def from_contract(cls, value: CognitiveQualityInvestigationBlockedHypothesis):
        return cls(
            domain=value.domain,
            source_metric=value.source_metric,
            segment_key=value.segment_key,
            investigation_kind=value.investigation_kind,
            hypothesis_kind=value.hypothesis_kind,
            blocking_dependencies=[
                CognitiveQualityInvestigationEvidenceEntryResponse.from_contract(item)
                for item in value.blocking_dependencies
            ],
        )


class CognitiveQualityInvestigationHypothesisReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    reference_baseline: str
    policy_version: str
    workspace_id: str
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    source_packet_fingerprint: str | None
    source_packet_status: CognitiveQualityInvestigationEvidencePacketStatus | None
    source_packet_primary_action: CognitiveQualityInvestigationEvidencePrimaryAction | None
    source_plan_fingerprint: str | None
    source_diagnostic_fingerprint: str | None
    benchmark_review_recommended: bool
    status: CognitiveQualityInvestigationHypothesisReviewStatus
    primary_action: CognitiveQualityInvestigationHypothesisReviewPrimaryAction
    candidates: list[CognitiveQualityInvestigationHypothesisCandidateResponse]
    blocked_items: list[CognitiveQualityInvestigationBlockedHypothesisResponse]
    review_fingerprint: str
    learning_authority: Literal[False]
    memory_write_authority: Literal[False]
    experience_trust_authority: Literal[False]
    routing_authority: Literal[False]
    model_selection_authority: Literal[False]
    provider_selection_authority: Literal[False]
    profile_selection_authority: Literal[False]
    prompt_mutation_authority: Literal[False]
    context_mutation_authority: Literal[False]
    policy_mutation_authority: Literal[False]
    configuration_authority: Literal[False]
    execution_authority: Literal[False]
    benchmark_promotion_authority: Literal[False]
    rollout_authority: Literal[False]
    automatic_learning: Literal[False]
    automatic_optimization: Literal[False]

    @classmethod
    def from_contract(cls, value: CognitiveQualityInvestigationHypothesisReview):
        if not isinstance(value, CognitiveQualityInvestigationHypothesisReview):
            raise TypeError("cognitive quality investigation hypothesis review invalid")
        return cls(
            contract_version=value.contract_version,
            reference_baseline=value.reference_baseline,
            policy_version=value.policy_version,
            workspace_id=value.workspace_id.value,
            reference_since=value.reference_since,
            reference_until=value.reference_until,
            candidate_since=value.candidate_since,
            candidate_until=value.candidate_until,
            source_packet_fingerprint=value.source_packet_fingerprint,
            source_packet_status=value.source_packet_status,
            source_packet_primary_action=value.source_packet_primary_action,
            source_plan_fingerprint=value.source_plan_fingerprint,
            source_diagnostic_fingerprint=value.source_diagnostic_fingerprint,
            benchmark_review_recommended=value.benchmark_review_recommended,
            status=value.status,
            primary_action=value.primary_action,
            candidates=[
                CognitiveQualityInvestigationHypothesisCandidateResponse.from_contract(item)
                for item in value.candidates
            ],
            blocked_items=[
                CognitiveQualityInvestigationBlockedHypothesisResponse.from_contract(item)
                for item in value.blocked_items
            ],
            review_fingerprint=value.review_fingerprint,
            learning_authority=value.learning_authority,
            memory_write_authority=value.memory_write_authority,
            experience_trust_authority=value.experience_trust_authority,
            routing_authority=value.routing_authority,
            model_selection_authority=value.model_selection_authority,
            provider_selection_authority=value.provider_selection_authority,
            profile_selection_authority=value.profile_selection_authority,
            prompt_mutation_authority=value.prompt_mutation_authority,
            context_mutation_authority=value.context_mutation_authority,
            policy_mutation_authority=value.policy_mutation_authority,
            configuration_authority=value.configuration_authority,
            execution_authority=value.execution_authority,
            benchmark_promotion_authority=value.benchmark_promotion_authority,
            rollout_authority=value.rollout_authority,
            automatic_learning=value.automatic_learning,
            automatic_optimization=value.automatic_optimization,
        )
