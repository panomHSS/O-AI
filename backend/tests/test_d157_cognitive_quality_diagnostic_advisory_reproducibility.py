from datetime import timedelta, timezone

from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_diagnostic_advisory import CognitiveQualityDiagnosticEvaluator
from tests.test_d157_cognitive_quality_diagnostic_advisory import CAND_END, NOW, REF_END, comparison, period_records


def run(cmp, *, rs=NOW, ru=REF_END, cs=REF_END, cu=CAND_END):
    return CognitiveQualityDiagnosticEvaluator.evaluate(comparison=cmp,workspace_id=WorkspaceId.PERSONAL,reference_since=rs,reference_until=ru,candidate_since=cs,candidate_until=cu)


def test_d157_u_same_evidence_same_fingerprint():
    cmp=comparison(period_records(NOW),period_records(REF_END,adverse=3))
    assert run(cmp).diagnostic_fingerprint==run(cmp).diagnostic_fingerprint


def test_d157_u_utc_offset_normalization_same_fingerprint():
    cmp=comparison(period_records(NOW),period_records(REF_END,adverse=3)); plus7=timezone(timedelta(hours=7))
    a=run(cmp); b=run(cmp,rs=NOW.astimezone(plus7),ru=REF_END.astimezone(plus7),cs=REF_END.astimezone(plus7),cu=CAND_END.astimezone(plus7))
    assert a.diagnostic_fingerprint==b.diagnostic_fingerprint


def test_d157_u_signal_order_is_deterministic():
    result=run(comparison(period_records(NOW),period_records(REF_END,adverse=3,critic=3)))
    keys=[(s.domain,s.metric,s.segment_key or "") for s in result.signals]
    assert keys==sorted(keys)


def test_d157_p_cohort_pair_is_canonical():
    result=run(comparison(period_records(NOW,adverse=3),period_records(REF_END,adverse=3,cohort_map=((15,"verification_active"),(30,"absent")))))
    signal=next(s for s in result.signals if s.domain=="experience_cohort_difference")
    assert signal.segment_key=="absent|verification_active"


def test_d157_f_integer_bps_floor_is_reproducible():
    signal=next(s for s in run(comparison(period_records(NOW),period_records(REF_END,adverse=4))).signals if s.metric=="adverse_outcome_rate")
    assert signal.delta_bps==1333 and isinstance(signal.delta_bps,int)
