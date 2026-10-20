from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.contracts.cognitive_quality_diagnostic_advisory import (
    D157_MATERIAL_RATE_INCREASE_BPS,
    D157_MATERIAL_SUBGROUP_GAP_BPS,
    D157_MIN_PERIOD_OBSERVATIONS,
    D157_MIN_SUBGROUP_OBSERVATIONS,
    D157_MIN_SUPPORTING_EVENT_INCREASE,
    D157_RATE_SCALE_BPS,
)
from app.contracts.workspace import WorkspaceId
from app.schemas.cognitive_quality_diagnostic import CognitiveQualityDiagnosticResponse
from app.services.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticEvaluator, CognitiveQualityDiagnosticService
from app.services.cognitive_quality_summary import CognitiveQualitySummaryService

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
REF_END = NOW + timedelta(days=1)
CAND_END = REF_END + timedelta(days=1)


class Repo:
    def __init__(self, records): self.records = list(records)
    def list_for_summary(self, *, workspace_id, since=None, until=None):
        result = [r for r in self.records if r.workspace_id == workspace_id.value]
        if since is not None: result = [r for r in result if r.occurred_at >= since]
        if until is not None: result = [r for r in result if r.occurred_at < until]
        return result


def rec(t, *, classification="verified_success", verification_result="pass", revision_count=0, critic_exhausted=False, confidence_class="sufficient", cohort="absent", task="general_chat"):
    terminal = {"verified_success":"completed", "bounded_insufficiency":"insufficient", "adverse_outcome":"failed", "invalid_evidence":"completed"}[classification]
    return SimpleNamespace(workspace_id="personal", occurred_at=t, quality_classification=classification, terminal_state=terminal, verification_result=verification_result, revision_count=revision_count, critic_exhausted=critic_exhausted, confidence_class=confidence_class, experience_cohort=cohort, task_kind=task)


def period_records(start, *, n=30, adverse=0, invalid=0, bounded=0, invalid_cognition=0, critic=0, revised=0, confidence_concern=0, task_map=None, cohort_map=None):
    result=[]
    for i in range(n):
        classification="verified_success"
        if i < adverse: classification="adverse_outcome"
        elif i < adverse+invalid: classification="invalid_evidence"
        elif i < adverse+invalid+bounded: classification="bounded_insufficiency"
        verification="invalid_cognition" if i < invalid_cognition else ("pass" if classification=="verified_success" else None)
        confidence="limited" if i < confidence_concern else "sufficient"
        task="general_chat"; cohort="absent"
        if task_map:
            for upper,name in task_map:
                if i < upper: task=name; break
        if cohort_map:
            for upper,name in cohort_map:
                if i < upper: cohort=name; break
        result.append(rec(start+timedelta(minutes=i), classification=classification, verification_result=verification, revision_count=1 if i<revised else 0, critic_exhausted=i<critic, confidence_class=confidence, task=task, cohort=cohort))
    return result


def comparison(ref_records, cand_records):
    service=CognitiveQualitySummaryService(Repo([*ref_records,*cand_records]), workspace_id=WorkspaceId.PERSONAL)
    return service.compare(reference_since=NOW, reference_until=REF_END, candidate_since=REF_END, candidate_until=CAND_END)


def evaluate(ref_records, cand_records):
    return CognitiveQualityDiagnosticEvaluator.evaluate(comparison=comparison(ref_records,cand_records), workspace_id=WorkspaceId.PERSONAL, reference_since=NOW, reference_until=REF_END, candidate_since=REF_END, candidate_until=CAND_END)


def test_d157_a_contract_policy_constants():
    assert (D157_RATE_SCALE_BPS,D157_MIN_PERIOD_OBSERVATIONS,D157_MIN_SUBGROUP_OBSERVATIONS,D157_MATERIAL_RATE_INCREASE_BPS,D157_MATERIAL_SUBGROUP_GAP_BPS,D157_MIN_SUPPORTING_EVENT_INCREASE)==(10000,30,10,1000,1500,3)


def test_d157_b_authority_and_immutability():
    result=evaluate(period_records(NOW),period_records(REF_END))
    for name in ("learning_authority","memory_write_authority","experience_trust_authority","routing_authority","model_selection_authority","provider_selection_authority","profile_selection_authority","prompt_mutation_authority","context_mutation_authority","policy_mutation_authority","configuration_authority","execution_authority","benchmark_promotion_authority","rollout_authority","automatic_learning","automatic_optimization"):
        assert getattr(result,name) is False
    with pytest.raises(FrozenInstanceError): result.status="invalid_evidence"  # type: ignore[misc]


def test_d157_c_period_overlap_is_invalid_without_diagnosis():
    cmp=comparison(period_records(NOW),period_records(REF_END))
    result=CognitiveQualityDiagnosticEvaluator.evaluate(comparison=cmp, workspace_id=WorkspaceId.PERSONAL, reference_since=NOW, reference_until=REF_END, candidate_since=REF_END-timedelta(seconds=1), candidate_until=CAND_END)
    assert result.status=="invalid_evidence" and result.signals==()


def test_d157_d_workspace_mismatch_is_invalid():
    cmp=comparison(period_records(NOW),period_records(REF_END))
    result=CognitiveQualityDiagnosticEvaluator.evaluate(comparison=cmp, workspace_id=WorkspaceId.COMPANY, reference_since=NOW, reference_until=REF_END, candidate_since=REF_END, candidate_until=CAND_END)
    assert result.status=="invalid_evidence"


def test_d157_e_sample_gate_29_and_30():
    assert evaluate(period_records(NOW,n=29),period_records(REF_END,n=29)).status=="insufficient_evidence"
    assert evaluate(period_records(NOW),period_records(REF_END)).status=="no_material_signal"


def test_d157_g_material_boundary_requires_rate_and_events():
    yes=evaluate(period_records(NOW),period_records(REF_END,adverse=3))
    no_events=evaluate(period_records(NOW,n=60),period_records(REF_END,n=60,adverse=2))
    assert any(s.metric=="adverse_outcome_rate" and s.delta_bps==1000 for s in yes.signals)
    terminal=next(s for s in yes.signals if s.metric=="terminal_failed_rate")
    assert (terminal.reference_numerator,terminal.reference_denominator,terminal.candidate_numerator,terminal.candidate_denominator,terminal.delta_bps)==(0,30,3,30,1000)
    assert all(s.metric!="adverse_outcome_rate" for s in no_events.signals)
    assert all(s.metric!="terminal_failed_rate" for s in no_events.signals)


def test_d157_h_i_quality_evidence_signals():
    assert any(s.metric=="invalid_evidence_rate" for s in evaluate(period_records(NOW),period_records(REF_END,invalid=3)).signals)
    assert any(s.metric=="bounded_insufficiency_rate" for s in evaluate(period_records(NOW),period_records(REF_END,bounded=3)).signals)


def test_d157_j_confidence_concern():
    result=evaluate(period_records(NOW),period_records(REF_END,confidence_concern=3))
    signal=next(s for s in result.signals if s.metric=="confidence_concern_rate")
    assert (signal.reference_denominator,signal.candidate_denominator)==(30,30)


def test_d157_k_l_cognition_signals():
    result=evaluate(period_records(NOW),period_records(REF_END,adverse=3,invalid_cognition=3))
    metrics={s.metric for s in result.signals}
    assert {"adverse_outcome_rate","verification_invalid_cognition_rate","terminal_failed_rate"} <= metrics
    assert result.primary_recommendation=="investigate_cognition"


def test_d157_m_n_critic_revision_signals():
    result=evaluate(period_records(NOW),period_records(REF_END,critic=3,revised=3))
    assert {"critic_exhausted_rate","revised_turn_rate"} <= {s.metric for s in result.signals}
    assert result.primary_recommendation=="investigate_critic"


def test_d157_o_task_concentration_candidate_only():
    ref=period_records(NOW,adverse=3,task_map=((10,"general_chat"),(30,"software_engineering")))
    cand=period_records(REF_END,adverse=3,task_map=((10,"general_chat"),(30,"software_engineering")))
    for i in range(3): ref[i].task_kind="software_engineering"
    signal=next(s for s in evaluate(ref,cand).signals if s.domain=="task_concentration")
    assert signal.segment_key=="general_chat" and signal.delta_bps==2000


def test_d157_p_experience_cohort_gap_is_observational():
    result=evaluate(period_records(NOW,adverse=3),period_records(REF_END,adverse=3,cohort_map=((15,"absent"),(30,"verification_active"))))
    signal=next(s for s in result.signals if s.domain=="experience_cohort_difference")
    assert signal.segment_key=="absent|verification_active" and abs(signal.delta_bps)>=1500
    assert result.primary_recommendation=="investigate_experience_cohort"


def test_d157_q_two_unique_domains_escalate_benchmark_review():
    result=evaluate(period_records(NOW),period_records(REF_END,adverse=3,critic=3))
    assert {s.domain for s in result.signals} >= {"cognition_validity","critic_revision"}
    assert result.primary_recommendation=="benchmark_review_recommended"


def test_d157_s_t_corrupt_d156_delta_is_invalid_evidence():
    cmp=comparison(period_records(NOW),period_records(REF_END))
    broken=replace(cmp,count_deltas=cmp.count_deltas[:-1])
    result=CognitiveQualityDiagnosticEvaluator.evaluate(comparison=broken, workspace_id=WorkspaceId.PERSONAL, reference_since=NOW, reference_until=REF_END, candidate_since=REF_END, candidate_until=CAND_END)
    assert result.status=="invalid_evidence" and result.reference_observed_count is None


def test_d157_v_schema_projection():
    model=CognitiveQualityDiagnosticResponse.from_contract(evaluate(period_records(NOW),period_records(REF_END,adverse=3)))
    assert model.workspace_id=="personal" and model.status=="investigation_recommended" and model.execution_authority is False


def test_d157_service_rejects_invalid_period_before_summary_compare():
    class NoCallSummary(CognitiveQualitySummaryService):
        def __init__(self): pass
        def compare(self, **kwargs): raise AssertionError("compare must not be called")
    service=CognitiveQualityDiagnosticService(NoCallSummary(), workspace_id=WorkspaceId.PERSONAL)
    result=service.diagnose(reference_since=NOW,reference_until=REF_END,candidate_since=NOW,candidate_until=CAND_END)
    assert result.status=="invalid_evidence"
