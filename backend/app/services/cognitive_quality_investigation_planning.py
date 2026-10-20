"""D158 deterministic read-only cognitive quality investigation planning."""
from __future__ import annotations

from datetime import datetime, timezone

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticAdvisory,
    CognitiveQualityDiagnosticSignal,
    D157_CONTRACT_VERSION,
    D157_POLICY_VERSION,
    D157_REFERENCE_BASELINE,
)
from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationItem,
    CognitiveQualityInvestigationPlan,
    cognitive_quality_investigation_item_sort_key,
    compute_cognitive_quality_investigation_plan_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticService

_PLAYBOOK = {
    ("evidence_integrity","invalid_evidence_rate"):(
        "evidence_integrity_review",
        ("d156_period_counts","d156_terminal_counts","d156_verification_counts"),
        "none",
    ),
    ("evidence_sufficiency","bounded_insufficiency_rate"):(
        "bounded_insufficiency_review",
        ("d156_period_counts","d156_confidence_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("evidence_sufficiency","confidence_concern_rate"):(
        "confidence_pattern_review",
        ("d156_confidence_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("cognition_validity","adverse_outcome_rate"):(
        "adverse_outcome_review",
        ("d156_terminal_counts","d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("cognition_validity","verification_invalid_cognition_rate"):(
        "invalid_cognition_review",
        ("d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("cognition_validity","terminal_failed_rate"):(
        "terminal_failure_review",
        ("d156_terminal_counts","d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("critic_revision","critic_exhausted_rate"):(
        "critic_exhaustion_review",
        ("d156_revision_critic_counts","d156_verification_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("critic_revision","revised_turn_rate"):(
        "revision_behavior_review",
        ("d156_revision_critic_counts","d156_terminal_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("task_concentration","adverse_outcome_rate_vs_overall"):(
        "task_kind_concentration_review",
        ("d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "task_kind_segment",
    ),
    ("experience_cohort_difference","adverse_outcome_rate_gap"):(
        "experience_cohort_difference_review",
        ("d156_experience_cohort_breakdown","future_matched_cohort_control"),
        "none",
    ),
}
_LONGITUDINAL_METRICS={
    "invalid_evidence_rate","bounded_insufficiency_rate","confidence_concern_rate",
    "adverse_outcome_rate","verification_invalid_cognition_rate","terminal_failed_rate",
    "critic_exhausted_rate","revised_turn_rate",
}
_AUTHORITY_FIELDS=(
    "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
    "model_selection_authority","provider_selection_authority","profile_selection_authority",
    "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
    "configuration_authority","execution_authority","benchmark_promotion_authority",
    "rollout_authority","automatic_learning","automatic_optimization",
)


def _aware(value: object) -> bool:
    return isinstance(value,datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _same_time(left: object,right: object) -> bool:
    if not isinstance(left,datetime) or not isinstance(right,datetime):
        return False
    la=_aware(left); ra=_aware(right)
    if la != ra: return False
    if not la: return left == right
    return left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def _periods_valid(reference_since: datetime,reference_until: datetime,candidate_since: datetime,candidate_until: datetime) -> bool:
    return (
        all(_aware(v) for v in (reference_since,reference_until,candidate_since,candidate_until))
        and reference_since < reference_until and candidate_since < candidate_until
        and reference_until <= candidate_since
    )


def _bounded_segment(value: object) -> bool:
    return (
        type(value) is str and bool(value) and value == value.strip()
        and len(value.encode("utf-8")) <= 256
        and not any(ord(ch)<32 or ord(ch)==127 for ch in value)
    )


def _clone_signal(signal: object) -> CognitiveQualityDiagnosticSignal | None:
    if type(signal) is not CognitiveQualityDiagnosticSignal:
        return None
    try:
        clone=CognitiveQualityDiagnosticSignal(
            domain=signal.domain,metric=signal.metric,segment_key=signal.segment_key,
            reference_numerator=signal.reference_numerator,reference_denominator=signal.reference_denominator,
            candidate_numerator=signal.candidate_numerator,candidate_denominator=signal.candidate_denominator,
            delta_bps=signal.delta_bps,
        )
    except (TypeError,ValueError):
        return None
    return clone if clone == signal else None


def _source_valid(
    advisory: object,*,workspace_id: WorkspaceId,reference_since: datetime,reference_until: datetime,
    candidate_since: datetime,candidate_until: datetime,
) -> bool:
    if type(advisory) is not CognitiveQualityDiagnosticAdvisory:
        return False
    if advisory.contract_version != D157_CONTRACT_VERSION or advisory.reference_baseline != D157_REFERENCE_BASELINE or advisory.policy_version != D157_POLICY_VERSION:
        return False
    if advisory.workspace_id is not workspace_id:
        return False
    if not all((
        _same_time(advisory.reference_since,reference_since),
        _same_time(advisory.reference_until,reference_until),
        _same_time(advisory.candidate_since,candidate_since),
        _same_time(advisory.candidate_until,candidate_until),
    )):
        return False
    if advisory.status != "invalid_evidence" and not _periods_valid(reference_since,reference_until,candidate_since,candidate_until):
        return False
    if any(getattr(advisory,name,None) is not False for name in _AUTHORITY_FIELDS):
        return False
    if not isinstance(advisory.signals,tuple):
        return False

    clones=[]; identities=set()
    for signal in advisory.signals:
        clone=_clone_signal(signal)
        if clone is None: return False
        identity=(clone.domain,clone.metric,clone.segment_key)
        if identity in identities: return False
        identities.add(identity)
        if (clone.domain,clone.metric) not in _PLAYBOOK:
            return False
        if clone.metric in _LONGITUDINAL_METRICS:
            if clone.segment_key is not None: return False
        elif clone.metric == "adverse_outcome_rate_vs_overall":
            if not _bounded_segment(clone.segment_key): return False
        elif clone.metric == "adverse_outcome_rate_gap":
            if not _bounded_segment(clone.segment_key): return False
            assert clone.segment_key is not None
            parts=clone.segment_key.split("|")
            if len(parts)!=2 or not all(_bounded_segment(p) for p in parts) or not parts[0] < parts[1]:
                return False
        clones.append(clone)

    ordered=tuple(sorted(clones,key=lambda s:(s.domain,s.metric,s.segment_key or "")))
    if tuple(advisory.signals) != ordered:
        return False
    try:
        rebuilt=CognitiveQualityDiagnosticAdvisory(
            workspace_id=advisory.workspace_id,reference_since=advisory.reference_since,
            reference_until=advisory.reference_until,candidate_since=advisory.candidate_since,
            candidate_until=advisory.candidate_until,reference_observed_count=advisory.reference_observed_count,
            candidate_observed_count=advisory.candidate_observed_count,status=advisory.status,
            primary_recommendation=advisory.primary_recommendation,signals=ordered,
            diagnostic_fingerprint=advisory.diagnostic_fingerprint,contract_version=advisory.contract_version,
            reference_baseline=advisory.reference_baseline,policy_version=advisory.policy_version,
            learning_authority=advisory.learning_authority,memory_write_authority=advisory.memory_write_authority,
            experience_trust_authority=advisory.experience_trust_authority,routing_authority=advisory.routing_authority,
            model_selection_authority=advisory.model_selection_authority,provider_selection_authority=advisory.provider_selection_authority,
            profile_selection_authority=advisory.profile_selection_authority,prompt_mutation_authority=advisory.prompt_mutation_authority,
            context_mutation_authority=advisory.context_mutation_authority,policy_mutation_authority=advisory.policy_mutation_authority,
            configuration_authority=advisory.configuration_authority,execution_authority=advisory.execution_authority,
            benchmark_promotion_authority=advisory.benchmark_promotion_authority,rollout_authority=advisory.rollout_authority,
            automatic_learning=advisory.automatic_learning,automatic_optimization=advisory.automatic_optimization,
        )
    except (TypeError,ValueError):
        return False
    return rebuilt == advisory


def _build_plan(
    *,workspace_id: WorkspaceId,reference_since: datetime,reference_until: datetime,
    candidate_since: datetime,candidate_until: datetime,source_diagnostic_fingerprint: str | None,
    source_diagnostic_status: str | None,source_primary_recommendation: str | None,
    status: str,primary_action: str,benchmark_review_recommended: bool,
    items: tuple[CognitiveQualityInvestigationItem,...]=(),
) -> CognitiveQualityInvestigationPlan:
    ordered=tuple(sorted(items,key=cognitive_quality_investigation_item_sort_key))
    fingerprint=compute_cognitive_quality_investigation_plan_fingerprint(
        workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
        candidate_since=candidate_since,candidate_until=candidate_until,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        source_diagnostic_status=source_diagnostic_status,  # type: ignore[arg-type]
        source_primary_recommendation=source_primary_recommendation,  # type: ignore[arg-type]
        status=status,primary_action=primary_action,  # type: ignore[arg-type]
        benchmark_review_recommended=benchmark_review_recommended,items=ordered,
    )
    return CognitiveQualityInvestigationPlan(
        workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
        candidate_since=candidate_since,candidate_until=candidate_until,
        source_diagnostic_fingerprint=source_diagnostic_fingerprint,
        source_diagnostic_status=source_diagnostic_status,  # type: ignore[arg-type]
        source_primary_recommendation=source_primary_recommendation,  # type: ignore[arg-type]
        status=status,primary_action=primary_action,  # type: ignore[arg-type]
        benchmark_review_recommended=benchmark_review_recommended,items=ordered,
        plan_fingerprint=fingerprint,
    )


class CognitiveQualityInvestigationPlanner:
    """Pure D158 planner; investigation planning has no intervention authority."""

    @classmethod
    def evaluate(
        cls,*,advisory: object | None,workspace_id: WorkspaceId,reference_since: datetime,
        reference_until: datetime,candidate_since: datetime,candidate_until: datetime,
    ) -> CognitiveQualityInvestigationPlan:
        if not isinstance(workspace_id,WorkspaceId):
            raise ValueError("cognitive_quality_investigation_workspace_invalid")
        if any(not isinstance(v,datetime) for v in (reference_since,reference_until,candidate_since,candidate_until)):
            raise ValueError("cognitive_quality_investigation_time_invalid")

        if not _source_valid(
            advisory,workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
            candidate_since=candidate_since,candidate_until=candidate_until,
        ):
            return _build_plan(
                workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
                candidate_since=candidate_since,candidate_until=candidate_until,
                source_diagnostic_fingerprint=None,source_diagnostic_status=None,source_primary_recommendation=None,
                status="invalid_evidence",primary_action="repair_evidence",benchmark_review_recommended=False,
            )

        assert isinstance(advisory,CognitiveQualityDiagnosticAdvisory)
        common=dict(
            workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
            candidate_since=candidate_since,candidate_until=candidate_until,
            source_diagnostic_fingerprint=advisory.diagnostic_fingerprint,
            source_diagnostic_status=advisory.status,
            source_primary_recommendation=advisory.primary_recommendation,
        )
        if advisory.status=="invalid_evidence":
            return _build_plan(**common,status="invalid_evidence",primary_action="repair_evidence",benchmark_review_recommended=False)
        if advisory.status=="insufficient_evidence":
            return _build_plan(**common,status="observation_required",primary_action="continue_observation",benchmark_review_recommended=False)
        if advisory.status=="no_material_signal":
            return _build_plan(**common,status="no_material_investigation",primary_action="continue_observation",benchmark_review_recommended=False)

        items=[]
        for source in advisory.signals:
            kind,evidence,scope=_PLAYBOOK[(source.domain,source.metric)]
            items.append(CognitiveQualityInvestigationItem(
                domain=source.domain,source_metric=source.metric,segment_key=source.segment_key,
                investigation_kind=kind,evidence_requirements=evidence,benchmark_scope_kind=scope,  # type: ignore[arg-type]
                benchmark_segment_key=source.segment_key if scope=="task_kind_segment" else None,
                source_reference_numerator=source.reference_numerator,
                source_reference_denominator=source.reference_denominator,
                source_candidate_numerator=source.candidate_numerator,
                source_candidate_denominator=source.candidate_denominator,
                source_delta_bps=source.delta_bps,
            ))
        benchmark=advisory.primary_recommendation=="benchmark_review_recommended"
        return _build_plan(
            **common,status="investigation_ready",
            primary_action="prepare_benchmark_review" if benchmark else "review_investigation_plan",
            benchmark_review_recommended=benchmark,items=tuple(items),
        )


class CognitiveQualityInvestigationPlanningService:
    """Read-only D158 composition over the D157 diagnostic service."""

    def __init__(self,diagnostic_service: CognitiveQualityDiagnosticService,*,workspace_id: WorkspaceId) -> None:
        if not isinstance(diagnostic_service,CognitiveQualityDiagnosticService):
            raise ValueError("cognitive_quality_investigation_diagnostic_service_invalid")
        if not isinstance(workspace_id,WorkspaceId):
            raise ValueError("cognitive_quality_investigation_workspace_invalid")
        self._diagnostic=diagnostic_service
        self._workspace_id=workspace_id

    def plan(
        self,*,reference_since: datetime,reference_until: datetime,candidate_since: datetime,candidate_until: datetime,
    ) -> CognitiveQualityInvestigationPlan:
        try:
            advisory=self._diagnostic.diagnose(
                reference_since=reference_since,reference_until=reference_until,
                candidate_since=candidate_since,candidate_until=candidate_until,
            )
        except ValueError:
            advisory=None
        return CognitiveQualityInvestigationPlanner.evaluate(
            advisory=advisory,workspace_id=self._workspace_id,
            reference_since=reference_since,reference_until=reference_until,
            candidate_since=candidate_since,candidate_until=candidate_until,
        )


__all__=["CognitiveQualityInvestigationPlanner","CognitiveQualityInvestigationPlanningService"]
