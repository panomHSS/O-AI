"""D158 immutable Cognitive Quality Investigation Planning V1 contracts."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticDomain,
    CognitiveQualityDiagnosticRecommendation,
    CognitiveQualityDiagnosticStatus,
)
from app.contracts.workspace import WorkspaceId

D158_REFERENCE_BASELINE = "b85572a4f1a5a179db9c98029f013ce8cf8a1d87"
D158_CONTRACT_VERSION = "1"
D158_POLICY_VERSION = "o-ai.d158.cognitive-quality-investigation-plan.v1"

CognitiveQualityInvestigationPlanStatus: TypeAlias = Literal[
    "invalid_evidence","observation_required","no_material_investigation","investigation_ready",
]
CognitiveQualityInvestigationPrimaryAction: TypeAlias = Literal[
    "repair_evidence","continue_observation","review_investigation_plan","prepare_benchmark_review",
]
CognitiveQualityInvestigationKind: TypeAlias = Literal[
    "evidence_integrity_review","bounded_insufficiency_review","confidence_pattern_review",
    "adverse_outcome_review","invalid_cognition_review","terminal_failure_review",
    "critic_exhaustion_review","revision_behavior_review","task_kind_concentration_review",
    "experience_cohort_difference_review",
]
CognitiveQualityInvestigationEvidenceRequirement: TypeAlias = Literal[
    "d156_period_counts","d156_terminal_counts","d156_verification_counts","d156_confidence_counts",
    "d156_revision_critic_counts","d156_task_kind_breakdown","d156_experience_cohort_breakdown",
    "d138_d139_targeted_benchmark_slice","future_matched_cohort_control",
]
CognitiveQualityInvestigationBenchmarkScopeKind: TypeAlias = Literal[
    "none","derive_from_candidate_task_breakdown","task_kind_segment",
]

D158_DOMAIN_PRIORITY: tuple[CognitiveQualityDiagnosticDomain, ...] = (
    "evidence_integrity","cognition_validity","critic_revision",
    "evidence_sufficiency","task_concentration","experience_cohort_difference",
)
D158_ALLOWED_SOURCE_METRICS: tuple[str, ...] = (
    "invalid_evidence_rate","bounded_insufficiency_rate","confidence_concern_rate",
    "adverse_outcome_rate","verification_invalid_cognition_rate","terminal_failed_rate",
    "critic_exhausted_rate","revised_turn_rate","adverse_outcome_rate_vs_overall",
    "adverse_outcome_rate_gap",
)

_INVESTIGATION_KINDS = {
    "evidence_integrity_review","bounded_insufficiency_review","confidence_pattern_review",
    "adverse_outcome_review","invalid_cognition_review","terminal_failure_review",
    "critic_exhaustion_review","revision_behavior_review","task_kind_concentration_review",
    "experience_cohort_difference_review",
}
_EVIDENCE_REQUIREMENTS = {
    "d156_period_counts","d156_terminal_counts","d156_verification_counts","d156_confidence_counts",
    "d156_revision_critic_counts","d156_task_kind_breakdown","d156_experience_cohort_breakdown",
    "d138_d139_targeted_benchmark_slice","future_matched_cohort_control",
}
_BENCHMARK_SCOPE_KINDS = {"none","derive_from_candidate_task_breakdown","task_kind_segment"}
_PLAN_STATUSES = {"invalid_evidence","observation_required","no_material_investigation","investigation_ready"}
_PRIMARY_ACTIONS = {"repair_evidence","continue_observation","review_investigation_plan","prepare_benchmark_review"}
_D157_STATUSES = {"invalid_evidence","insufficient_evidence","no_material_signal","investigation_recommended"}
_D157_RECOMMENDATIONS = {
    "continue_observation","investigate_evidence_integrity","investigate_evidence_sufficiency",
    "investigate_cognition","investigate_critic","investigate_task_cohort",
    "investigate_experience_cohort","benchmark_review_recommended",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN_RANK = {domain: index for index, domain in enumerate(D158_DOMAIN_PRIORITY)}


def _bounded_segment(value: object, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    if len(value.encode("utf-8")) > 256 or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(code)
    return value


def _bounded_nonnegative(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(code)
    return value


def _time_token(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise ValueError("cognitive_quality_investigation_time_invalid")
    if value.tzinfo is None or value.utcoffset() is None:
        return "naive:" + value.isoformat(timespec="microseconds")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationItem:
    domain: CognitiveQualityDiagnosticDomain
    source_metric: str
    segment_key: str | None
    investigation_kind: CognitiveQualityInvestigationKind
    evidence_requirements: tuple[CognitiveQualityInvestigationEvidenceRequirement, ...]
    benchmark_scope_kind: CognitiveQualityInvestigationBenchmarkScopeKind
    benchmark_segment_key: str | None
    source_reference_numerator: int
    source_reference_denominator: int
    source_candidate_numerator: int
    source_candidate_denominator: int
    source_delta_bps: int

    def __post_init__(self) -> None:
        if self.domain not in _DOMAIN_RANK:
            raise ValueError("cognitive_quality_investigation_domain_invalid")
        if self.source_metric not in D158_ALLOWED_SOURCE_METRICS:
            raise ValueError("cognitive_quality_investigation_metric_invalid")
        _bounded_segment(self.segment_key,"cognitive_quality_investigation_segment_invalid")
        if self.investigation_kind not in _INVESTIGATION_KINDS:
            raise ValueError("cognitive_quality_investigation_kind_invalid")
        if not isinstance(self.evidence_requirements, tuple) or not self.evidence_requirements:
            raise ValueError("cognitive_quality_investigation_evidence_invalid")
        if len(set(self.evidence_requirements)) != len(self.evidence_requirements):
            raise ValueError("cognitive_quality_investigation_evidence_duplicate")
        if any(item not in _EVIDENCE_REQUIREMENTS for item in self.evidence_requirements):
            raise ValueError("cognitive_quality_investigation_evidence_invalid")
        if self.benchmark_scope_kind not in _BENCHMARK_SCOPE_KINDS:
            raise ValueError("cognitive_quality_investigation_benchmark_scope_invalid")
        bseg = _bounded_segment(self.benchmark_segment_key,"cognitive_quality_investigation_benchmark_segment_invalid")
        if self.benchmark_scope_kind == "task_kind_segment":
            if bseg is None or bseg != self.segment_key:
                raise ValueError("cognitive_quality_investigation_benchmark_segment_invalid")
        elif bseg is not None:
            raise ValueError("cognitive_quality_investigation_benchmark_segment_invalid")
        for name in ("source_reference_numerator","source_reference_denominator","source_candidate_numerator","source_candidate_denominator"):
            _bounded_nonnegative(getattr(self,name),f"cognitive_quality_investigation_{name}_invalid")
        if self.source_reference_numerator > self.source_reference_denominator:
            raise ValueError("cognitive_quality_investigation_reference_rate_invalid")
        if self.source_candidate_numerator > self.source_candidate_denominator:
            raise ValueError("cognitive_quality_investigation_candidate_rate_invalid")
        if type(self.source_delta_bps) is not int:
            raise ValueError("cognitive_quality_investigation_delta_invalid")


def cognitive_quality_investigation_item_sort_key(item: CognitiveQualityInvestigationItem) -> tuple[int,str,str]:
    if not isinstance(item,CognitiveQualityInvestigationItem):
        raise TypeError("cognitive quality investigation item invalid")
    return (_DOMAIN_RANK[item.domain],item.source_metric,item.segment_key or "")


def _item_payload(item: CognitiveQualityInvestigationItem) -> dict[str,object]:
    return {
        "domain":item.domain,"source_metric":item.source_metric,"segment_key":item.segment_key,
        "investigation_kind":item.investigation_kind,"evidence_requirements":list(item.evidence_requirements),
        "benchmark_scope_kind":item.benchmark_scope_kind,"benchmark_segment_key":item.benchmark_segment_key,
        "source_reference_numerator":item.source_reference_numerator,
        "source_reference_denominator":item.source_reference_denominator,
        "source_candidate_numerator":item.source_candidate_numerator,
        "source_candidate_denominator":item.source_candidate_denominator,
        "source_delta_bps":item.source_delta_bps,
    }


def compute_cognitive_quality_investigation_plan_fingerprint(
    *,workspace_id: WorkspaceId,reference_since: datetime,reference_until: datetime,
    candidate_since: datetime,candidate_until: datetime,source_diagnostic_fingerprint: str | None,
    source_diagnostic_status: CognitiveQualityDiagnosticStatus | None,
    source_primary_recommendation: CognitiveQualityDiagnosticRecommendation | None,
    status: CognitiveQualityInvestigationPlanStatus,primary_action: CognitiveQualityInvestigationPrimaryAction,
    benchmark_review_recommended: bool,items: tuple[CognitiveQualityInvestigationItem,...],
) -> str:
    if not isinstance(workspace_id,WorkspaceId):
        raise ValueError("cognitive_quality_investigation_workspace_invalid")
    ordered=tuple(sorted(items,key=cognitive_quality_investigation_item_sort_key))
    payload={
        "contract_version":D158_CONTRACT_VERSION,"reference_baseline":D158_REFERENCE_BASELINE,
        "policy_version":D158_POLICY_VERSION,"workspace_id":workspace_id.value,
        "reference_since":_time_token(reference_since),"reference_until":_time_token(reference_until),
        "candidate_since":_time_token(candidate_since),"candidate_until":_time_token(candidate_until),
        "source_diagnostic_fingerprint":source_diagnostic_fingerprint,
        "source_diagnostic_status":source_diagnostic_status,
        "source_primary_recommendation":source_primary_recommendation,
        "status":status,"primary_action":primary_action,
        "benchmark_review_recommended":benchmark_review_recommended,
        "items":[_item_payload(item) for item in ordered],
    }
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveQualityInvestigationPlan:
    workspace_id: WorkspaceId
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
    items: tuple[CognitiveQualityInvestigationItem,...]
    plan_fingerprint: str

    contract_version: Literal["1"] = D158_CONTRACT_VERSION
    reference_baseline: str = D158_REFERENCE_BASELINE
    policy_version: str = D158_POLICY_VERSION
    learning_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    experience_trust_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    provider_selection_authority: Literal[False] = False
    profile_selection_authority: Literal[False] = False
    prompt_mutation_authority: Literal[False] = False
    context_mutation_authority: Literal[False] = False
    policy_mutation_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    benchmark_promotion_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_optimization: Literal[False] = False

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id,WorkspaceId):
            raise ValueError("cognitive_quality_investigation_workspace_invalid")
        if any(not isinstance(v,datetime) for v in (self.reference_since,self.reference_until,self.candidate_since,self.candidate_until)):
            raise ValueError("cognitive_quality_investigation_time_invalid")
        if self.contract_version != D158_CONTRACT_VERSION or self.reference_baseline != D158_REFERENCE_BASELINE or self.policy_version != D158_POLICY_VERSION:
            raise ValueError("cognitive_quality_investigation_contract_invalid")
        if self.status not in _PLAN_STATUSES or self.primary_action not in _PRIMARY_ACTIONS:
            raise ValueError("cognitive_quality_investigation_projection_invalid")
        if type(self.benchmark_review_recommended) is not bool:
            raise ValueError("cognitive_quality_investigation_benchmark_flag_invalid")

        src=(self.source_diagnostic_fingerprint,self.source_diagnostic_status,self.source_primary_recommendation)
        missing=all(v is None for v in src); complete=all(v is not None for v in src)
        if not (missing or complete):
            raise ValueError("cognitive_quality_investigation_source_identity_invalid")
        if complete:
            assert self.source_diagnostic_fingerprint is not None
            assert self.source_diagnostic_status is not None
            assert self.source_primary_recommendation is not None
            if _SHA256.fullmatch(self.source_diagnostic_fingerprint) is None:
                raise ValueError("cognitive_quality_investigation_source_fingerprint_invalid")
            if self.source_diagnostic_status not in _D157_STATUSES or self.source_primary_recommendation not in _D157_RECOMMENDATIONS:
                raise ValueError("cognitive_quality_investigation_source_projection_invalid")

        items=tuple(self.items)
        if any(type(item) is not CognitiveQualityInvestigationItem for item in items):
            raise ValueError("cognitive_quality_investigation_item_invalid")
        if items != tuple(sorted(items,key=cognitive_quality_investigation_item_sort_key)):
            raise ValueError("cognitive_quality_investigation_item_order_invalid")

        if missing:
            if (self.status,self.primary_action,self.benchmark_review_recommended,items) != ("invalid_evidence","repair_evidence",False,()):
                raise ValueError("cognitive_quality_investigation_source_missing_projection_invalid")
        else:
            assert self.source_diagnostic_status is not None and self.source_primary_recommendation is not None
            if self.source_diagnostic_status == "invalid_evidence":
                expected=("invalid_evidence","repair_evidence")
            elif self.source_diagnostic_status == "insufficient_evidence":
                expected=("observation_required","continue_observation")
            elif self.source_diagnostic_status == "no_material_signal":
                expected=("no_material_investigation","continue_observation")
            else:
                expected=("investigation_ready","prepare_benchmark_review" if self.source_primary_recommendation=="benchmark_review_recommended" else "review_investigation_plan")
            if (self.status,self.primary_action) != expected:
                raise ValueError("cognitive_quality_investigation_status_projection_invalid")
            expected_benchmark=self.source_diagnostic_status=="investigation_recommended" and self.source_primary_recommendation=="benchmark_review_recommended"
            if self.benchmark_review_recommended is not expected_benchmark:
                raise ValueError("cognitive_quality_investigation_benchmark_projection_invalid")
            if self.source_diagnostic_status=="investigation_recommended":
                if not items: raise ValueError("cognitive_quality_investigation_items_required")
            elif items:
                raise ValueError("cognitive_quality_investigation_items_forbidden")

        for name in (
            "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
            "model_selection_authority","provider_selection_authority","profile_selection_authority",
            "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
            "configuration_authority","execution_authority","benchmark_promotion_authority",
            "rollout_authority","automatic_learning","automatic_optimization",
        ):
            if getattr(self,name) is not False:
                raise ValueError(f"cognitive_quality_investigation_{name}_invalid")

        expected=compute_cognitive_quality_investigation_plan_fingerprint(
            workspace_id=self.workspace_id,reference_since=self.reference_since,reference_until=self.reference_until,
            candidate_since=self.candidate_since,candidate_until=self.candidate_until,
            source_diagnostic_fingerprint=self.source_diagnostic_fingerprint,
            source_diagnostic_status=self.source_diagnostic_status,
            source_primary_recommendation=self.source_primary_recommendation,
            status=self.status,primary_action=self.primary_action,
            benchmark_review_recommended=self.benchmark_review_recommended,items=items,
        )
        if self.plan_fingerprint != expected:
            raise ValueError("cognitive_quality_investigation_fingerprint_invalid")


__all__=[
    "CognitiveQualityInvestigationBenchmarkScopeKind","CognitiveQualityInvestigationEvidenceRequirement",
    "CognitiveQualityInvestigationItem","CognitiveQualityInvestigationKind","CognitiveQualityInvestigationPlan",
    "CognitiveQualityInvestigationPlanStatus","CognitiveQualityInvestigationPrimaryAction",
    "D158_ALLOWED_SOURCE_METRICS","D158_CONTRACT_VERSION","D158_DOMAIN_PRIORITY","D158_POLICY_VERSION",
    "D158_REFERENCE_BASELINE","cognitive_quality_investigation_item_sort_key",
    "compute_cognitive_quality_investigation_plan_fingerprint",
]
