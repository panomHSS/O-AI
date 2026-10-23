from __future__ import annotations

from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.api.v1.execution_experience_reviews import (
    accept_execution_experience_review,
    execution_experience_review_history,
    get_execution_experience_review,
    list_execution_experience_reviews,
    reject_execution_experience_review,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.db.session import create_database_engine
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.schemas.execution_experience_reviews import (
    ExecutionExperienceReviewDecisionRequest,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewLifecycleService,
)
from app.services.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeIntegration,
    GovernedExecutionExperienceRuntimeStore,
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


def build_service():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    runtime_store = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback_store,
        runtime_store=runtime_store,
    )
    feedback = feedback_for(
        approval_id="approval-d186-api",
        request_id="request-d186-api",
    )
    feedback_store.register(feedback)
    assert integration.try_integrate(feedback.approval_id)
    service = ExecutionExperienceReviewLifecycleService(
        repository=ExecutionExperienceReviewRepository(
            session,
            WorkspaceScope(WorkspaceId.PERSONAL),
        ),
        runtime_store=runtime_store,
    )
    record = service.capture(feedback.approval_id)
    assert record is not None
    return engine, session, service, record


def test_d186_api_read_surface_and_accept_shape():
    engine, session, service, record = build_service()
    try:
        listed = list_execution_experience_reviews(
            service=service,
            page=1,
            page_size=25,
            state=None,
        )
        assert listed.success is True
        assert listed.data.total == 1

        fetched = get_execution_experience_review(record.id, service)
        assert fetched.data.id == record.id

        history = execution_experience_review_history(record.id, service)
        assert [item.event_type for item in history.data.items] == ["PROPOSED"]

        accepted = accept_execution_experience_review(
            review_id=record.id,
            revision=1,
            payload=ExecutionExperienceReviewDecisionRequest(
                source_review_fingerprint=record.source_review_fingerprint
            ),
            service=service,
        )
        assert accepted.success is True
        assert accepted.data.state == "REVIEW_ACCEPTED"
        assert accepted.data.trust_authority is False
        assert accepted.data.automatic_trust is False
    finally:
        session.close()
        engine.dispose()


def test_d186_api_reject_shape():
    engine, session, service, record = build_service()
    try:
        rejected = reject_execution_experience_review(
            review_id=record.id,
            revision=1,
            payload=ExecutionExperienceReviewDecisionRequest(
                source_review_fingerprint=record.source_review_fingerprint
            ),
            service=service,
        )
        assert rejected.success is True
        assert rejected.data.state == "REVIEW_REJECTED"
        assert rejected.data.current_revision == 2
    finally:
        session.close()
        engine.dispose()


class SpyD186Lifecycle:
    def __init__(self, *, explode: bool = False):
        self.calls: list[str] = []
        self.explode = explode

    def try_capture(self, approval_id: str) -> bool:
        self.calls.append(approval_id)
        if self.explode:
            raise RuntimeError("private d186 capture failure")
        return True


def owner_service_with_d186(spy):
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    binding = binding_from(reviewed)
    bindings = CognitiveExecutionBindingStore()
    bindings.register(binding)
    feedback = GovernedExecutionOutcomeFeedbackStore()
    runtime = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback,
        runtime_store=runtime,
    )
    service = OwnerApprovedGovernedExecutionService(
        binding_store=bindings,
        approval_service=d45,
        workspace_scope=WorkspaceScope(binding.workspace_id),
        outcome_feedback_recorder=GovernedExecutionOutcomeFeedbackRecorder(
            store=feedback
        ),
        experience_runtime_integration=integration,
        experience_owner_review_lifecycle=spy,
    )
    return service, reviewed, read, runtime


def test_d186_production_capture_runs_once_after_successful_d185_integration():
    spy = SpyD186Lifecycle()
    service, reviewed, read, runtime = owner_service_with_d186(spy)
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert runtime.get(reviewed.approval_id) is not None
    assert spy.calls == [reviewed.approval_id]


def test_d186_capture_exception_cannot_change_execution_outcome():
    spy = SpyD186Lifecycle(explode=True)
    service, reviewed, read, runtime = owner_service_with_d186(spy)
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.decision == "approved"
    assert result.execution.status == "completed"
    assert result.execution.result is not None
    assert result.execution.result.status == "succeeded"
    assert read.calls == 1
    assert runtime.get(reviewed.approval_id) is not None
    assert spy.calls == [reviewed.approval_id]


def test_d186_unbound_legacy_d45_invokes_no_review_capture():
    d45, read, _ = build_d45()
    reviewed = proposal(d45)
    spy = SpyD186Lifecycle()
    service = OwnerApprovedGovernedExecutionService(
        binding_store=CognitiveExecutionBindingStore(),
        approval_service=d45,
        workspace_scope=None,
        outcome_feedback_recorder=None,
        experience_runtime_integration=None,
        experience_owner_review_lifecycle=spy,
    )
    result = service.approve(reviewed.approval_id, reviewed.plan_digest)
    assert result.execution.status == "completed"
    assert read.calls == 1
    assert spy.calls == []
