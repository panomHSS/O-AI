from __future__ import annotations

from dataclasses import fields
from typing import get_args

import pytest

from app.contracts.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewAssessment,
)
from app.contracts.governed_execution_experience_runtime import (
    D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION,
    D185_RETENTION_DISPOSITION,
    GovernedExecutionExperienceRuntimeOutcome,
    GovernedExecutionExperienceRuntimeStatus,
)
from app.contracts.workspace import WorkspaceScope
from app.services.governed_execution_experience_candidate import (
    GovernedExecutionExperienceProjector,
)
from app.services.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewEvaluator,
)
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeConflictError,
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
    GovernedExecutionExperienceRuntimeStoreFullError,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackRecorder,
    GovernedExecutionOutcomeFeedbackStore,
)
from app.services.owner_approved_governed_execution import (
    CognitiveExecutionBindingStore,
    OwnerApprovedGovernedExecutionService,
)
from tests.test_d181_owner_approved_governed_execution import (
    binding_from,
    build_d45,
    proposal,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

AUTHORITY_FIELDS = (
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "persistence_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


def integration_for(feedback=None, *, max_items=100):
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    if feedback is not None:
        feedback_store.register(feedback)
    runtime_store = GovernedExecutionExperienceRuntimeStore(max_items=max_items)
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback_store,
        runtime_store=runtime_store,
    )
    return integration, runtime_store, feedback_store


def test_d185_contract_constants_and_status_vocabulary_are_exact():
    assert (
        D185_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_CONTRACT_VERSION
        == "o-ai.governed-execution-experience-runtime.v1"
    )
    assert D185_RETENTION_DISPOSITION == "ephemeral"
    assert get_args(GovernedExecutionExperienceRuntimeStatus) == (
        "review_eligible",
        "review_ineligible",
        "invalid_evidence",
        "projection_failed",
        "integration_unavailable",
    )


@pytest.mark.parametrize("field_name", AUTHORITY_FIELDS)
def test_d185_all_authority_defaults_are_false(field_name: str):
    feedback = feedback_for()
    integration, store, _ = integration_for(feedback)
    assert integration.try_integrate(feedback.approval_id)
    outcome = store.get(feedback.approval_id)
    assert outcome is not None
    assert getattr(outcome, field_name) is False


def test_d185_store_exact_duplicate_is_idempotent():
    feedback = feedback_for()
    integration, store, _ = integration_for(feedback)
    assert integration.try_integrate(feedback.approval_id)
    first = store.get(feedback.approval_id)
    assert first is not None
    assert store.register(first) is first
    assert store.outcome_count == 1


def test_d185_store_conflicting_duplicate_is_rejected_without_overwrite():
    feedback = feedback_for()
    integration, store, _ = integration_for(feedback)
    assert integration.try_integrate(feedback.approval_id)
    first = store.get(feedback.approval_id)
    assert first is not None
    conflict = GovernedExecutionExperienceRuntimeOutcome(
        approval_id=first.approval_id,
        runtime_status="integration_unavailable",
        source_feedback_fingerprint=None,
        candidate=None,
        review=None,
    )
    with pytest.raises(GovernedExecutionExperienceRuntimeConflictError):
        store.register(conflict)
    assert store.get(feedback.approval_id) is first


def test_d185_store_is_bounded_without_silent_eviction():
    first = feedback_for(approval_id="approval-d185-a", request_id="request-d185-a")
    second = feedback_for(approval_id="approval-d185-b", request_id="request-d185-b")
    integration, store, feedback_store = integration_for(first, max_items=1)
    feedback_store.register(second)
    assert integration.try_integrate(first.approval_id)
    assert integration.try_integrate(second.approval_id) is False
    assert store.get(first.approval_id) is not None
    assert store.get(second.approval_id) is None
    assert store.outcome_count == 1

    with pytest.raises(GovernedExecutionExperienceRuntimeStoreFullError):
        store.register(
            GovernedExecutionExperienceRuntimeOutcome(
                approval_id="approval-d185-c",
                runtime_status="integration_unavailable",
                source_feedback_fingerprint=None,
                candidate=None,
                review=None,
            )
        )


def test_d185_missing_d182_feedback_becomes_integration_unavailable():
    integration, store, _ = integration_for()
    assert integration.try_integrate("approval-d185-missing")
    outcome = store.get("approval-d185-missing")
    assert outcome is not None
    assert outcome.runtime_status == "integration_unavailable"
    assert outcome.source_feedback_fingerprint is None
    assert outcome.candidate is None
    assert outcome.review is None


@pytest.mark.parametrize(
    (
        "decision",
        "execution_status",
        "result_status",
        "classification",
        "expected_runtime",
        "expected_review",
        "expected_reason",
    ),
    (
        (
            "approved",
            "completed",
            "succeeded",
            "execution_succeeded",
            "review_eligible",
            "eligible_for_owner_review",
            "authorized_execution_succeeded",
        ),
        (
            "denied",
            "blocked",
            None,
            "owner_denied",
            "review_ineligible",
            "ineligible",
            "owner_declined",
        ),
        (
            "approved",
            "completed",
            "failed",
            "execution_failed",
            "review_ineligible",
            "ineligible",
            "adverse_execution_outcome",
        ),
        (
            "approved",
            "blocked",
            None,
            "execution_blocked",
            "review_ineligible",
            "ineligible",
            "adverse_execution_outcome",
        ),
        (
            "approved",
            "rejected",
            None,
            "execution_rejected",
            "review_ineligible",
            "ineligible",
            "adverse_execution_outcome",
        ),
        (
            "approved",
            "unavailable",
            None,
            "execution_unavailable",
            "review_ineligible",
            "ineligible",
            "adverse_execution_outcome",
        ),
    ),
)
def test_d185_exact_d182_d183_d184_runtime_matrix(
    decision,
    execution_status,
    result_status,
    classification,
    expected_runtime,
    expected_review,
    expected_reason,
):
    feedback = feedback_for(
        decision=decision,
        execution_status=execution_status,
        result_status=result_status,
    )
    assert feedback.classification == classification

    integration, store, _ = integration_for(feedback)
    assert integration.try_integrate(feedback.approval_id)
    outcome = store.get(feedback.approval_id)
    assert outcome is not None
    assert outcome.runtime_status == expected_runtime
    assert outcome.source_feedback_fingerprint == feedback.feedback_fingerprint
    assert outcome.candidate is not None
    assert outcome.candidate.source_feedback_fingerprint == feedback.feedback_fingerprint
    assert outcome.review is not None
    assert outcome.review.eligibility == expected_review
    assert outcome.review.reason_code == expected_reason

    if expected_runtime == "review_eligible":
        assert outcome.review.proposal is not None
        assert (
            outcome.review.proposal.source_candidate_fingerprint
            == outcome.candidate.candidate_fingerprint
        )
        assert (
            outcome.review.proposal.source_feedback_fingerprint
            == feedback.feedback_fingerprint
        )
    else:
        assert outcome.review.proposal is None


def test_d185_projection_failure_stops_before_d184(monkeypatch):
    feedback = feedback_for()
    integration, store, _ = integration_for(feedback)
    calls = {"review": 0}

    monkeypatch.setattr(
        GovernedExecutionExperienceProjector,
        "project",
        classmethod(lambda cls, value: None),
    )

    def forbidden_review(cls, value):
        calls["review"] += 1
        raise AssertionError("D184 must not run after D183 projection failure")

    monkeypatch.setattr(
        GovernedExecutionExperienceReviewEvaluator,
        "evaluate",
        classmethod(forbidden_review),
    )

    assert integration.try_integrate(feedback.approval_id)
    outcome = store.get(feedback.approval_id)
    assert outcome is not None
    assert outcome.runtime_status == "projection_failed"
    assert outcome.candidate is None
    assert outcome.review is None
    assert calls["review"] == 0


def test_d185_maps_exact_d184_invalid_evidence(monkeypatch):
    feedback = feedback_for()
    integration, store, _ = integration_for(feedback)

    monkeypatch.setattr(
        GovernedExecutionExperienceReviewEvaluator,
        "evaluate",
        classmethod(
            lambda cls, value: GovernedExecutionExperienceReviewAssessment(
                eligibility="invalid_evidence",
                reason_code="invalid_evidence",
                proposal=None,
            )
        ),
    )

    assert integration.try_integrate(feedback.approval_id)
    outcome = store.get(feedback.approval_id)
    assert outcome is not None
    assert outcome.runtime_status == "invalid_evidence"
    assert outcome.candidate is not None
    assert outcome.review is not None
    assert outcome.review.eligibility == "invalid_evidence"


def test_d185_contract_rejects_eligible_without_review():
    feedback = feedback_for()
    candidate = GovernedExecutionExperienceProjector.project(feedback)
    assert candidate is not None
    with pytest.raises(ValueError):
        GovernedExecutionExperienceRuntimeOutcome(
            approval_id=feedback.approval_id,
            runtime_status="review_eligible",
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            candidate=candidate,
            review=None,
        )


def test_d185_contract_rejects_ineligible_with_eligible_proposal():
    feedback = feedback_for()
    candidate = GovernedExecutionExperienceProjector.project(feedback)
    assert candidate is not None
    review = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert review.proposal is not None
    with pytest.raises(ValueError):
        GovernedExecutionExperienceRuntimeOutcome(
            approval_id=feedback.approval_id,
            runtime_status="review_ineligible",
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            candidate=candidate,
            review=review,
        )


def test_d185_contract_rejects_tampered_lineage():
    feedback = feedback_for()
    candidate = GovernedExecutionExperienceProjector.project(feedback)
    assert candidate is not None
    review = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
    assert review.proposal is not None
    with pytest.raises(ValueError):
        GovernedExecutionExperienceRuntimeOutcome(
            approval_id="different-approval",
            runtime_status="review_eligible",
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            candidate=candidate,
            review=review,
        )


def test_d185_contract_has_no_raw_sensitive_field_surface():
    names = {field.name for field in fields(GovernedExecutionExperienceRuntimeOutcome)}
    assert names.isdisjoint(
        {
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
    )


class SpyIntegration:
    def __init__(self, *, explode=False):
        self.calls = []
        self.explode = explode

    def try_integrate(self, approval_id):
        self.calls.append(approval_id)
        if self.explode:
            raise RuntimeError("private d185 failure")
        return True


class FalseRecorder:
    def __init__(self):
        self.calls = 0

    def try_record(self, binding, outcome):
        self.calls += 1
        return False


def bound_owner_service(*, recorder, integration):
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    service = OwnerApprovedGovernedExecutionService(
        binding_store=bindings,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=recorder,
        experience_runtime_integration=integration,
    )
    return service, reviewed, read


def test_d185_runs_once_only_after_successful_d182_recording():
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    recorder = GovernedExecutionOutcomeFeedbackRecorder(store=feedback_store)
    spy = SpyIntegration()
    service, reviewed, read = bound_owner_service(
        recorder=recorder,
        integration=spy,
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert spy.calls == [reviewed.approval_id]
    assert feedback_store.get(reviewed.approval_id) is not None


def test_d185_does_not_run_when_d182_recording_returns_false():
    recorder = FalseRecorder()
    spy = SpyIntegration()
    service, reviewed, read = bound_owner_service(
        recorder=recorder,
        integration=spy,
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert recorder.calls == 1
    assert spy.calls == []


def test_d185_exception_cannot_change_approved_d45_outcome():
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    recorder = GovernedExecutionOutcomeFeedbackRecorder(store=feedback_store)
    service, reviewed, read = bound_owner_service(
        recorder=recorder,
        integration=SpyIntegration(explode=True),
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.decision == "approved"
    assert result.execution.status == "completed"
    assert result.execution.result is not None
    assert result.execution.result.status == "succeeded"
    assert read.calls == 1
    assert feedback_store.get(reviewed.approval_id) is not None


def test_d185_exception_cannot_change_denied_d45_outcome():
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    recorder = GovernedExecutionOutcomeFeedbackRecorder(store=feedback_store)
    service, reviewed, read = bound_owner_service(
        recorder=recorder,
        integration=SpyIntegration(explode=True),
    )
    result = service.deny(reviewed.approval_id, reviewed.plan_digest)
    assert result.decision == "denied"
    assert result.execution.status == "blocked"
    assert result.execution.result is None
    assert read.calls == 0
    assert feedback_store.get(reviewed.approval_id) is not None


def test_d185_unbound_legacy_d45_invokes_neither_d182_nor_d185():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    recorder = FalseRecorder()
    spy = SpyIntegration()
    service = OwnerApprovedGovernedExecutionService(
        binding_store=CognitiveExecutionBindingStore(),
        approval_service=d45,
        workspace_scope=None,
        outcome_feedback_recorder=recorder,
        experience_runtime_integration=spy,
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert recorder.calls == 0
    assert spy.calls == []
