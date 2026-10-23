from __future__ import annotations

from app.contracts.governed_execution_experience_trust import (
    compute_governed_execution_experience_trust_promotion_fingerprint,
)
from tests.test_d187_execution_experience_trust import build_services


def fingerprint(proposal, *, source_turn_id: str | None = None):
    return compute_governed_execution_experience_trust_promotion_fingerprint(
        workspace_id=proposal.workspace_id,
        conversation_id=proposal.conversation_id,
        source_turn_id=(
            proposal.source_turn_id
            if source_turn_id is None
            else source_turn_id
        ),
        source_artifact_digest=proposal.source_artifact_digest,
        intent_digest=proposal.intent_digest,
        approval_id=proposal.approval_id,
        execution_request_id=proposal.execution_request_id,
        plan_digest=proposal.plan_digest,
        source_feedback_fingerprint=proposal.source_feedback_fingerprint,
        source_candidate_fingerprint=proposal.source_candidate_fingerprint,
        source_review_fingerprint=proposal.source_review_fingerprint,
        source_d186_record_fingerprint=proposal.source_d186_record_fingerprint,
        target_kind=proposal.target_kind,
        capability_id=proposal.capability_id,
        adapter_id=proposal.adapter_id,
        operation=proposal.operation,
        effect=proposal.effect,
        risk_class=proposal.risk_class,
        source_classification=proposal.source_classification,
        experience_outcome_class=proposal.experience_outcome_class,
        experience_lesson_code=proposal.experience_lesson_code,
        review_reason_code=proposal.review_reason_code,
    )


def test_d187_identical_safe_lineage_has_identical_promotion_fingerprint():
    engine, session, _, service, review = build_services()
    try:
        result = service.evaluate(review.id)
        assert result.proposal is not None
        proposal = service._assess(
            service._review_repository.get(str(review.id))
        ).proposal
        assert proposal is not None
        assert fingerprint(proposal) == proposal.promotion_fingerprint
        assert fingerprint(proposal) == fingerprint(proposal)
    finally:
        session.close()
        engine.dispose()


def test_d187_safe_lineage_change_changes_promotion_fingerprint():
    engine, session, _, service, review = build_services()
    try:
        proposal = service._assess(
            service._review_repository.get(str(review.id))
        ).proposal
        assert proposal is not None
        assert fingerprint(proposal) != fingerprint(
            proposal,
            source_turn_id="different-source-turn",
        )
    finally:
        session.close()
        engine.dispose()


def test_d187_promotion_fingerprint_excludes_trusted_lifecycle_identity_and_time():
    engine, session, _, service, review = build_services()
    try:
        assessment = service._assess(
            service._review_repository.get(str(review.id))
        )
        proposal = assessment.proposal
        assert proposal is not None
        assert not hasattr(proposal, "id")
        assert not hasattr(proposal, "state")
        assert not hasattr(proposal, "current_revision")
        assert not hasattr(proposal, "created_at")
        assert not hasattr(proposal, "updated_at")
    finally:
        session.close()
        engine.dispose()
