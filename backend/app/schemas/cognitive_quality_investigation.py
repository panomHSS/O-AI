"""D158 safe read-only cognitive quality investigation planning schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticDomain,
    CognitiveQualityDiagnosticRecommendation,
    CognitiveQualityDiagnosticStatus,
)
from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationBenchmarkScopeKind,
    CognitiveQualityInvestigationEvidenceRequirement,
    CognitiveQualityInvestigationKind,
    CognitiveQualityInvestigationPlan,
    CognitiveQualityInvestigationPlanStatus,
    CognitiveQualityInvestigationPrimaryAction,
)


class CognitiveQualityInvestigationItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    evidence_requirements: list[CognitiveQualityInvestigationEvidenceRequirement]
    benchmark_scope_kind: CognitiveQualityInvestigationBenchmarkScopeKind
    benchmark_segment_key: str | None
    source_reference_numerator: int
    source_reference_denominator: int
    source_candidate_numerator: int
    source_candidate_denominator: int
    source_delta_bps: int


class CognitiveQualityInvestigationPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    reference_baseline: str
    policy_version: str
    workspace_id: str
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    source_diagnostic_fingerprint: str | None
    source_diagnostic_status: CognitiveQualityDiagnosticStatus | None
    source_primary_recommendation: CognitiveQualityDiagnosticRecommendation | None
    status: CognitiveQualityInvestigationPlanStatus
    primary_action: CognitiveQualityInvestigationPrimaryAction
    benchmark_review_recommended: bool
    items: list[CognitiveQualityInvestigationItemResponse]
    plan_fingerprint: str
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
    def from_contract(cls,value: CognitiveQualityInvestigationPlan) -> "CognitiveQualityInvestigationPlanResponse":
        if not isinstance(value,CognitiveQualityInvestigationPlan):
            raise TypeError("cognitive quality investigation plan invalid")
        return cls(
            contract_version=value.contract_version,reference_baseline=value.reference_baseline,
            policy_version=value.policy_version,workspace_id=value.workspace_id.value,
            reference_since=value.reference_since,reference_until=value.reference_until,
            candidate_since=value.candidate_since,candidate_until=value.candidate_until,
            source_diagnostic_fingerprint=value.source_diagnostic_fingerprint,
            source_diagnostic_status=value.source_diagnostic_status,
            source_primary_recommendation=value.source_primary_recommendation,
            status=value.status,primary_action=value.primary_action,
            benchmark_review_recommended=value.benchmark_review_recommended,
            items=[CognitiveQualityInvestigationItemResponse(
                domain=item.domain,source_metric=item.source_metric,segment_key=item.segment_key,
                investigation_kind=item.investigation_kind,evidence_requirements=list(item.evidence_requirements),
                benchmark_scope_kind=item.benchmark_scope_kind,benchmark_segment_key=item.benchmark_segment_key,
                source_reference_numerator=item.source_reference_numerator,
                source_reference_denominator=item.source_reference_denominator,
                source_candidate_numerator=item.source_candidate_numerator,
                source_candidate_denominator=item.source_candidate_denominator,
                source_delta_bps=item.source_delta_bps,
            ) for item in value.items],
            plan_fingerprint=value.plan_fingerprint,learning_authority=value.learning_authority,
            memory_write_authority=value.memory_write_authority,experience_trust_authority=value.experience_trust_authority,
            routing_authority=value.routing_authority,model_selection_authority=value.model_selection_authority,
            provider_selection_authority=value.provider_selection_authority,profile_selection_authority=value.profile_selection_authority,
            prompt_mutation_authority=value.prompt_mutation_authority,context_mutation_authority=value.context_mutation_authority,
            policy_mutation_authority=value.policy_mutation_authority,configuration_authority=value.configuration_authority,
            execution_authority=value.execution_authority,benchmark_promotion_authority=value.benchmark_promotion_authority,
            rollout_authority=value.rollout_authority,automatic_learning=value.automatic_learning,
            automatic_optimization=value.automatic_optimization,
        )
