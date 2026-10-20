"""D157 safe read-only cognitive quality diagnostic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticAdvisory,
    CognitiveQualityDiagnosticDomain,
    CognitiveQualityDiagnosticRecommendation,
    CognitiveQualityDiagnosticStatus,
)


class CognitiveQualityDiagnosticSignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: CognitiveQualityDiagnosticDomain
    metric: str
    segment_key: str | None
    reference_numerator: int
    reference_denominator: int
    candidate_numerator: int
    candidate_denominator: int
    delta_bps: int


class CognitiveQualityDiagnosticResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    reference_baseline: str
    policy_version: str
    workspace_id: str
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    reference_observed_count: int | None
    candidate_observed_count: int | None
    status: CognitiveQualityDiagnosticStatus
    primary_recommendation: CognitiveQualityDiagnosticRecommendation
    signals: list[CognitiveQualityDiagnosticSignalResponse]
    diagnostic_fingerprint: str

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
    def from_contract(cls, value: CognitiveQualityDiagnosticAdvisory) -> "CognitiveQualityDiagnosticResponse":
        if not isinstance(value, CognitiveQualityDiagnosticAdvisory):
            raise TypeError("cognitive quality diagnostic advisory invalid")
        return cls(
            contract_version=value.contract_version,
            reference_baseline=value.reference_baseline,
            policy_version=value.policy_version,
            workspace_id=value.workspace_id.value,
            reference_since=value.reference_since,
            reference_until=value.reference_until,
            candidate_since=value.candidate_since,
            candidate_until=value.candidate_until,
            reference_observed_count=value.reference_observed_count,
            candidate_observed_count=value.candidate_observed_count,
            status=value.status,
            primary_recommendation=value.primary_recommendation,
            signals=[CognitiveQualityDiagnosticSignalResponse(domain=item.domain, metric=item.metric, segment_key=item.segment_key, reference_numerator=item.reference_numerator, reference_denominator=item.reference_denominator, candidate_numerator=item.candidate_numerator, candidate_denominator=item.candidate_denominator, delta_bps=item.delta_bps) for item in value.signals],
            diagnostic_fingerprint=value.diagnostic_fingerprint,
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
