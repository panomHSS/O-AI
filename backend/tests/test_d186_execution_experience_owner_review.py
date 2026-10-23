from __future__ import annotations

from dataclasses import fields
from typing import get_args

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.contracts.governed_execution_experience_owner_review import (
    D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION,
    GovernedExecutionExperienceOwnerReviewEventType,
    GovernedExecutionExperienceOwnerReviewProposal,
    GovernedExecutionExperienceOwnerReviewState,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.db.session import create_database_engine
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewConflictError,
    ExecutionExperienceReviewLifecycleService,
    ExecutionExperienceReviewNotFoundError,
    ExecutionExperienceReviewValidationError,
)
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackStore,
)
from tests.test_d183_governed_execution_experience_candidate import feedback_for

AUTHORITY_FIELDS = (
    "execution_authority",
    "authorization_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_owner_decision",
    "automatic_trust",
    "automatic_learning",
    "automatic_promotion",
)


@pytest.fixture()
def lifecycle():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = Session()
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    runtime_store = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback_store,
        runtime_store=runtime_store,
    )
    service = ExecutionExperienceReviewLifecycleService(
        repository=ExecutionExperienceReviewRepository(
            session,
            WorkspaceScope(WorkspaceId.PERSONAL),
        ),
        runtime_store=runtime_store,
    )
    try:
        yield service, session, feedback_store, runtime_store, integration
    finally:
        session.close()
        engine.dispose()


def eligible_runtime(
    lifecycle,
    *,
    approval_id="approval-d186",
    request_id="request-d186",
):
    service, _, feedback_store, runtime_store, integration = lifecycle
    feedback = feedback_for(approval_id=approval_id, request_id=request_id)
    assert feedback.workspace_id is WorkspaceId.PERSONAL
    feedback_store.register(feedback)
    assert integration.try_integrate(approval_id)
    outcome = runtime_store.get(approval_id)
    assert outcome is not None
    assert outcome.runtime_status == "review_eligible"
    assert outcome.review is not None and outcome.review.proposal is not None
    return service, outcome


def test_d186_contract_version_and_vocabularies_are_exact():
    assert (
        D186_GOVERNED_EXECUTION_EXPERIENCE_OWNER_REVIEW_CONTRACT_VERSION
        == "o-ai.governed-execution-experience-owner-review.v1"
    )
    assert get_args(GovernedExecutionExperienceOwnerReviewState) == (
        "PENDING_REVIEW",
        "REVIEW_ACCEPTED",
        "REVIEW_REJECTED",
    )
    assert get_args(GovernedExecutionExperienceOwnerReviewEventType) == (
        "PROPOSED",
        "OWNER_ACCEPTED",
        "OWNER_REJECTED",
    )


def test_d186_eligible_d185_capture_creates_one_pending_review(lifecycle):
    service, outcome = eligible_runtime(lifecycle)
    captured = service.capture(outcome.approval_id)
    assert captured is not None
    assert captured.state == "PENDING_REVIEW"
    assert captured.current_revision == 1
    assert (
        captured.source_review_fingerprint
        == outcome.review.proposal.review_fingerprint
    )
    history = service.history(captured.id)
    assert [(item.sequence, item.event_type, item.actor) for item in history.items] == [
        (1, "PROPOSED", "SYSTEM")
    ]


@pytest.mark.parametrize("field_name", AUTHORITY_FIELDS)
def test_d186_all_response_authority_defaults_are_false(lifecycle, field_name: str):
    service, outcome = eligible_runtime(lifecycle)
    captured = service.capture(outcome.approval_id)
    assert captured is not None
    assert getattr(captured, field_name) is False


def test_d186_exact_duplicate_capture_is_idempotent(lifecycle):
    service, outcome = eligible_runtime(lifecycle)
    first = service.capture(outcome.approval_id)
    second = service.capture(outcome.approval_id)
    assert first is not None and second is not None
    assert first.id == second.id
    assert first.record_fingerprint == second.record_fingerprint
    assert len(service.history(first.id).items) == 1


@pytest.mark.parametrize(
    ("decision", "execution_status", "result_status"),
    (
        ("denied", "blocked", None),
        ("approved", "completed", "failed"),
        ("approved", "blocked", None),
        ("approved", "rejected", None),
        ("approved", "unavailable", None),
    ),
)
def test_d186_nonreviewable_d185_outcomes_create_no_record(
    lifecycle,
    decision,
    execution_status,
    result_status,
):
    service, _, feedback_store, runtime_store, integration = lifecycle
    feedback = feedback_for(
        decision=decision,
        execution_status=execution_status,
        result_status=result_status,
        approval_id="approval-d186-nonreview",
        request_id="request-d186-nonreview",
    )
    feedback_store.register(feedback)
    assert integration.try_integrate(feedback.approval_id)
    outcome = runtime_store.get(feedback.approval_id)
    assert outcome is not None
    assert outcome.runtime_status != "review_eligible"
    assert service.capture(feedback.approval_id) is None
    assert service.list(None, 1, 25).total == 0


def test_d186_owner_accept_is_one_time_terminal_transition(lifecycle):
    service, outcome = eligible_runtime(lifecycle)
    record = service.capture(outcome.approval_id)
    assert record is not None
    accepted = service.accept(record.id, 1, record.source_review_fingerprint)
    assert accepted.state == "REVIEW_ACCEPTED"
    assert accepted.current_revision == 2
    with pytest.raises(ExecutionExperienceReviewConflictError):
        service.accept(record.id, 1, record.source_review_fingerprint)
    assert [item.event_type for item in service.history(record.id).items] == [
        "PROPOSED",
        "OWNER_ACCEPTED",
    ]


def test_d186_owner_reject_is_one_time_terminal_transition(lifecycle):
    service, outcome = eligible_runtime(lifecycle)
    record = service.capture(outcome.approval_id)
    assert record is not None
    rejected = service.reject(record.id, 1, record.source_review_fingerprint)
    assert rejected.state == "REVIEW_REJECTED"
    assert rejected.current_revision == 2
    with pytest.raises(ExecutionExperienceReviewConflictError):
        service.reject(record.id, 1, record.source_review_fingerprint)
    assert [item.event_type for item in service.history(record.id).items] == [
        "PROPOSED",
        "OWNER_REJECTED",
    ]


def test_d186_wrong_source_review_fingerprint_fails_closed(lifecycle):
    service, outcome = eligible_runtime(lifecycle)
    record = service.capture(outcome.approval_id)
    assert record is not None
    with pytest.raises(ExecutionExperienceReviewValidationError):
        service.accept(record.id, 1, "0" * 64)
    assert service.get(record.id).state == "PENDING_REVIEW"


def test_d186_cross_workspace_get_is_not_found(lifecycle):
    service, session, _, runtime_store, _ = lifecycle
    _, outcome = eligible_runtime(lifecycle)
    record = service.capture(outcome.approval_id)
    assert record is not None
    company = ExecutionExperienceReviewLifecycleService(
        repository=ExecutionExperienceReviewRepository(
            session,
            WorkspaceScope(WorkspaceId.COMPANY),
        ),
        runtime_store=runtime_store,
    )
    with pytest.raises(ExecutionExperienceReviewNotFoundError):
        company.get(record.id)


def test_d186_contract_has_no_free_text_or_raw_sensitive_surface():
    names = {field.name for field in fields(GovernedExecutionExperienceOwnerReviewProposal)}
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
            "decision_comment",
        }
    )
