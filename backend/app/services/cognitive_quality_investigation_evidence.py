"""D159 deterministic read-only cognitive quality investigation evidence assembly."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal

from app.contracts.cognitive_quality_investigation_evidence import (
    CognitiveQualityInvestigationEvidenceEntry,
    CognitiveQualityInvestigationEvidencePacket,
    CognitiveQualityInvestigationEvidenceValue,
    compute_cognitive_quality_investigation_evidence_packet_fingerprint,
)
from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationItem,
    CognitiveQualityInvestigationPlan,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationPlanningService,
)
from app.services.cognitive_quality_summary import (
    CognitiveQualityBreakdown,
    CognitiveQualityComparison,
    CognitiveQualityCounts,
    CognitiveQualitySummary,
    CognitiveQualitySummaryService,
)

_AUTHORITY_FIELDS = (
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
_PERIOD_METRICS = (
    "observed_count",
    "verified_success_count",
    "bounded_insufficiency_count",
    "adverse_outcome_count",
    "invalid_evidence_count",
)
_TERMINAL_METRICS = (
    "terminal_completed_count",
    "terminal_insufficient_count",
    "terminal_failed_count",
)
_VERIFICATION_METRICS = (
    "verification_pass_count",
    "verification_revise_count",
    "verification_insufficient_evidence_count",
    "verification_invalid_cognition_count",
)
_CONFIDENCE_METRICS = (
    "confidence_sufficient_count",
    "confidence_limited_count",
    "confidence_insufficient_count",
    "confidence_unknown_count",
)
_REVISION_CRITIC_METRICS = ("revised_turn_count", "critic_exhausted_count")
_ALL_COUNT_METRICS = tuple(field.name for field in fields(CognitiveQualityCounts))


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _same_time(left: datetime, right: datetime) -> bool:
    return _aware(left) and _aware(right) and left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def _valid_periods(reference_since, reference_until, candidate_since, candidate_until) -> bool:
    return (
        all(_aware(v) for v in (reference_since, reference_until, candidate_since, candidate_until))
        and reference_since < reference_until
        and candidate_since < candidate_until
        and reference_until <= candidate_since
    )


def _bounded_key(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value.encode("utf-8")) <= 256
        and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    )


def _clone_plan(plan: object) -> CognitiveQualityInvestigationPlan | None:
    if type(plan) is not CognitiveQualityInvestigationPlan:
        return None
    try:
        items = tuple(
            CognitiveQualityInvestigationItem(
                domain=item.domain,
                source_metric=item.source_metric,
                segment_key=item.segment_key,
                investigation_kind=item.investigation_kind,
                evidence_requirements=tuple(item.evidence_requirements),
                benchmark_scope_kind=item.benchmark_scope_kind,
                benchmark_segment_key=item.benchmark_segment_key,
                source_reference_numerator=item.source_reference_numerator,
                source_reference_denominator=item.source_reference_denominator,
                source_candidate_numerator=item.source_candidate_numerator,
                source_candidate_denominator=item.source_candidate_denominator,
                source_delta_bps=item.source_delta_bps,
            )
            for item in plan.items
        )
        clone = CognitiveQualityInvestigationPlan(
            workspace_id=plan.workspace_id,
            reference_since=plan.reference_since,
            reference_until=plan.reference_until,
            candidate_since=plan.candidate_since,
            candidate_until=plan.candidate_until,
            source_diagnostic_fingerprint=plan.source_diagnostic_fingerprint,
            source_diagnostic_status=plan.source_diagnostic_status,
            source_primary_recommendation=plan.source_primary_recommendation,
            status=plan.status,
            primary_action=plan.primary_action,
            benchmark_review_recommended=plan.benchmark_review_recommended,
            items=items,
            plan_fingerprint=plan.plan_fingerprint,
            contract_version=plan.contract_version,
            reference_baseline=plan.reference_baseline,
            policy_version=plan.policy_version,
            learning_authority=plan.learning_authority,
            memory_write_authority=plan.memory_write_authority,
            experience_trust_authority=plan.experience_trust_authority,
            routing_authority=plan.routing_authority,
            model_selection_authority=plan.model_selection_authority,
            provider_selection_authority=plan.provider_selection_authority,
            profile_selection_authority=plan.profile_selection_authority,
            prompt_mutation_authority=plan.prompt_mutation_authority,
            context_mutation_authority=plan.context_mutation_authority,
            policy_mutation_authority=plan.policy_mutation_authority,
            configuration_authority=plan.configuration_authority,
            execution_authority=plan.execution_authority,
            benchmark_promotion_authority=plan.benchmark_promotion_authority,
            rollout_authority=plan.rollout_authority,
            automatic_learning=plan.automatic_learning,
            automatic_optimization=plan.automatic_optimization,
        )
    except (AttributeError, TypeError, ValueError):
        return None
    return clone if clone == plan else None


def _plan_valid(plan: object, *, workspace_id: WorkspaceId, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime) -> CognitiveQualityInvestigationPlan | None:
    clone = _clone_plan(plan)
    if clone is None or clone.workspace_id is not workspace_id:
        return None
    if not all((
        _same_time(clone.reference_since, reference_since),
        _same_time(clone.reference_until, reference_until),
        _same_time(clone.candidate_since, candidate_since),
        _same_time(clone.candidate_until, candidate_until),
    )):
        return None
    if clone.status != "invalid_evidence" and not _valid_periods(reference_since, reference_until, candidate_since, candidate_until):
        return None
    if any(getattr(clone, name, None) is not False for name in _AUTHORITY_FIELDS):
        return None
    return clone


def _valid_counts(counts: object) -> bool:
    if type(counts) is not CognitiveQualityCounts:
        return False
    values = {field.name: getattr(counts, field.name) for field in fields(CognitiveQualityCounts)}
    if any(type(value) is not int or value < 0 for value in values.values()):
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


def _valid_breakdowns(items: object, overall: CognitiveQualityCounts) -> bool:
    if not isinstance(items, tuple):
        return False
    keys: set[str] = set()
    totals = {field.name: 0 for field in fields(CognitiveQualityCounts)}
    for item in items:
        if type(item) is not CognitiveQualityBreakdown or not _bounded_key(item.key) or item.key in keys or not _valid_counts(item.counts):
            return False
        keys.add(item.key)
        for name in totals:
            totals[name] += getattr(item.counts, name)
    return all(totals[name] == getattr(overall, name) for name in totals)


def _valid_summary(summary: object, *, workspace_id: WorkspaceId, since: datetime, until: datetime) -> bool:
    return (
        type(summary) is CognitiveQualitySummary
        and summary.workspace_id is workspace_id
        and summary.since is not None
        and summary.until is not None
        and _same_time(summary.since, since)
        and _same_time(summary.until, until)
        and _valid_counts(summary.counts)
        and _valid_breakdowns(summary.by_experience_cohort, summary.counts)
        and _valid_breakdowns(summary.by_task_kind, summary.counts)
    )


def _rate_text(numerator: int, denominator: int) -> str | None:
    return None if denominator == 0 else format(Decimal(numerator) / Decimal(denominator), ".6f")


def _valid_count_deltas(comparison: CognitiveQualityComparison) -> bool:
    if not isinstance(comparison.count_deltas, tuple) or len(comparison.count_deltas) != len(_COUNT_DELTA_METRICS):
        return False
    seen: set[str] = set()
    for delta in comparison.count_deltas:
        metric = getattr(delta, "metric", None)
        if metric not in _COUNT_DELTA_METRICS or metric in seen:
            return False
        seen.add(metric)
        reference = getattr(comparison.reference.counts, metric)
        candidate = getattr(comparison.candidate.counts, metric)
        if (
            getattr(delta, "reference_count", None) != reference
            or getattr(delta, "candidate_count", None) != candidate
            or getattr(delta, "delta_count", None) != candidate - reference
        ):
            return False
    return seen == set(_COUNT_DELTA_METRICS)


def _valid_rate_deltas(comparison: CognitiveQualityComparison) -> bool:
    if not isinstance(comparison.rate_deltas, tuple) or len(comparison.rate_deltas) != len(_RATE_DELTA_METRICS):
        return False
    expected = dict(_RATE_DELTA_METRICS)
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
        rr, cr = _rate_text(rn, rd), _rate_text(cn, cd)
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
    return (
        type(comparison) is CognitiveQualityComparison
        and _valid_summary(comparison.reference, workspace_id=workspace_id, since=reference_since, until=reference_until)
        and _valid_summary(comparison.candidate, workspace_id=workspace_id, since=candidate_since, until=candidate_until)
        and _valid_count_deltas(comparison)
        and _valid_rate_deltas(comparison)
    )


def _breakdown_map(items: tuple[CognitiveQualityBreakdown, ...]) -> dict[str, CognitiveQualityCounts]:
    return {item.key: item.counts for item in items}


def _zero_counts() -> CognitiveQualityCounts:
    return CognitiveQualityCounts()


def _source_lineage(item: CognitiveQualityInvestigationItem, comparison: CognitiveQualityComparison) -> tuple[int, int, int, int] | None:
    reference, candidate = comparison.reference.counts, comparison.candidate.counts
    direct = {
        "invalid_evidence_rate": "invalid_evidence_count",
        "bounded_insufficiency_rate": "bounded_insufficiency_count",
        "adverse_outcome_rate": "adverse_outcome_count",
        "verification_invalid_cognition_rate": "verification_invalid_cognition_count",
        "terminal_failed_rate": "terminal_failed_count",
        "critic_exhausted_rate": "critic_exhausted_count",
        "revised_turn_rate": "revised_turn_count",
    }
    if item.source_metric in direct:
        field = direct[item.source_metric]
        return getattr(reference, field), reference.observed_count, getattr(candidate, field), candidate.observed_count
    if item.source_metric == "confidence_concern_rate":
        ref_num = reference.confidence_limited_count + reference.confidence_insufficient_count + reference.confidence_unknown_count
        ref_den = reference.confidence_sufficient_count + ref_num
        cand_num = candidate.confidence_limited_count + candidate.confidence_insufficient_count + candidate.confidence_unknown_count
        cand_den = candidate.confidence_sufficient_count + cand_num
        return ref_num, ref_den, cand_num, cand_den
    if item.source_metric == "adverse_outcome_rate_vs_overall":
        if not _bounded_key(item.segment_key):
            return None
        task = _breakdown_map(comparison.candidate.by_task_kind).get(item.segment_key)
        if task is None:
            return None
        return candidate.adverse_outcome_count, candidate.observed_count, task.adverse_outcome_count, task.observed_count
    if item.source_metric == "adverse_outcome_rate_gap":
        if not _bounded_key(item.segment_key):
            return None
        assert item.segment_key is not None
        parts = item.segment_key.split("|")
        if len(parts) != 2:
            return None
        cohorts = _breakdown_map(comparison.candidate.by_experience_cohort)
        left, right = cohorts.get(parts[0]), cohorts.get(parts[1])
        if left is None or right is None:
            return None
        return left.adverse_outcome_count, left.observed_count, right.adverse_outcome_count, right.observed_count
    return None


def _lineage_matches(item: CognitiveQualityInvestigationItem, comparison: CognitiveQualityComparison) -> bool:
    lineage = _source_lineage(item, comparison)
    return lineage == (
        item.source_reference_numerator,
        item.source_reference_denominator,
        item.source_candidate_numerator,
        item.source_candidate_denominator,
    )


def _values_for_metrics(metrics: tuple[str, ...], reference: CognitiveQualityCounts, candidate: CognitiveQualityCounts, *, segment_key: str | None = None) -> tuple[CognitiveQualityInvestigationEvidenceValue, ...]:
    return tuple(
        CognitiveQualityInvestigationEvidenceValue(
            metric=metric,
            segment_key=segment_key,
            reference_count=getattr(reference, metric),
            candidate_count=getattr(candidate, metric),
        )
        for metric in metrics
    )


def _breakdown_values(reference_items: tuple[CognitiveQualityBreakdown, ...], candidate_items: tuple[CognitiveQualityBreakdown, ...]) -> tuple[CognitiveQualityInvestigationEvidenceValue, ...]:
    reference, candidate = _breakdown_map(reference_items), _breakdown_map(candidate_items)
    result: list[CognitiveQualityInvestigationEvidenceValue] = []
    for key in sorted(set(reference) | set(candidate)):
        result.extend(_values_for_metrics(_ALL_COUNT_METRICS, reference.get(key, _zero_counts()), candidate.get(key, _zero_counts()), segment_key=key))
    return tuple(result)


def _available_values(requirement: str, comparison: CognitiveQualityComparison) -> tuple[CognitiveQualityInvestigationEvidenceValue, ...]:
    reference, candidate = comparison.reference.counts, comparison.candidate.counts
    if requirement == "d156_period_counts":
        return _values_for_metrics(_PERIOD_METRICS, reference, candidate)
    if requirement == "d156_terminal_counts":
        return _values_for_metrics(_TERMINAL_METRICS, reference, candidate)
    if requirement == "d156_verification_counts":
        return _values_for_metrics(_VERIFICATION_METRICS, reference, candidate)
    if requirement == "d156_confidence_counts":
        return _values_for_metrics(_CONFIDENCE_METRICS, reference, candidate)
    if requirement == "d156_revision_critic_counts":
        return _values_for_metrics(_REVISION_CRITIC_METRICS, reference, candidate)
    if requirement == "d156_task_kind_breakdown":
        return _breakdown_values(comparison.reference.by_task_kind, comparison.candidate.by_task_kind)
    if requirement == "d156_experience_cohort_breakdown":
        return _breakdown_values(comparison.reference.by_experience_cohort, comparison.candidate.by_experience_cohort)
    raise ValueError("cognitive_quality_investigation_evidence_requirement_invalid")


def _entry(*, item: CognitiveQualityInvestigationItem, requirement: str, comparison: CognitiveQualityComparison | None, comparison_is_valid: bool, lineage_matches: bool) -> CognitiveQualityInvestigationEvidenceEntry:
    common = dict(
        domain=item.domain,
        source_metric=item.source_metric,
        segment_key=item.segment_key,
        investigation_kind=item.investigation_kind,
        evidence_requirement=requirement,
    )
    empty = dict(values=(), benchmark_scope_kind=None, benchmark_segment_key=None, benchmark_candidate_task_keys=())
    if requirement == "future_matched_cohort_control":
        return CognitiveQualityInvestigationEvidenceEntry(
            **common, availability="future_required",
            availability_reason="future_governed_collection_required", **empty
        )
    if not comparison_is_valid or comparison is None:
        return CognitiveQualityInvestigationEvidenceEntry(
            **common, availability="unavailable", availability_reason="comparison_unavailable", **empty
        )
    if not lineage_matches:
        return CognitiveQualityInvestigationEvidenceEntry(
            **common, availability="unavailable", availability_reason="source_lineage_mismatch", **empty
        )
    if requirement == "d138_d139_targeted_benchmark_slice":
        if item.benchmark_scope_kind == "task_kind_segment":
            return CognitiveQualityInvestigationEvidenceEntry(
                **common, availability="descriptor_only", availability_reason="benchmark_descriptor_only",
                values=(), benchmark_scope_kind="task_kind_segment",
                benchmark_segment_key=item.benchmark_segment_key, benchmark_candidate_task_keys=(),
            )
        if item.benchmark_scope_kind == "derive_from_candidate_task_breakdown":
            keys = tuple(sorted(entry.key for entry in comparison.candidate.by_task_kind))
            if keys:
                return CognitiveQualityInvestigationEvidenceEntry(
                    **common, availability="descriptor_only", availability_reason="benchmark_descriptor_only",
                    values=(), benchmark_scope_kind="derive_from_candidate_task_breakdown",
                    benchmark_segment_key=None, benchmark_candidate_task_keys=keys,
                )
        return CognitiveQualityInvestigationEvidenceEntry(
            **common, availability="unavailable", availability_reason="source_lineage_mismatch", **empty
        )
    return CognitiveQualityInvestigationEvidenceEntry(
        **common, availability="available", availability_reason="assembled",
        values=_available_values(requirement, comparison),
        benchmark_scope_kind=None, benchmark_segment_key=None, benchmark_candidate_task_keys=(),
    )


def _build_packet(*, workspace_id: WorkspaceId, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime, source_plan: CognitiveQualityInvestigationPlan | None, status: str, primary_action: str, entries: tuple[CognitiveQualityInvestigationEvidenceEntry, ...] = ()) -> CognitiveQualityInvestigationEvidencePacket:
    source_plan_fingerprint = source_plan.plan_fingerprint if source_plan is not None else None
    source_plan_status = source_plan.status if source_plan is not None else None
    source_plan_primary_action = source_plan.primary_action if source_plan is not None else None
    source_diagnostic_fingerprint = source_plan.source_diagnostic_fingerprint if source_plan is not None else None
    benchmark_review_recommended = source_plan.benchmark_review_recommended if source_plan is not None else False
    fingerprint = compute_cognitive_quality_investigation_evidence_packet_fingerprint(
        workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until,
        candidate_since=candidate_since, candidate_until=candidate_until,
        source_plan_fingerprint=source_plan_fingerprint, source_plan_status=source_plan_status,
        source_plan_primary_action=source_plan_primary_action,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark_review_recommended,
        status=status, primary_action=primary_action, entries=entries,
    )
    return CognitiveQualityInvestigationEvidencePacket(
        workspace_id=workspace_id, reference_since=reference_since, reference_until=reference_until,
        candidate_since=candidate_since, candidate_until=candidate_until,
        source_plan_fingerprint=source_plan_fingerprint, source_plan_status=source_plan_status,
        source_plan_primary_action=source_plan_primary_action,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        benchmark_review_recommended=benchmark_review_recommended,
        status=status, primary_action=primary_action, entries=entries, packet_fingerprint=fingerprint,
    )


class CognitiveQualityInvestigationEvidenceService:
    """Read-only D159 composition over D158 planning and D156 aggregate comparison."""

    def __init__(self, planning_service: CognitiveQualityInvestigationPlanningService, summary_service: CognitiveQualitySummaryService, *, workspace_id: WorkspaceId) -> None:
        if not isinstance(planning_service, CognitiveQualityInvestigationPlanningService):
            raise ValueError("cognitive_quality_investigation_evidence_planning_service_invalid")
        if not isinstance(summary_service, CognitiveQualitySummaryService):
            raise ValueError("cognitive_quality_investigation_evidence_summary_service_invalid")
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("cognitive_quality_investigation_evidence_workspace_invalid")
        self._planning, self._summary, self._workspace_id = planning_service, summary_service, workspace_id

    def assemble(self, *, reference_since: datetime, reference_until: datetime, candidate_since: datetime, candidate_until: datetime) -> CognitiveQualityInvestigationEvidencePacket:
        try:
            raw_plan = self._planning.plan(
                reference_since=reference_since, reference_until=reference_until,
                candidate_since=candidate_since, candidate_until=candidate_until,
            )
        except ValueError:
            raw_plan = None
        plan = _plan_valid(
            raw_plan, workspace_id=self._workspace_id,
            reference_since=reference_since, reference_until=reference_until,
            candidate_since=candidate_since, candidate_until=candidate_until,
        )
        if plan is None:
            return _build_packet(
                workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until,
                candidate_since=candidate_since, candidate_until=candidate_until, source_plan=None,
                status="invalid_evidence", primary_action="repair_source_evidence",
            )
        if plan.status == "invalid_evidence":
            return _build_packet(
                workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until,
                candidate_since=candidate_since, candidate_until=candidate_until, source_plan=plan,
                status="invalid_evidence", primary_action="repair_source_evidence",
            )
        if plan.status in {"observation_required", "no_material_investigation"}:
            return _build_packet(
                workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until,
                candidate_since=candidate_since, candidate_until=candidate_until, source_plan=plan,
                status="no_assembly_required", primary_action="continue_observation",
            )

        try:
            raw_comparison = self._summary.compare(
                reference_since=reference_since, reference_until=reference_until,
                candidate_since=candidate_since, candidate_until=candidate_until,
            )
        except ValueError:
            raw_comparison = None
        comparison_is_valid = _comparison_valid(
            raw_comparison, workspace_id=self._workspace_id,
            reference_since=reference_since, reference_until=reference_until,
            candidate_since=candidate_since, candidate_until=candidate_until,
        )
        comparison = raw_comparison if comparison_is_valid else None
        assert comparison is None or isinstance(comparison, CognitiveQualityComparison)

        entries: list[CognitiveQualityInvestigationEvidenceEntry] = []
        for item in plan.items:
            lineage_matches = comparison is not None and _lineage_matches(item, comparison)
            for requirement in item.evidence_requirements:
                entries.append(_entry(
                    item=item, requirement=requirement, comparison=comparison,
                    comparison_is_valid=comparison_is_valid, lineage_matches=lineage_matches,
                ))
        ordered = tuple(entries)
        complete = bool(ordered) and all(entry.availability == "available" for entry in ordered)
        return _build_packet(
            workspace_id=self._workspace_id, reference_since=reference_since, reference_until=reference_until,
            candidate_since=candidate_since, candidate_until=candidate_until, source_plan=plan,
            status="evidence_complete" if complete else "evidence_incomplete",
            primary_action="review_assembled_evidence" if complete else "review_missing_evidence",
            entries=ordered,
        )


__all__ = ["CognitiveQualityInvestigationEvidenceService"]
