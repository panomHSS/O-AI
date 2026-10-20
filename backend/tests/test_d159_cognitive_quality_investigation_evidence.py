from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.contracts.cognitive_quality_investigation_planning import (
    CognitiveQualityInvestigationItem,
    CognitiveQualityInvestigationPlan,
    compute_cognitive_quality_investigation_plan_fingerprint,
)
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_investigation_evidence import CognitiveQualityInvestigationEvidenceService
from app.services.cognitive_quality_investigation_planning import CognitiveQualityInvestigationPlanningService
from app.services.cognitive_quality_summary import (
    CognitiveQualityBreakdown,
    CognitiveQualityComparison,
    CognitiveQualityCounts,
    CognitiveQualityMetricDelta,
    CognitiveQualityRateDelta,
    CognitiveQualitySummary,
    CognitiveQualitySummaryService,
    rate_text,
)

RS = datetime(2026, 10, 1, tzinfo=timezone.utc)
RU = datetime(2026, 10, 8, tzinfo=timezone.utc)
CS = datetime(2026, 10, 8, tzinfo=timezone.utc)
CU = datetime(2026, 10, 15, tzinfo=timezone.utc)
DIAG = "a" * 64


class FakePlanning(CognitiveQualityInvestigationPlanningService):
    def __init__(self, value):
        self.value, self.calls = value, 0
    def plan(self, **kwargs):
        self.calls += 1
        return self.value


class FakeSummary(CognitiveQualitySummaryService):
    def __init__(self, value):
        self.value, self.calls = value, 0
    def compare(self, **kwargs):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def counts(*, observed=30, verified=27, bounded=0, adverse=3, invalid=0, failed=3, verification_invalid=3, revised=0, critic=0, conf_sufficient=27, conf_limited=3, conf_insufficient=0, conf_unknown=0):
    return CognitiveQualityCounts(
        observed_count=observed, verified_success_count=verified,
        bounded_insufficiency_count=bounded, adverse_outcome_count=adverse,
        invalid_evidence_count=invalid, terminal_completed_count=observed-failed,
        terminal_insufficient_count=0, terminal_failed_count=failed,
        verification_pass_count=observed-verification_invalid,
        verification_revise_count=0, verification_insufficient_evidence_count=0,
        verification_invalid_cognition_count=verification_invalid,
        revised_turn_count=revised, critic_exhausted_count=critic,
        confidence_sufficient_count=conf_sufficient, confidence_limited_count=conf_limited,
        confidence_insufficient_count=conf_insufficient, confidence_unknown_count=conf_unknown,
    )


def _summary(period_start, period_end, c, *, task_key="software_engineering", cohort_key="absent"):
    return CognitiveQualitySummary(
        WorkspaceId.PERSONAL, period_start, period_end, c,
        (CognitiveQualityBreakdown(cohort_key, c),),
        (CognitiveQualityBreakdown(task_key, c),),
    )


def comparison(ref=None, cand=None, *, ref_task="software_engineering", cand_task="software_engineering", ref_cohort="absent", cand_cohort="absent"):
    ref = ref or counts()
    cand = cand or counts(verified=24, adverse=6, failed=6, verification_invalid=6, conf_sufficient=24, conf_limited=6)
    rs, cs = _summary(RS, RU, ref, task_key=ref_task, cohort_key=ref_cohort), _summary(CS, CU, cand, task_key=cand_task, cohort_key=cand_cohort)
    count_names = (
        "observed_count","verified_success_count","bounded_insufficiency_count",
        "adverse_outcome_count","invalid_evidence_count","revised_turn_count","critic_exhausted_count",
    )
    count_deltas = tuple(CognitiveQualityMetricDelta(n, getattr(ref,n), getattr(cand,n), getattr(cand,n)-getattr(ref,n)) for n in count_names)
    rates = []
    for metric, name in (
        ("verified_success_rate","verified_success_count"),
        ("bounded_insufficiency_rate","bounded_insufficiency_count"),
        ("adverse_outcome_rate","adverse_outcome_count"),
        ("invalid_evidence_rate","invalid_evidence_count"),
    ):
        rn, cn, rd, cd = getattr(ref,name), getattr(cand,name), ref.observed_count, cand.observed_count
        rr, cr = rate_text(rn,rd), rate_text(cn,cd)
        dr = None if rr is None or cr is None else format(Decimal(cr)-Decimal(rr), ".6f")
        rates.append(CognitiveQualityRateDelta(metric,rn,cn,rd,cd,rr,cr,dr))
    return CognitiveQualityComparison(rs, cs, count_deltas, tuple(rates))


def item(*, domain="cognition_validity", metric="terminal_failed_rate", requirements=("d156_terminal_counts",), kind="terminal_failure_review", segment=None, benchmark_scope="derive_from_candidate_task_breakdown", benchmark_segment=None, rn=3, rd=30, cn=6, cd=30, delta=1000):
    return CognitiveQualityInvestigationItem(
        domain=domain, source_metric=metric, segment_key=segment, investigation_kind=kind,
        evidence_requirements=requirements, benchmark_scope_kind=benchmark_scope,
        benchmark_segment_key=benchmark_segment, source_reference_numerator=rn,
        source_reference_denominator=rd, source_candidate_numerator=cn,
        source_candidate_denominator=cd, source_delta_bps=delta,
    )


def plan(*, status="investigation_ready", primary_action="review_investigation_plan", items=None, benchmark=False, source_diag=DIAG, source_status="investigation_recommended", source_recommendation="investigate_cognition"):
    values = tuple(items if items is not None else (item(),))
    fp = compute_cognitive_quality_investigation_plan_fingerprint(
        workspace_id=WorkspaceId.PERSONAL, reference_since=RS, reference_until=RU,
        candidate_since=CS, candidate_until=CU, source_diagnostic_fingerprint=source_diag,
        source_diagnostic_status=source_status, source_primary_recommendation=source_recommendation,
        status=status, primary_action=primary_action, benchmark_review_recommended=benchmark, items=values,
    )
    return CognitiveQualityInvestigationPlan(
        workspace_id=WorkspaceId.PERSONAL, reference_since=RS, reference_until=RU,
        candidate_since=CS, candidate_until=CU, source_diagnostic_fingerprint=source_diag,
        source_diagnostic_status=source_status, source_primary_recommendation=source_recommendation,
        status=status, primary_action=primary_action, benchmark_review_recommended=benchmark,
        items=values, plan_fingerprint=fp,
    )


def service(p, c=None):
    return CognitiveQualityInvestigationEvidenceService(
        FakePlanning(p), FakeSummary(c if c is not None else comparison()),
        workspace_id=WorkspaceId.PERSONAL,
    )


def assemble(svc):
    return svc.assemble(reference_since=RS, reference_until=RU, candidate_since=CS, candidate_until=CU)


def test_d159_a_b_c_d_e_contract_status_availability_and_authority():
    packet = assemble(service(plan()))
    assert packet.contract_version == "1"
    assert packet.reference_baseline == "4b402d08ed99f1a229ef030d10d129ba56dc854d"
    assert packet.policy_version == "o-ai.d159.cognitive-quality-investigation-evidence.v1"
    assert (packet.status, packet.primary_action) == ("evidence_complete","review_assembled_evidence")
    assert (packet.entries[0].availability, packet.entries[0].availability_reason) == ("available","assembled")
    for name in (
        "learning_authority","memory_write_authority","experience_trust_authority","routing_authority",
        "model_selection_authority","provider_selection_authority","profile_selection_authority",
        "prompt_mutation_authority","context_mutation_authority","policy_mutation_authority",
        "configuration_authority","execution_authority","benchmark_promotion_authority",
        "rollout_authority","automatic_learning","automatic_optimization",
    ):
        assert getattr(packet,name) is False


def test_d159_f_g_h_i_j_fail_closed_source_validation():
    p = plan()
    bad_fp = object.__new__(CognitiveQualityInvestigationPlan)
    for f in p.__dataclass_fields__: object.__setattr__(bad_fp, f, getattr(p,f))
    object.__setattr__(bad_fp, "plan_fingerprint", "0"*64)
    bad_auth = object.__new__(CognitiveQualityInvestigationPlan)
    for f in p.__dataclass_fields__: object.__setattr__(bad_auth, f, getattr(p,f))
    object.__setattr__(bad_auth, "execution_authority", True)
    for source in (object(), bad_fp, bad_auth):
        packet = assemble(service(source))
        assert (packet.status, packet.primary_action, packet.entries) == ("invalid_evidence","repair_source_evidence",())
        assert packet.source_plan_fingerprint is None

    wrong_workspace = CognitiveQualityInvestigationEvidenceService(FakePlanning(p), FakeSummary(comparison()), workspace_id=WorkspaceId.COMPANY)
    assert assemble(wrong_workspace).status == "invalid_evidence"

    shifted = service(p)
    packet = shifted.assemble(reference_since=RS+timedelta(seconds=1), reference_until=RU, candidate_since=CS, candidate_until=CU)
    assert packet.status == "invalid_evidence"


def test_d159_k_valid_d158_invalid_preserves_plan_identity():
    p = plan(status="invalid_evidence", primary_action="repair_evidence", items=(), benchmark=False, source_diag=None, source_status=None, source_recommendation=None)
    packet = assemble(service(p))
    assert (packet.status, packet.primary_action, packet.entries) == ("invalid_evidence","repair_source_evidence",())
    assert packet.source_plan_fingerprint == p.plan_fingerprint


def test_d159_l_m_no_assembly_statuses_skip_d156_compare():
    for status, diag in (("observation_required","insufficient_evidence"),("no_material_investigation","no_material_signal")):
        p = plan(status=status, primary_action="continue_observation", items=(), source_status=diag, source_recommendation="continue_observation")
        summary = FakeSummary(comparison())
        svc = CognitiveQualityInvestigationEvidenceService(FakePlanning(p), summary, workspace_id=WorkspaceId.PERSONAL)
        packet = assemble(svc)
        assert (packet.status, packet.primary_action, packet.entries) == ("no_assembly_required","continue_observation",())
        assert summary.calls == 0


def test_d159_n_investigation_ready_calls_compare_once():
    summary = FakeSummary(comparison())
    svc = CognitiveQualityInvestigationEvidenceService(FakePlanning(plan()), summary, workspace_id=WorkspaceId.PERSONAL)
    assemble(svc)
    assert summary.calls == 1


def test_d159_o_first_five_exact_projections():
    requirements=("d156_period_counts","d156_terminal_counts","d156_verification_counts","d156_confidence_counts","d156_revision_critic_counts")
    packet = assemble(service(plan(items=(item(requirements=requirements),))))
    assert packet.status == "evidence_complete"
    assert tuple(e.evidence_requirement for e in packet.entries) == requirements
    assert [len(e.values) for e in packet.entries] == [5,3,4,4,2]


def test_d159_p_q_breakdown_union_zero_absent_side():
    ref = counts(observed=30, verified=30, adverse=0, failed=0, verification_invalid=0, conf_sufficient=30, conf_limited=0)
    cand = counts(verified=24, adverse=6, failed=6, verification_invalid=6, conf_sufficient=24, conf_limited=6)
    comp = comparison(ref,cand,ref_task="analysis",cand_task="software_engineering",ref_cohort="absent",cand_cohort="verification_active")
    i = item(requirements=("d156_task_kind_breakdown","d156_experience_cohort_breakdown"), rn=0, rd=30, cn=6, cd=30)
    packet = assemble(service(plan(items=(i,)), comp))
    assert packet.status == "evidence_complete"
    task, cohort = packet.entries
    assert {v.segment_key for v in task.values} == {"analysis","software_engineering"}
    assert {v.segment_key for v in cohort.values} == {"absent","verification_active"}
    a = next(v for v in task.values if v.segment_key=="analysis" and v.metric=="observed_count")
    b = next(v for v in task.values if v.segment_key=="software_engineering" and v.metric=="observed_count")
    assert (a.reference_count,a.candidate_count)==(30,0)
    assert (b.reference_count,b.candidate_count)==(0,30)


def test_d159_r_s_one_requirement_one_entry_and_order():
    first=item(
        domain="critic_revision",
        metric="critic_exhausted_rate",
        kind="critic_exhaustion_review",
        requirements=("d156_revision_critic_counts","d156_verification_counts","d156_task_kind_breakdown"),
        rn=0,rd=30,cn=0,cd=30,delta=0,
    )
    second=item(
        domain="critic_revision",
        metric="revised_turn_rate",
        kind="revision_behavior_review",
        requirements=("d156_revision_critic_counts","d156_terminal_counts","d156_task_kind_breakdown"),
        rn=0,rd=30,cn=0,cd=30,delta=0,
    )
    packet=assemble(service(plan(items=(first,second),source_recommendation="investigate_critic")))
    assert len(packet.entries)==6
    assert tuple(e.evidence_requirement for e in packet.entries[:3])==first.evidence_requirements
    assert tuple(e.evidence_requirement for e in packet.entries[3:])==second.evidence_requirements


def test_d159_t_u_derive_benchmark_descriptor_only():
    packet=assemble(service(plan(items=(item(requirements=("d138_d139_targeted_benchmark_slice",)),))))
    entry=packet.entries[0]
    assert (packet.status,entry.availability,entry.availability_reason)==("evidence_incomplete","descriptor_only","benchmark_descriptor_only")
    assert entry.benchmark_scope_kind=="derive_from_candidate_task_breakdown"
    assert entry.benchmark_candidate_task_keys==("software_engineering",)
    assert entry.values==()


def test_d159_v_task_segment_descriptor_preserves_segment():
    i=item(domain="task_concentration",metric="adverse_outcome_rate_vs_overall",kind="task_kind_concentration_review",requirements=("d138_d139_targeted_benchmark_slice",),segment="software_engineering",benchmark_scope="task_kind_segment",benchmark_segment="software_engineering",rn=6,rd=30,cn=6,cd=30,delta=0)
    packet=assemble(service(plan(items=(i,),source_recommendation="investigate_task_cohort")))
    entry=packet.entries[0]
    assert entry.availability=="descriptor_only"
    assert entry.benchmark_segment_key=="software_engineering"
    assert entry.benchmark_candidate_task_keys==()


def test_d159_w_future_matched_cohort_is_future_required():
    i=item(domain="experience_cohort_difference",metric="adverse_outcome_rate_gap",kind="experience_cohort_difference_review",requirements=("future_matched_cohort_control",),segment="absent|verification_active",benchmark_scope="none",benchmark_segment=None,rn=0,rd=15,cn=3,cd=15,delta=2000)
    packet=assemble(service(plan(items=(i,),source_recommendation="investigate_experience_cohort")))
    entry=packet.entries[0]
    assert (entry.availability,entry.availability_reason)==("future_required","future_governed_collection_required")
    assert entry.values==() and packet.status=="evidence_incomplete"


def test_d159_x_comparison_unavailable():
    packet=assemble(service(plan(),ValueError("no comparison")))
    assert packet.status=="evidence_incomplete"
    assert (packet.entries[0].availability,packet.entries[0].availability_reason)==("unavailable","comparison_unavailable")


def test_d159_y_lineage_mismatch_no_rediagnosis():
    p=plan()
    drift=comparison(cand=counts(verified=23,adverse=7,failed=7,verification_invalid=7,conf_sufficient=23,conf_limited=7))
    packet=assemble(service(p,drift))
    assert packet.source_plan_fingerprint==p.plan_fingerprint
    assert packet.status=="evidence_incomplete"
    assert packet.entries[0].availability_reason=="source_lineage_mismatch"


def test_d159_benchmark_flag_mirrors_d158_only():
    p=plan(benchmark=True,primary_action="prepare_benchmark_review",source_recommendation="benchmark_review_recommended")
    assert assemble(service(p)).benchmark_review_recommended is True
    assert assemble(service(plan())).benchmark_review_recommended is False
