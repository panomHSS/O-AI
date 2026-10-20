"""D157 deterministic read-only cognitive quality diagnostic advisory."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from decimal import Decimal

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticAdvisory,
    CognitiveQualityDiagnosticSignal,
    D157_MATERIAL_RATE_INCREASE_BPS,
    D157_MATERIAL_SUBGROUP_GAP_BPS,
    D157_MIN_PERIOD_OBSERVATIONS,
    D157_MIN_SUBGROUP_OBSERVATIONS,
    D157_MIN_SUPPORTING_EVENT_INCREASE,
    D157_RATE_SCALE_BPS,
    compute_cognitive_quality_diagnostic_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_summary import (
    CognitiveQualityBreakdown,
    CognitiveQualityComparison,
    CognitiveQualityCounts,
    CognitiveQualitySummary,
    CognitiveQualitySummaryService,
)

_COUNT_DELTA_METRICS = (
    "observed_count",
    "verified_success_count",
    "bounded_insufficiency_count",
    "adverse_outcome_count",
    "invalid_evidence_count",
    "revised_turn_count",
    "critic_exhausted_count",
)
_RATE_DELTA_METRICS = (
    ("verified_success_rate", "verified_success_count"),
    ("bounded_insufficiency_rate", "bounded_insufficiency_count"),
    ("adverse_outcome_rate", "adverse_outcome_count"),
    ("invalid_evidence_rate", "invalid_evidence_count"),
)
_RECOMMENDATION = {
    "evidence_integrity": "investigate_evidence_integrity",
    "cognition_validity": "investigate_cognition",
    "critic_revision": "investigate_critic",
    "evidence_sufficiency": "investigate_evidence_sufficiency",
    "task_concentration": "investigate_task_cohort",
    "experience_cohort_difference": "investigate_experience_cohort",
}


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _periods_valid(reference_since, reference_until, candidate_since, candidate_until) -> bool:
    if not all(_aware(v) for v in (reference_since, reference_until, candidate_since, candidate_until)):
        return False
    return reference_since < reference_until and candidate_since < candidate_until and reference_until <= candidate_since


def _rate_bps(numerator: int, denominator: int) -> int:
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError("cognitive_quality_diagnostic_rate_input_invalid")
    if numerator < 0 or denominator <= 0 or numerator > denominator:
        raise ValueError("cognitive_quality_diagnostic_rate_input_invalid")
    return numerator * D157_RATE_SCALE_BPS // denominator


def _rate_text(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return format(Decimal(numerator) / Decimal(denominator), ".6f")


def _valid_counts(counts: object) -> bool:
    if type(counts) is not CognitiveQualityCounts:
        return False
    values = {f.name: getattr(counts, f.name) for f in fields(CognitiveQualityCounts)}
    if any(type(v) is not int or v < 0 for v in values.values()):
        return False
    observed = counts.observed_count
    if counts.verified_success_count + counts.bounded_insufficiency_count + counts.adverse_outcome_count + counts.invalid_evidence_count != observed:
        return False
    if counts.terminal_completed_count + counts.terminal_insufficient_count + counts.terminal_failed_count != observed:
        return False
    if counts.verification_pass_count + counts.verification_revise_count + counts.verification_insufficient_evidence_count + counts.verification_invalid_cognition_count > observed:
        return False
    if counts.revised_turn_count > observed or counts.critic_exhausted_count > observed:
        return False
    if counts.confidence_sufficient_count + counts.confidence_limited_count + counts.confidence_insufficient_count + counts.confidence_unknown_count > observed:
        return False
    return True


def _bounded_key(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip() and len(value.encode("utf-8")) <= 64 and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _valid_breakdowns(items: object, overall: CognitiveQualityCounts) -> bool:
    if not isinstance(items, tuple):
        return False
    keys: set[str] = set()
    totals = {f.name: 0 for f in fields(CognitiveQualityCounts)}
    for item in items:
        if type(item) is not CognitiveQualityBreakdown or not _bounded_key(item.key) or item.key in keys:
            return False
        if not _valid_counts(item.counts):
            return False
        keys.add(item.key)
        for name in totals:
            totals[name] += getattr(item.counts, name)
    return all(totals[name] == getattr(overall, name) for name in totals)


def _valid_summary(summary: object, *, workspace_id: WorkspaceId, since: datetime, until: datetime) -> bool:
    return (
        type(summary) is CognitiveQualitySummary
        and summary.workspace_id is workspace_id
        and summary.since == since
        and summary.until == until
        and _valid_counts(summary.counts)
        and _valid_breakdowns(summary.by_experience_cohort, summary.counts)
        and _valid_breakdowns(summary.by_task_kind, summary.counts)
    )


def _valid_count_deltas(comparison: CognitiveQualityComparison) -> bool:
    if not isinstance(comparison.count_deltas, tuple) or len(comparison.count_deltas) != len(_COUNT_DELTA_METRICS):
        return False
    seen: set[str] = set()
    for delta in comparison.count_deltas:
        metric = getattr(delta, "metric", None)
        if metric not in _COUNT_DELTA_METRICS or metric in seen:
            return False
        seen.add(metric)
        expected_ref = getattr(comparison.reference.counts, metric)
        expected_cand = getattr(comparison.candidate.counts, metric)
        if getattr(delta, "reference_count", None) != expected_ref or getattr(delta, "candidate_count", None) != expected_cand or getattr(delta, "delta_count", None) != expected_cand - expected_ref:
            return False
    return seen == set(_COUNT_DELTA_METRICS)


def _valid_rate_deltas(comparison: CognitiveQualityComparison) -> bool:
    if not isinstance(comparison.rate_deltas, tuple) or len(comparison.rate_deltas) != len(_RATE_DELTA_METRICS):
        return False
    expected = {metric: count_name for metric, count_name in _RATE_DELTA_METRICS}
    seen: set[str] = set()
    for delta in comparison.rate_deltas:
        metric = getattr(delta, "metric", None)
        if metric not in expected or metric in seen:
            return False
        seen.add(metric)
        count_name = expected[metric]
        rn = getattr(comparison.reference.counts, count_name)
        cn = getattr(comparison.candidate.counts, count_name)
        rd = comparison.reference.counts.observed_count
        cd = comparison.candidate.counts.observed_count
        rr = _rate_text(rn, rd)
        cr = _rate_text(cn, cd)
        dr = None if rr is None or cr is None else format(Decimal(cr) - Decimal(rr), ".6f")
        if (
            getattr(delta, "reference_numerator", None) != rn
            or getattr(delta, "candidate_numerator", None) != cn
            or getattr(delta, "reference_denominator", None) != rd
            or getattr(delta, "candidate_denominator", None) != cd
            or getattr(delta, "reference_rate", None) != rr
            or getattr(delta, "candidate_rate", None) != cr
            or getattr(delta, "delta_rate", None) != dr
        ):
            return False
    return seen == set(expected)


def _comparison_valid(comparison: object, *, workspace_id: WorkspaceId, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime) -> bool:
    if type(comparison) is not CognitiveQualityComparison:
        return False
    return (
        _valid_summary(comparison.reference, workspace_id=workspace_id, since=reference_since, until=reference_until)
        and _valid_summary(comparison.candidate, workspace_id=workspace_id, since=candidate_since, until=candidate_until)
        and _valid_count_deltas(comparison)
        and _valid_rate_deltas(comparison)
    )


def _material_signal(*, reference_numerator: int, reference_denominator: int, candidate_numerator: int, candidate_denominator: int) -> tuple[bool, int]:
    delta_bps = _rate_bps(candidate_numerator, candidate_denominator) - _rate_bps(reference_numerator, reference_denominator)
    supported = candidate_numerator - reference_numerator >= D157_MIN_SUPPORTING_EVENT_INCREASE
    return delta_bps >= D157_MATERIAL_RATE_INCREASE_BPS and supported, delta_bps


def _build(*, workspace_id: WorkspaceId, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime, reference_observed_count: int | None, candidate_observed_count: int | None, status: str, recommendation: str, signals: tuple[CognitiveQualityDiagnosticSignal, ...] = ()) -> CognitiveQualityDiagnosticAdvisory:
    ordered = tuple(sorted(signals, key=lambda s: (s.domain, s.metric, s.segment_key or "")))
    fingerprint = compute_cognitive_quality_diagnostic_fingerprint(
        workspace_id=workspace_id,
        reference_since=reference_since,
        reference_until=reference_until,
        candidate_since=candidate_since,
        candidate_until=candidate_until,
        reference_observed_count=reference_observed_count,
        candidate_observed_count=candidate_observed_count,
        status=status,  # type: ignore[arg-type]
        primary_recommendation=recommendation,  # type: ignore[arg-type]
        signals=ordered,
    )
    return CognitiveQualityDiagnosticAdvisory(
        workspace_id=workspace_id,
        reference_since=reference_since,
        reference_until=reference_until,
        candidate_since=candidate_since,
        candidate_until=candidate_until,
        reference_observed_count=reference_observed_count,
        candidate_observed_count=candidate_observed_count,
        status=status,  # type: ignore[arg-type]
        primary_recommendation=recommendation,  # type: ignore[arg-type]
        signals=ordered,
        diagnostic_fingerprint=fingerprint,
    )


class CognitiveQualityDiagnosticEvaluator:
    """Pure D157 evaluator; observational signals are not causal conclusions."""

    @classmethod
    def evaluate(cls, *, comparison: object | None, workspace_id: WorkspaceId, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime) -> CognitiveQualityDiagnosticAdvisory:
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_diagnostic_workspace_invalid")
        if not _periods_valid(reference_since, reference_until, candidate_since, candidate_until):
            return _build(workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until, reference_observed_count=None, candidate_observed_count=None, status="invalid_evidence", recommendation="continue_observation")
        if not _comparison_valid(comparison, workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until):
            return _build(workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until, reference_observed_count=None, candidate_observed_count=None, status="invalid_evidence", recommendation="continue_observation")

        assert isinstance(comparison, CognitiveQualityComparison)
        reference = comparison.reference
        candidate = comparison.candidate
        rden = reference.counts.observed_count
        cden = candidate.counts.observed_count
        if rden < D157_MIN_PERIOD_OBSERVATIONS or cden < D157_MIN_PERIOD_OBSERVATIONS:
            return _build(workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until, reference_observed_count=rden, candidate_observed_count=cden, status="insufficient_evidence", recommendation="continue_observation")

        signals: list[CognitiveQualityDiagnosticSignal] = []

        def longitudinal(domain: str, metric: str, ref_num: int, cand_num: int) -> None:
            material, delta = _material_signal(reference_numerator=ref_num, reference_denominator=rden, candidate_numerator=cand_num, candidate_denominator=cden)
            if material:
                signals.append(CognitiveQualityDiagnosticSignal(domain=domain, metric=metric, segment_key=None, reference_numerator=ref_num, reference_denominator=rden, candidate_numerator=cand_num, candidate_denominator=cden, delta_bps=delta))  # type: ignore[arg-type]

        longitudinal("evidence_integrity", "invalid_evidence_rate", reference.counts.invalid_evidence_count, candidate.counts.invalid_evidence_count)
        longitudinal("evidence_sufficiency", "bounded_insufficiency_rate", reference.counts.bounded_insufficiency_count, candidate.counts.bounded_insufficiency_count)

        ref_conf_den = reference.counts.confidence_sufficient_count + reference.counts.confidence_limited_count + reference.counts.confidence_insufficient_count + reference.counts.confidence_unknown_count
        cand_conf_den = candidate.counts.confidence_sufficient_count + candidate.counts.confidence_limited_count + candidate.counts.confidence_insufficient_count + candidate.counts.confidence_unknown_count
        ref_conf_num = reference.counts.confidence_limited_count + reference.counts.confidence_insufficient_count + reference.counts.confidence_unknown_count
        cand_conf_num = candidate.counts.confidence_limited_count + candidate.counts.confidence_insufficient_count + candidate.counts.confidence_unknown_count
        if ref_conf_den >= D157_MIN_SUBGROUP_OBSERVATIONS and cand_conf_den >= D157_MIN_SUBGROUP_OBSERVATIONS:
            material, delta = _material_signal(reference_numerator=ref_conf_num, reference_denominator=ref_conf_den, candidate_numerator=cand_conf_num, candidate_denominator=cand_conf_den)
            if material:
                signals.append(CognitiveQualityDiagnosticSignal(domain="evidence_sufficiency", metric="confidence_concern_rate", segment_key=None, reference_numerator=ref_conf_num, reference_denominator=ref_conf_den, candidate_numerator=cand_conf_num, candidate_denominator=cand_conf_den, delta_bps=delta))

        longitudinal("cognition_validity", "adverse_outcome_rate", reference.counts.adverse_outcome_count, candidate.counts.adverse_outcome_count)
        longitudinal("cognition_validity", "verification_invalid_cognition_rate", reference.counts.verification_invalid_cognition_count, candidate.counts.verification_invalid_cognition_count)
        longitudinal("cognition_validity", "terminal_failed_rate", reference.counts.terminal_failed_count, candidate.counts.terminal_failed_count)
        longitudinal("critic_revision", "critic_exhausted_rate", reference.counts.critic_exhausted_count, candidate.counts.critic_exhausted_count)
        longitudinal("critic_revision", "revised_turn_rate", reference.counts.revised_turn_count, candidate.counts.revised_turn_count)

        overall_adverse_rate = _rate_bps(candidate.counts.adverse_outcome_count, cden)
        for item in candidate.by_task_kind:
            n = item.counts.observed_count
            adverse = item.counts.adverse_outcome_count
            if n < D157_MIN_SUBGROUP_OBSERVATIONS or adverse < D157_MIN_SUPPORTING_EVENT_INCREASE:
                continue
            delta = _rate_bps(adverse, n) - overall_adverse_rate
            if delta >= D157_MATERIAL_SUBGROUP_GAP_BPS:
                signals.append(CognitiveQualityDiagnosticSignal(domain="task_concentration", metric="adverse_outcome_rate_vs_overall", segment_key=item.key, reference_numerator=candidate.counts.adverse_outcome_count, reference_denominator=cden, candidate_numerator=adverse, candidate_denominator=n, delta_bps=delta))

        cohorts = [item for item in candidate.by_experience_cohort if item.counts.observed_count >= D157_MIN_SUBGROUP_OBSERVATIONS]
        cohorts.sort(key=lambda item: item.key)
        for index, left in enumerate(cohorts):
            for right in cohorts[index + 1:]:
                left_num, left_den = left.counts.adverse_outcome_count, left.counts.observed_count
                right_num, right_den = right.counts.adverse_outcome_count, right.counts.observed_count
                delta = _rate_bps(right_num, right_den) - _rate_bps(left_num, left_den)
                if abs(delta) >= D157_MATERIAL_SUBGROUP_GAP_BPS:
                    signals.append(CognitiveQualityDiagnosticSignal(domain="experience_cohort_difference", metric="adverse_outcome_rate_gap", segment_key=f"{left.key}|{right.key}", reference_numerator=left_num, reference_denominator=left_den, candidate_numerator=right_num, candidate_denominator=right_den, delta_bps=delta))

        ordered = tuple(sorted(signals, key=lambda s: (s.domain, s.metric, s.segment_key or "")))
        if not ordered:
            return _build(workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until, reference_observed_count=rden, candidate_observed_count=cden, status="no_material_signal", recommendation="continue_observation")
        domains = {item.domain for item in ordered}
        recommendation = "benchmark_review_recommended" if len(domains) >= 2 else _RECOMMENDATION[next(iter(domains))]
        return _build(workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until, reference_observed_count=rden, candidate_observed_count=cden, status="investigation_recommended", recommendation=recommendation, signals=ordered)


class CognitiveQualityDiagnosticService:
    """Read-only composition over D156 summary evidence."""

    def __init__(self, summary_service: CognitiveQualitySummaryService, *, workspace_id: WorkspaceId) -> None:
        if not isinstance(summary_service, CognitiveQualitySummaryService):
            raise ValueError("cognitive_quality_diagnostic_summary_service_invalid")
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_diagnostic_workspace_invalid")
        self._summary = summary_service
        self._workspace_id = workspace_id

    def diagnose(self, *, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime) -> CognitiveQualityDiagnosticAdvisory:
        if not _periods_valid(reference_since, reference_until, candidate_since, candidate_until):
            return CognitiveQualityDiagnosticEvaluator.evaluate(comparison=None, workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until)
        try:
            comparison = self._summary.compare(reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until)
        except ValueError:
            comparison = None
        return CognitiveQualityDiagnosticEvaluator.evaluate(comparison=comparison, workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until, candidate_since=candidate_since, candidate_until=candidate_until)


__all__ = ["CognitiveQualityDiagnosticEvaluator", "CognitiveQualityDiagnosticService"]
