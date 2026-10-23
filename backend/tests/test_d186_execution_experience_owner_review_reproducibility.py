from __future__ import annotations

from app.contracts.governed_execution_experience_owner_review import (
    compute_governed_execution_experience_owner_review_record_fingerprint,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewLifecycleService,
)
from app.services.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewEvaluator,
)
from tests.test_d184_governed_execution_experience_review import candidate_for


def source_proposal():
    review = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate_for())
    assert review.proposal is not None
    return review.proposal


def fingerprint(source, *, source_turn_id: str | None = None):
    return compute_governed_execution_experience_owner_review_record_fingerprint(
        workspace_id=source.workspace_id,
        conversation_id=source.conversation_id,
        source_turn_id=(
            source.source_turn_id
            if source_turn_id is None
            else source_turn_id
        ),
        source_artifact_digest=source.source_artifact_digest,
        intent_digest=source.intent_digest,
        approval_id=source.approval_id,
        execution_request_id=source.execution_request_id,
        plan_digest=source.plan_digest,
        source_feedback_fingerprint=source.source_feedback_fingerprint,
        source_candidate_fingerprint=source.source_candidate_fingerprint,
        source_review_fingerprint=source.review_fingerprint,
        target_kind=source.target_kind,
        capability_id=source.capability_id,
        adapter_id=source.adapter_id,
        operation=source.operation,
        effect=source.effect,
        risk_class=source.risk_class,
        source_classification=source.source_classification,
        experience_outcome_class=source.experience_outcome_class,
        experience_lesson_code=source.experience_lesson_code,
        review_reason_code=source.review_reason_code,
    )


def test_d186_identical_safe_lineage_has_identical_record_fingerprint():
    first = source_proposal()
    second = source_proposal()
    assert fingerprint(first) == fingerprint(second)


def test_d186_record_fingerprint_changes_with_safe_lineage():
    first = source_proposal()
    assert fingerprint(first) != fingerprint(
        first,
        source_turn_id="different-source-turn",
    )


def test_d186_projection_fingerprint_excludes_lifecycle_identity_and_time():
    source = source_proposal()
    projected = ExecutionExperienceReviewLifecycleService._project(source)
    assert projected.record_fingerprint == fingerprint(source)
    assert not hasattr(projected, "id")
    assert not hasattr(projected, "state")
    assert not hasattr(projected, "current_revision")
    assert not hasattr(projected, "created_at")
    assert not hasattr(projected, "updated_at")
