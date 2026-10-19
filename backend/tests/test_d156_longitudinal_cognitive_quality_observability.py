from dataclasses import replace
from datetime import datetime, timezone
from app.contracts.cognitive_brain import CognitiveFailureCode, CognitiveTurnState
from app.contracts.cognitive_quality_observability import cognitive_quality_turn_digest
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_quality_projection import CognitiveQualityProjectionService
from tests.test_d136_cognitive_executive import outcome
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson

NOW=datetime(2026,10,20,tzinfo=timezone.utc)

def test_d156_reuses_d146():
    o=CognitiveQualityProjectionService(clock=lambda:NOW).project(turn_id="turn-1",outcome=outcome(),candidate=candidate_for_lesson("verified_success"),experience_evaluated=True)
    assert (o.quality_classification,o.quality_reason_code,o.experience_cohort)==("verified_success","verified_success","absent")
    assert o.source_candidate_fingerprint and o.source_feedback_fingerprint

def test_d156_failure_without_fake_candidate():
    failed=replace(outcome(CognitiveTurnState.FAILED),failure_code=CognitiveFailureCode.CRITIC_UNAVAILABLE)
    o=CognitiveQualityProjectionService(clock=lambda:NOW).project(turn_id="turn-1",outcome=failed,experience_evaluated=False)
    assert (o.quality_classification,o.quality_reason_code,o.experience_cohort)==("adverse_outcome","critic_exhausted","not_evaluated")
    assert o.source_candidate_fingerprint is None

def test_d156_turn_digest_workspace_bound():
    a=cognitive_quality_turn_digest(workspace_id=WorkspaceId.PERSONAL,turn_id="private-turn")
    b=cognitive_quality_turn_digest(workspace_id=WorkspaceId.COMPANY,turn_id="private-turn")
    assert a!=b and len(a)==64 and "private-turn" not in a

def test_d156_authority_firewall():
    o=CognitiveQualityProjectionService(clock=lambda:NOW).project(turn_id="turn-1",outcome=outcome(),candidate=candidate_for_lesson("verified_success"),experience_evaluated=True)
    for n in ("learning_authority","memory_write_authority","experience_trust_authority","routing_authority","model_selection_authority","prompt_mutation_authority","context_mutation_authority","policy_mutation_authority","execution_authority","benchmark_promotion_authority"):
        assert getattr(o,n) is False
