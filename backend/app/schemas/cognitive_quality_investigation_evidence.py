"""D159 safe read-only cognitive quality investigation evidence schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticDomain
from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceAvailability,
    CognitiveQualityInvestigationEvidenceAvailabilityReason,
    CognitiveQualityInvestigationEvidenceEntry,
    CognitiveQualityInvestigationEvidencePacket,
    CognitiveQualityInvestigationEvidencePacketStatus,
    CognitiveQualityInvestigationEvidencePrimaryAction,
    CognitiveQualityInvestigationEvidenceValue,
)
from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationBenchmarkScopeKind,
    CognitiveQualityInvestigationEvidenceRequirement,
    CognitiveQualityInvestigationKind,
    CognitiveQualityInvestigationPlanStatus,
    CognitiveQualityInvestigationPrimaryAction,
)


class CognitiveQualityInvestigationEvidenceValueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    segment_key: str | None
    reference_count: int
    candidate_count: int

    @classmethod
    def from_contract(cls, value: CognitiveQualityInvestigationEvidenceValue):
        return cls(
            metric=value.metric, segment_key=value.segment_key,
            reference_count=value.reference_count, candidate_count=value.candidate_count,
        )


class CognitiveQualityInvestigationEvidenceEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    evidence_requirement: CognitiveQualityInvestigationEvidenceRequirement
    availability: CognitiveQualityInvestigationEvidenceAvailability
    availability_reason: CognitiveQualityInvestigationEvidenceAvailabilityReason
    values: list[CognitiveQualityInvestigationEvidenceValueResponse]
    benchmark_scope_kind: CognitiveQualityInvestigationBenchmarkScopeKind | None
    benchmark_segment_key: str | None
    benchmark_candidate_task_keys: list[str]

    @classmethod
    def from_contract(cls, value: CognitiveQualityInvestigationEvidenceEntry):
        return cls(
            domain=value.domain, source_metric=value.source_metric, segment_key=value.segment_key,
            investigation_kind=value.investigation_kind, evidence_requirement=value.evidence_requirement,
            availability=value.availability, availability_reason=value.availability_reason,
            values=[CognitiveQualityInvestigationEvidenceValueResponse.from_contract(item) for item in value.values],
            benchmark_scope_kind=value.benchmark_scope_kind,
            benchmark_segment_key=value.benchmark_segment_key,
            benchmark_candidate_task_keys=list(value.benchmark_candidate_task_keys),
        )


class CognitiveQualityInvestigationEvidencePacketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    reference_baseline: str
    policy_version: str
    workspace_id: str
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    source_plan_fingerprint: str | None
    source_plan_status: CognitiveQualityInvestigationPlanStatus | None
    source_plan_primary_action: CognitiveQualityInvestigationPrimaryAction | None
    source_diagnostic_fingerprint: str | None
    benchmark_review_recommended: bool
    status: CognitiveQualityInvestigationEvidencePacketStatus
    primary_action: CognitiveQualityInvestigationEvidencePrimaryAction
    entries: list[CognitiveQualityInvestigationEvidenceEntryResponse]
    packet_fingerprint: str
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
    def from_contract(cls, value: CognitiveQualityInvestigationEvidencePacket):
        if not isinstance(value, CognitiveQualityInvestigationEvidencePacket):
            raise TypeError("cognitive quality investigation evidence packet invalid")
        return cls(
            contract_version=value.contract_version, reference_baseline=value.reference_baseline,
            policy_version=value.policy_version, workspace_id=value.workspace_id.value,
            reference_since=value.reference_since, reference_until=value.reference_until,
            candidate_since=value.candidate_since, candidate_until=value.candidate_until,
            source_plan_fingerprint=value.source_plan_fingerprint,
            source_plan_status=value.source_plan_status,
            source_plan_primary_action=value.source_plan_primary_action,
            source_diagnostic_fingerprint=value.source_diagnostic_fingerprint,
            benchmark_review_recommended=value.benchmark_review_recommended,
            status=value.status, primary_action=value.primary_action,
            entries=[CognitiveQualityInvestigationEvidenceEntryResponse.from_contract(item) for item in value.entries],
            packet_fingerprint=value.packet_fingerprint,
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
