"""D157 immutable Cognitive Quality Diagnostic Advisory V1 contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from app.contracts.workspace import WorkspaceId

D157_REFERENCE_BASELINE = "997dc70c3104957a10d672e4d7dad0d77a800fc0"
D157_CONTRACT_VERSION = "1"
D157_POLICY_VERSION = "o-ai.d157.cognitive-quality-diagnostic.v1"
D157_RATE_SCALE_BPS = 10_000
D157_MIN_PERIOD_OBSERVATIONS = 30
D157_MIN_SUBGROUP_OBSERVATIONS = 10
D157_MATERIAL_RATE_INCREASE_BPS = 1_000
D157_MATERIAL_SUBGROUP_GAP_BPS = 1_500
D157_MIN_SUPPORTING_EVENT_INCREASE = 3

CognitiveQualityDiagnosticStatus: TypeAlias = Literal[
    "invalid_evidence",
    "insufficient_evidence",
    "no_material_signal",
    "investigation_recommended",
]
CognitiveQualityDiagnosticRecommendation: TypeAlias = Literal[
    "continue_observation",
    "investigate_evidence_integrity",
    "investigate_evidence_sufficiency",
    "investigate_cognition",
    "investigate_critic",
    "investigate_task_cohort",
    "investigate_experience_cohort",
    "benchmark_review_recommended",
]
CognitiveQualityDiagnosticDomain: TypeAlias = Literal[
    "evidence_integrity",
    "evidence_sufficiency",
    "cognition_validity",
    "critic_revision",
    "task_concentration",
    "experience_cohort_difference",
]

_DOMAIN_RECOMMENDATION = {
    "evidence_integrity": "investigate_evidence_integrity",
    "evidence_sufficiency": "investigate_evidence_sufficiency",
    "cognition_validity": "investigate_cognition",
    "critic_revision": "investigate_critic",
    "task_concentration": "investigate_task_cohort",
    "experience_cohort_difference": "investigate_experience_cohort",
}
_ALLOWED_METRICS = {
    "invalid_evidence_rate",
    "bounded_insufficiency_rate",
    "confidence_concern_rate",
    "adverse_outcome_rate",
    "verification_invalid_cognition_rate",
    "critic_exhausted_rate",
    "revised_turn_rate",
    "adverse_outcome_rate_vs_overall",
    "adverse_outcome_rate_gap",
}


def _bounded_nonnegative(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(code)
    return value


def _bounded_segment(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("cognitive_quality_diagnostic_segment_invalid")
    if len(value.encode("utf-8")) > 256 or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("cognitive_quality_diagnostic_segment_invalid")
    return value


def _time_token(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise ValueError("cognitive_quality_diagnostic_time_invalid")
    if value.tzinfo is None or value.utcoffset() is None:
        return "naive:" + value.isoformat(timespec="microseconds")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class CognitiveQualityDiagnosticSignal:
    domain: CognitiveQualityDiagnosticDomain
    metric: str
    segment_key: str | None
    reference_numerator: int
    reference_denominator: int
    candidate_numerator: int
    candidate_denominator: int
    delta_bps: int

    def __post_init__(self) -> None:
        if self.domain not in _DOMAIN_RECOMMENDATION:
            raise ValueError("cognitive_quality_diagnostic_domain_invalid")
        if self.metric not in _ALLOWED_METRICS:
            raise ValueError("cognitive_quality_diagnostic_metric_invalid")
        _bounded_segment(self.segment_key)
        for name in (
            "reference_numerator",
            "reference_denominator",
            "candidate_numerator",
            "candidate_denominator",
        ):
            _bounded_nonnegative(getattr(self, name), f"cognitive_quality_diagnostic_{name}_invalid")
        if self.reference_numerator > self.reference_denominator:
            raise ValueError("cognitive_quality_diagnostic_reference_rate_invalid")
        if self.candidate_numerator > self.candidate_denominator:
            raise ValueError("cognitive_quality_diagnostic_candidate_rate_invalid")
        if type(self.delta_bps) is not int:
            raise ValueError("cognitive_quality_diagnostic_delta_invalid")


def _signal_payload(signal: CognitiveQualityDiagnosticSignal) -> dict[str, object]:
    return {
        "domain": signal.domain,
        "metric": signal.metric,
        "segment_key": signal.segment_key,
        "reference_numerator": signal.reference_numerator,
        "reference_denominator": signal.reference_denominator,
        "candidate_numerator": signal.candidate_numerator,
        "candidate_denominator": signal.candidate_denominator,
        "delta_bps": signal.delta_bps,
    }


def compute_cognitive_quality_diagnostic_fingerprint(
    *,
    workspace_id: WorkspaceId,
    reference_since: datetime,
    reference_until: datetime,
    candidate_since: datetime,
    candidate_until: datetime,
    reference_observed_count: int | None,
    candidate_observed_count: int | None,
    status: CognitiveQualityDiagnosticStatus,
    primary_recommendation: CognitiveQualityDiagnosticRecommendation,
    signals: tuple[CognitiveQualityDiagnosticSignal, ...],
) -> str:
    if not isinstance(workspace_id, WorkspaceId):
        raise ValueError("cognitive_quality_diagnostic_workspace_invalid")
    if reference_observed_count is not None:
        _bounded_nonnegative(reference_observed_count, "cognitive_quality_diagnostic_reference_count_invalid")
    if candidate_observed_count is not None:
        _bounded_nonnegative(candidate_observed_count, "cognitive_quality_diagnostic_candidate_count_invalid")
    ordered = tuple(sorted(signals, key=lambda s: (s.domain, s.metric, s.segment_key or "")))
    payload = {
        "contract_version": D157_CONTRACT_VERSION,
        "reference_baseline": D157_REFERENCE_BASELINE,
        "policy_version": D157_POLICY_VERSION,
        "workspace_id": workspace_id.value,
        "reference_since": _time_token(reference_since),
        "reference_until": _time_token(reference_until),
        "candidate_since": _time_token(candidate_since),
        "candidate_until": _time_token(candidate_until),
        "reference_observed_count": reference_observed_count,
        "candidate_observed_count": candidate_observed_count,
        "status": status,
        "primary_recommendation": primary_recommendation,
        "signals": [_signal_payload(item) for item in ordered],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveQualityDiagnosticAdvisory:
    workspace_id: WorkspaceId
    reference_since: datetime
    reference_until: datetime
    candidate_since: datetime
    candidate_until: datetime
    reference_observed_count: int | None
    candidate_observed_count: int | None
    status: CognitiveQualityDiagnosticStatus
    primary_recommendation: CognitiveQualityDiagnosticRecommendation
    signals: tuple[CognitiveQualityDiagnosticSignal, ...]
    diagnostic_fingerprint: str

    contract_version: Literal["1"] = D157_CONTRACT_VERSION
    reference_baseline: str = D157_REFERENCE_BASELINE
    policy_version: str = D157_POLICY_VERSION

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
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_diagnostic_workspace_invalid")
        if self.contract_version != D157_CONTRACT_VERSION:
            raise ValueError("cognitive_quality_diagnostic_contract_invalid")
        if self.reference_baseline != D157_REFERENCE_BASELINE:
            raise ValueError("cognitive_quality_diagnostic_baseline_invalid")
        if self.policy_version != D157_POLICY_VERSION:
            raise ValueError("cognitive_quality_diagnostic_policy_invalid")
        for value in (self.reference_since, self.reference_until, self.candidate_since, self.candidate_until):
            if not isinstance(value, datetime):
                raise ValueError("cognitive_quality_diagnostic_time_invalid")
        if self.reference_observed_count is not None:
            _bounded_nonnegative(self.reference_observed_count, "cognitive_quality_diagnostic_reference_count_invalid")
        if self.candidate_observed_count is not None:
            _bounded_nonnegative(self.candidate_observed_count, "cognitive_quality_diagnostic_candidate_count_invalid")

        signals = tuple(self.signals)
        if any(not isinstance(item, CognitiveQualityDiagnosticSignal) for item in signals):
            raise ValueError("cognitive_quality_diagnostic_signal_invalid")
        ordered = tuple(sorted(signals, key=lambda s: (s.domain, s.metric, s.segment_key or "")))
        if signals != ordered:
            raise ValueError("cognitive_quality_diagnostic_signal_order_invalid")

        if self.status in {"invalid_evidence", "insufficient_evidence", "no_material_signal"}:
            if self.primary_recommendation != "continue_observation" or signals:
                raise ValueError("cognitive_quality_diagnostic_status_projection_invalid")
        elif self.status == "investigation_recommended":
            if not signals:
                raise ValueError("cognitive_quality_diagnostic_status_projection_invalid")
            domains = {item.domain for item in signals}
            if len(domains) >= 2:
                if self.primary_recommendation != "benchmark_review_recommended":
                    raise ValueError("cognitive_quality_diagnostic_multi_domain_invalid")
            elif self.primary_recommendation != _DOMAIN_RECOMMENDATION[next(iter(domains))]:
                raise ValueError("cognitive_quality_diagnostic_primary_invalid")
        else:
            raise ValueError("cognitive_quality_diagnostic_status_invalid")

        for name in (
            "learning_authority",
            "memory_write_authority",
            "experience_trust_authority",
            "routing_authority",
            "model_selection_authority",
            "provider_selection_authority",
            "profile_selection_authority",
            "prompt_mutation_authority",
            "context_mutation_authority",
            "policy_mutation_authority",
            "configuration_authority",
            "execution_authority",
            "benchmark_promotion_authority",
            "rollout_authority",
            "automatic_learning",
            "automatic_optimization",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_quality_diagnostic_{name}_invalid")

        expected = compute_cognitive_quality_diagnostic_fingerprint(
            workspace_id=self.workspace_id,
            reference_since=self.reference_since,
            reference_until=self.reference_until,
            candidate_since=self.candidate_since,
            candidate_until=self.candidate_until,
            reference_observed_count=self.reference_observed_count,
            candidate_observed_count=self.candidate_observed_count,
            status=self.status,
            primary_recommendation=self.primary_recommendation,
            signals=signals,
        )
        if self.diagnostic_fingerprint != expected:
            raise ValueError("cognitive_quality_diagnostic_fingerprint_invalid")


__all__ = [
    "CognitiveQualityDiagnosticAdvisory",
    "CognitiveQualityDiagnosticDomain",
    "CognitiveQualityDiagnosticRecommendation",
    "CognitiveQualityDiagnosticSignal",
    "CognitiveQualityDiagnosticStatus",
    "D157_CONTRACT_VERSION",
    "D157_MATERIAL_RATE_INCREASE_BPS",
    "D157_MATERIAL_SUBGROUP_GAP_BPS",
    "D157_MIN_PERIOD_OBSERVATIONS",
    "D157_MIN_SUBGROUP_OBSERVATIONS",
    "D157_MIN_SUPPORTING_EVENT_INCREASE",
    "D157_POLICY_VERSION",
    "D157_RATE_SCALE_BPS",
    "D157_REFERENCE_BASELINE",
    "compute_cognitive_quality_diagnostic_fingerprint",
]
