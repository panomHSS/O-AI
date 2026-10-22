from __future__ import annotations

from dataclasses import fields, replace
from typing import get_args

import pytest

from app.contracts.governed_execution_experience_candidate import (
    D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION,
    D183_PROMOTION_DISPOSITION,
    D183_RETENTION_DISPOSITION,
    GovernedExecutionExperienceCandidate,
    GovernedExecutionExperienceLessonCode,
    GovernedExecutionExperienceOutcomeClass,
)
from app.services.governed_execution_experience_candidate import (
    GovernedExecutionExperienceProjector,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
    GovernedExecutionOutcomeFeedbackStore,
)
from tests.test_d182_governed_execution_outcome_feedback import binding_for, outcome


CASES = (
    (
        "approved",
        "completed",
        "succeeded",
        "execution_succeeded",
        "success",
        "authorized_execution_succeeded",
    ),
    (
        "denied",
        "blocked",
        None,
        "owner_denied",
        "owner_declined",
        "owner_declined_execution",
    ),
    (
        "approved",
        "completed",
        "failed",
        "execution_failed",
        "execution_failure",
        "authorized_execution_failed",
    ),
    (
        "approved",
        "blocked",
        None,
        "execution_blocked",
        "execution_blocked",
        "execution_policy_blocked",
    ),
    (
        "approved",
        "rejected",
        None,
        "execution_rejected",
        "execution_rejected",
        "execution_request_rejected",
    ),
    (
        "approved",
        "unavailable",
        None,
        "execution_unavailable",
        "execution_unavailable",
        "execution_capability_unavailable",
    ),
)

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_promotion",
)


def feedback_for(
    *,
    decision: str = "approved",
    execution_status: str = "completed",
    result_status: str | None = "succeeded",
    approval_id: str = "approval-d183",
    request_id: str = "request-d183",
):
    decision_outcome = outcome(
        approval_id=approval_id,
        request_id=request_id,
        decision=decision,
        execution_status=execution_status,
        result_status=result_status,
        reason_code=(
            "owner_approval_denied"
            if decision == "denied"
            else f"d183-{execution_status}"
        ),
    )
    binding = binding_for(decision_outcome)
    store = GovernedExecutionOutcomeFeedbackStore()
    recorder = GovernedExecutionOutcomeFeedbackRecorder(store=store)
    assert recorder.try_record(binding, decision_outcome)
    feedback = store.get(decision_outcome.approval_id)
    assert feedback is not None
    return feedback


@pytest.mark.parametrize(
    (
        "decision",
        "execution_status",
        "result_status",
        "source_classification",
        "expected_outcome",
        "expected_lesson",
    ),
    CASES,
)
def test_d183_exact_d182_projection_matrix(
    decision,
    execution_status,
    result_status,
    source_classification,
    expected_outcome,
    expected_lesson,
):
    feedback = feedback_for(
        decision=decision,
        execution_status=execution_status,
        result_status=result_status,
    )
    assert feedback.classification == source_classification

    candidate = GovernedExecutionExperienceProjector.project(feedback)
    assert candidate is not None
    assert candidate.source_classification == source_classification
    assert candidate.experience_outcome_class == expected_outcome
    assert candidate.experience_lesson_code == expected_lesson


def test_d183_owner_denial_is_not_execution_failure():
    candidate = GovernedExecutionExperienceProjector.project(
        feedback_for(
            decision="denied",
            execution_status="blocked",
            result_status=None,
        )
    )
    assert candidate is not None
    assert candidate.experience_outcome_class == "owner_declined"
    assert candidate.experience_lesson_code == "owner_declined_execution"
    assert candidate.experience_outcome_class != "execution_failure"


def test_d183_exact_safe_lineage_is_preserved():
    feedback = feedback_for()
    candidate = GovernedExecutionExperienceProjector.project(feedback)
    assert candidate is not None

    for name in (
        "workspace_id",
        "conversation_id",
        "source_turn_id",
        "source_artifact_digest",
        "intent_digest",
        "approval_id",
        "execution_request_id",
        "plan_digest",
        "target_kind",
        "capability_id",
        "adapter_id",
        "operation",
        "effect",
        "risk_class",
        "owner_decision",
        "execution_status",
        "result_status",
        "execution_reason_code",
    ):
        assert getattr(candidate, name) == getattr(feedback, name)

    assert candidate.source_feedback_fingerprint == feedback.feedback_fingerprint
    assert candidate.source_classification == feedback.classification


def test_d183_contract_constants_and_vocabularies_are_exact():
    assert (
        D183_GOVERNED_EXECUTION_EXPERIENCE_CONTRACT_VERSION
        == "o-ai.governed-execution-experience-candidate.v1"
    )
    assert D183_RETENTION_DISPOSITION == "ephemeral"
    assert D183_PROMOTION_DISPOSITION == "candidate_only"
    assert get_args(GovernedExecutionExperienceOutcomeClass) == (
        "success",
        "owner_declined",
        "execution_failure",
        "execution_blocked",
        "execution_rejected",
        "execution_unavailable",
    )
    assert get_args(GovernedExecutionExperienceLessonCode) == (
        "authorized_execution_succeeded",
        "owner_declined_execution",
        "authorized_execution_failed",
        "execution_policy_blocked",
        "execution_request_rejected",
        "execution_capability_unavailable",
    )


def test_d183_candidate_fingerprint_is_sha256_hex():
    candidate = GovernedExecutionExperienceProjector.project(feedback_for())
    assert candidate is not None
    assert len(candidate.candidate_fingerprint) == 64
    int(candidate.candidate_fingerprint, 16)


def test_d183_retention_and_promotion_are_exact():
    candidate = GovernedExecutionExperienceProjector.project(feedback_for())
    assert candidate is not None
    assert candidate.retention_disposition == "ephemeral"
    assert candidate.promotion_disposition == "candidate_only"


@pytest.mark.parametrize("field_name", AUTHORITY_FIELDS)
def test_d183_authority_firewall_is_false(field_name: str):
    candidate = GovernedExecutionExperienceProjector.project(feedback_for())
    assert candidate is not None
    assert getattr(candidate, field_name) is False


def test_d183_wrong_input_type_fails_closed():
    assert GovernedExecutionExperienceProjector.project(object()) is None
    assert GovernedExecutionExperienceProjector.project(None) is None


def test_d183_tampered_d182_fingerprint_fails_closed():
    feedback = feedback_for()
    object.__setattr__(feedback, "feedback_fingerprint", "0" * 64)
    assert GovernedExecutionExperienceProjector.project(feedback) is None


def test_d183_tampered_d182_authority_flag_fails_closed():
    feedback = feedback_for()
    object.__setattr__(feedback, "execution_authority", True)
    assert GovernedExecutionExperienceProjector.project(feedback) is None


def test_d183_manual_outcome_lesson_mismatch_is_rejected():
    candidate = GovernedExecutionExperienceProjector.project(feedback_for())
    assert candidate is not None
    with pytest.raises(ValueError):
        replace(
            candidate,
            experience_lesson_code="owner_declined_execution",
        )


def test_d183_manual_owner_decision_mismatch_is_rejected():
    candidate = GovernedExecutionExperienceProjector.project(feedback_for())
    assert candidate is not None
    with pytest.raises(ValueError):
        replace(candidate, owner_decision="denied")


def test_d183_candidate_has_no_raw_or_sensitive_field_surface():
    names = {field.name for field in fields(GovernedExecutionExperienceCandidate)}
    forbidden = {
        "output",
        "error",
        "parameters",
        "payload",
        "prompt",
        "response",
        "credentials",
        "token",
        "secret",
    }
    assert names.isdisjoint(forbidden)
