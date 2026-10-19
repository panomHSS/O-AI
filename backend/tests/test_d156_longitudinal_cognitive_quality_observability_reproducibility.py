from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_projection import CognitiveQualityProjectionService
from app.services.cognitive_quality_summary import CognitiveQualitySummaryService,rate_text
from tests.test_d136_cognitive_executive import outcome
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson
NOW=datetime(2026,10,20,tzinfo=timezone.utc)

def test_d156_same_evidence_same_fingerprint():
    s=CognitiveQualityProjectionService(clock=lambda:NOW); kw=dict(turn_id="turn-1",outcome=outcome(),candidate=candidate_for_lesson("verified_success"),experience_evaluated=True)
    assert s.project(**kw).projection_fingerprint==s.project(**kw).projection_fingerprint

def test_d156_zero_denominator_not_fake_zero():
    assert rate_text(0,0) is None and rate_text(1,2)=="0.500000"

class Repo:
    def __init__(self,rs): self.rs=rs
    def list_for_summary(self,*,workspace_id,since=None,until=None):
        x=[r for r in self.rs if r.workspace_id==workspace_id.value]
        if since is not None:x=[r for r in x if r.occurred_at>=since]
        if until is not None:x=[r for r in x if r.occurred_at<until]
        return x

def rec(t,c):
    terminal={"verified_success":"completed","adverse_outcome":"failed"}[c]
    return SimpleNamespace(workspace_id="personal",occurred_at=t,quality_classification=c,terminal_state=terminal,verification_result="pass" if c=="verified_success" else None,revision_count=0,critic_exhausted=False,confidence_class="sufficient" if c=="verified_success" else None,experience_cohort="absent",task_kind="general_chat")

def test_d156_comparison_deterministic_no_verdict():
    s=CognitiveQualitySummaryService(Repo([rec(NOW,"verified_success"),rec(NOW+timedelta(hours=1),"adverse_outcome"),rec(NOW+timedelta(days=1),"verified_success"),rec(NOW+timedelta(days=1,hours=1),"verified_success")]),workspace_id=WorkspaceId.PERSONAL)
    r=s.compare(reference_since=NOW,reference_until=NOW+timedelta(days=1),candidate_since=NOW+timedelta(days=1),candidate_until=NOW+timedelta(days=2))
    assert {d.metric:d.delta_count for d in r.count_deltas}["verified_success_count"]==1
    assert not hasattr(r,"verdict")
