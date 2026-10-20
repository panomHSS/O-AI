from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from app.contracts.cognitive_quality_diagnostic_advisory import (
    CognitiveQualityDiagnosticAdvisory,
    CognitiveQualityDiagnosticSignal,
    compute_cognitive_quality_diagnostic_fingerprint,
)
from app.contracts.cognitive_quality_investigation_planning import (
    D158_CONTRACT_VERSION,
    D158_DOMAIN_PRIORITY,
    D158_POLICY_VERSION,
    D158_REFERENCE_BASELINE,
)
from app.contracts.workspace import WorkspaceId
from app.schemas.cognitive_quality_investigation import CognitiveQualityInvestigationPlanResponse
from app.services.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticService
from app.services.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationPlanner,
    CognitiveQualityInvestigationPlanningService,
)

NOW=datetime(2026,10,20,tzinfo=timezone.utc)
REF_END=NOW+timedelta(days=1)
CAND_END=REF_END+timedelta(days=1)

RECOMMENDATION={
    "evidence_integrity":"investigate_evidence_integrity",
    "evidence_sufficiency":"investigate_evidence_sufficiency",
    "cognition_validity":"investigate_cognition",
    "critic_revision":"investigate_critic",
    "task_concentration":"investigate_task_cohort",
    "experience_cohort_difference":"investigate_experience_cohort",
}

MAPPING={
    ("evidence_integrity","invalid_evidence_rate",None):(
        "evidence_integrity_review",
        ("d156_period_counts","d156_terminal_counts","d156_verification_counts"),
        "none",
    ),
    ("evidence_sufficiency","bounded_insufficiency_rate",None):(
        "bounded_insufficiency_review",
        ("d156_period_counts","d156_confidence_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("evidence_sufficiency","confidence_concern_rate",None):(
        "confidence_pattern_review",
        ("d156_confidence_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("cognition_validity","adverse_outcome_rate",None):(
        "adverse_outcome_review",
        ("d156_terminal_counts","d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("cognition_validity","verification_invalid_cognition_rate",None):(
        "invalid_cognition_review",
        ("d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("cognition_validity","terminal_failed_rate",None):(
        "terminal_failure_review",
        ("d156_terminal_counts","d156_verification_counts","d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "derive_from_candidate_task_breakdown",
    ),
    ("critic_revision","critic_exhausted_rate",None):(
        "critic_exhaustion_review",
        ("d156_revision_critic_counts","d156_verification_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("critic_revision","revised_turn_rate",None):(
        "revision_behavior_review",
        ("d156_revision_critic_counts","d156_terminal_counts","d156_task_kind_breakdown"),
        "none",
    ),
    ("task_concentration","adverse_outcome_rate_vs_overall","software_engineering"):(
        "task_kind_concentration_review",
        ("d156_task_kind_breakdown","d138_d139_targeted_benchmark_slice"),
        "task_kind_segment",
    ),
    ("experience_cohort_difference","adverse_outcome_rate_gap","absent|verification_active"):(
        "experience_cohort_difference_review",
        ("d156_experience_cohort_breakdown","future_matched_cohort_control"),
        "none",
    ),
}


def signal(domain,metric,segment_key=None):
    values=(3,30,3,10,2000) if metric=="adverse_outcome_rate_vs_overall" else ((0,15,3,15,2000) if metric=="adverse_outcome_rate_gap" else (0,30,3,30,1000))
    return CognitiveQualityDiagnosticSignal(
        domain=domain,metric=metric,segment_key=segment_key,
        reference_numerator=values[0],reference_denominator=values[1],
        candidate_numerator=values[2],candidate_denominator=values[3],delta_bps=values[4],
    )


def advisory(
    signals=(),*,status="investigation_recommended",recommendation=None,
    workspace_id=WorkspaceId.PERSONAL,reference_since=NOW,reference_until=REF_END,
    candidate_since=REF_END,candidate_until=CAND_END,
):
    ordered=tuple(sorted(signals,key=lambda item:(item.domain,item.metric,item.segment_key or "")))
    if recommendation is None:
        if status!="investigation_recommended":
            recommendation="continue_observation"
        else:
            domains={item.domain for item in ordered}
            recommendation="benchmark_review_recommended" if len(domains)>=2 else RECOMMENDATION[next(iter(domains))]
    counts=(30,30) if status!="invalid_evidence" else (None,None)
    fp=compute_cognitive_quality_diagnostic_fingerprint(
        workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
        candidate_since=candidate_since,candidate_until=candidate_until,
        reference_observed_count=counts[0],candidate_observed_count=counts[1],
        status=status,primary_recommendation=recommendation,signals=ordered,
    )
    return CognitiveQualityDiagnosticAdvisory(
        workspace_id=workspace_id,reference_since=reference_since,reference_until=reference_until,
        candidate_since=candidate_since,candidate_until=candidate_until,
        reference_observed_count=counts[0],candidate_observed_count=counts[1],
        status=status,primary_recommendation=recommendation,signals=ordered,diagnostic_fingerprint=fp,
    )


def plan(source,*,workspace_id=WorkspaceId.PERSONAL,rs=NOW,ru=REF_END,cs=REF_END,cu=CAND_END):
    return CognitiveQualityInvestigationPlanner.evaluate(
        advisory=source,workspace_id=workspace_id,reference_since=rs,reference_until=ru,
        candidate_since=cs,candidate_until=cu,
    )


def test_d158_a_b_c_contract_identity_authority_and_immutability():
    assert D158_REFERENCE_BASELINE=="b85572a4f1a5a179db9c98029f013ce8cf8a1d87"
    assert D158_CONTRACT_VERSION=="1"
    assert D158_POLICY_VERSION=="o-ai.d158.cognitive-quality-investigation-plan.v1"
    assert D158_DOMAIN_PRIORITY==(
        "evidence_integrity","cognition_validity","critic_revision",
        "evidence_sufficiency","task_concentration","experience_cohort_difference",
    )
    result=plan(advisory(status="no_material_signal"))
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert getattr(result,name) is False
    try:
        result.status="investigation_ready"  # type: ignore[misc]
        raise AssertionError("frozen plan mutated")
    except FrozenInstanceError:
        pass


def test_d158_d_e_wrong_type_and_workspace_fail_closed():
    bad=plan(object())
    assert (bad.status,bad.primary_action,bad.items)==("invalid_evidence","repair_evidence",())
    wrong=plan(advisory(status="no_material_signal"),workspace_id=WorkspaceId.COMPANY)
    assert wrong.status=="invalid_evidence"


def test_d158_f_semantic_time_matching_accepts_same_instants():
    plus7=timezone(timedelta(hours=7))
    source=advisory((signal("cognition_validity","terminal_failed_rate"),))
    result=plan(source,rs=NOW.astimezone(plus7),ru=REF_END.astimezone(plus7),cs=REF_END.astimezone(plus7),cu=CAND_END.astimezone(plus7))
    assert result.status=="investigation_ready"


def test_d158_g_h_bad_source_fingerprint_and_authority_fail_closed():
    source=advisory((signal("cognition_validity","terminal_failed_rate"),))
    object.__setattr__(source,"diagnostic_fingerprint","0"*64)
    assert plan(source).status=="invalid_evidence"
    source2=advisory((signal("cognition_validity","terminal_failed_rate"),))
    object.__setattr__(source2,"execution_authority",True)
    assert plan(source2).status=="invalid_evidence"


def test_d158_i_s_t_u_all_exact_playbook_mappings():
    for (domain,metric,segment),expected in MAPPING.items():
        result=plan(advisory((signal(domain,metric,segment),)))
        assert result.status=="investigation_ready" and len(result.items)==1
        item=result.items[0]
        assert item.investigation_kind==expected[0]
        assert item.evidence_requirements==expected[1]
        assert item.benchmark_scope_kind==expected[2]
        assert item.benchmark_segment_key==(segment if expected[2]=="task_kind_segment" else None)
        assert item.source_metric==metric


def test_d158_j_wrong_domain_metric_combination_is_rejected():
    source=advisory((signal("cognition_validity","critic_exhausted_rate"),),recommendation="investigate_cognition")
    assert plan(source).status=="invalid_evidence"


def test_d158_k_duplicate_signal_identity_is_rejected():
    item=signal("cognition_validity","terminal_failed_rate")
    source=advisory((item,item),recommendation="investigate_cognition")
    assert plan(source).status=="invalid_evidence"


def test_d158_l_m_n_segment_semantics_fail_closed():
    bad_long=advisory((signal("cognition_validity","terminal_failed_rate","unexpected"),),recommendation="investigate_cognition")
    assert plan(bad_long).status=="invalid_evidence"
    bad_task=advisory((signal("task_concentration","adverse_outcome_rate_vs_overall"),),recommendation="investigate_task_cohort")
    assert plan(bad_task).status=="invalid_evidence"
    bad_pair=advisory((signal("experience_cohort_difference","adverse_outcome_rate_gap","verification_active|absent"),),recommendation="investigate_experience_cohort")
    assert plan(bad_pair).status=="invalid_evidence"


def test_d158_o_p_q_source_status_projection():
    invalid=plan(advisory(status="invalid_evidence"))
    insufficient=plan(advisory(status="insufficient_evidence"))
    quiet=plan(advisory(status="no_material_signal"))
    assert (invalid.status,invalid.primary_action,invalid.items)==("invalid_evidence","repair_evidence",())
    assert (insufficient.status,insufficient.primary_action,insufficient.items)==("observation_required","continue_observation",())
    assert (quiet.status,quiet.primary_action,quiet.items)==("no_material_investigation","continue_observation",())


def test_d158_r_one_signal_creates_exactly_one_item_and_copies_evidence():
    result=plan(advisory((signal("cognition_validity","terminal_failed_rate"),)))
    item=result.items[0]
    assert len(result.items)==1
    assert (item.source_reference_numerator,item.source_reference_denominator,item.source_candidate_numerator,item.source_candidate_denominator,item.source_delta_bps)==(0,30,3,30,1000)


def test_d158_v_benchmark_flag_mirrors_d157_only():
    same=advisory((
        signal("cognition_validity","adverse_outcome_rate"),
        signal("cognition_validity","terminal_failed_rate"),
    ),recommendation="investigate_cognition")
    same_result=plan(same)
    assert same_result.benchmark_review_recommended is False
    assert same_result.primary_action=="review_investigation_plan"

    multi=advisory((
        signal("evidence_integrity","invalid_evidence_rate"),
        signal("cognition_validity","terminal_failed_rate"),
    ),recommendation="benchmark_review_recommended")
    multi_result=plan(multi)
    assert multi_result.benchmark_review_recommended is True
    assert multi_result.primary_action=="prepare_benchmark_review"


def test_d158_w_domain_priority_not_source_lexical_order():
    source=advisory((
        signal("evidence_integrity","invalid_evidence_rate"),
        signal("cognition_validity","terminal_failed_rate"),
    ),recommendation="benchmark_review_recommended")
    assert [item.domain for item in source.signals]==["cognition_validity","evidence_integrity"]
    assert [item.domain for item in plan(source).items]==["evidence_integrity","cognition_validity"]


def test_d158_y_schema_projection_and_service_composition():
    source=advisory((signal("cognition_validity","terminal_failed_rate"),))
    class FakeDiagnostic(CognitiveQualityDiagnosticService):
        def __init__(self,value): self.value,self.calls=value,0
        def diagnose(self,**kwargs): self.calls+=1; return self.value
    fake=FakeDiagnostic(source)
    service=CognitiveQualityInvestigationPlanningService(fake,workspace_id=WorkspaceId.PERSONAL)
    result=service.plan(reference_since=NOW,reference_until=REF_END,candidate_since=REF_END,candidate_until=CAND_END)
    model=CognitiveQualityInvestigationPlanResponse.from_contract(result)
    assert fake.calls==1 and model.workspace_id=="personal"
    assert model.items[0].investigation_kind=="terminal_failure_review"
    assert model.execution_authority is False
