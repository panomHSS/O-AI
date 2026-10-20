from datetime import timedelta, timezone

from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_investigation_planning import CognitiveQualityInvestigationPlanner
from tests.test_d158_cognitive_quality_investigation_planning import (
    CAND_END, NOW, REF_END, advisory, signal,
)


def run(source,*,rs=NOW,ru=REF_END,cs=REF_END,cu=CAND_END):
    return CognitiveQualityInvestigationPlanner.evaluate(
        advisory=source,workspace_id=WorkspaceId.PERSONAL,
        reference_since=rs,reference_until=ru,candidate_since=cs,candidate_until=cu,
    )


def test_d158_x_same_source_same_plan_fingerprint():
    source=advisory((signal("cognition_validity","terminal_failed_rate"),))
    assert run(source).plan_fingerprint==run(source).plan_fingerprint


def test_d158_x_utc_offset_normalization_same_fingerprint():
    source=advisory((signal("cognition_validity","terminal_failed_rate"),))
    plus7=timezone(timedelta(hours=7))
    a=run(source)
    b=run(source,rs=NOW.astimezone(plus7),ru=REF_END.astimezone(plus7),cs=REF_END.astimezone(plus7),cu=CAND_END.astimezone(plus7))
    assert a.plan_fingerprint==b.plan_fingerprint


def test_d158_w_item_order_is_deterministic():
    source=advisory((
        signal("evidence_sufficiency","bounded_insufficiency_rate"),
        signal("evidence_integrity","invalid_evidence_rate"),
        signal("cognition_validity","terminal_failed_rate"),
    ),recommendation="benchmark_review_recommended")
    result=run(source)
    assert [item.domain for item in result.items]==[
        "evidence_integrity","cognition_validity","evidence_sufficiency",
    ]


def test_d158_m_task_segment_is_forwarded_without_rewriting():
    source=advisory((signal("task_concentration","adverse_outcome_rate_vs_overall","software_engineering"),))
    item=run(source).items[0]
    assert item.segment_key=="software_engineering"
    assert item.benchmark_segment_key=="software_engineering"
