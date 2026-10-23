from __future__ import annotations

from typing import get_args

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.contracts.governed_execution_experience_trust import (
    D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION,
    GovernedExecutionExperienceTrustEligibility,
    GovernedExecutionExperienceTrustEventType,
    GovernedExecutionExperienceTrustState,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.db.session import create_database_engine
from app.models.execution_experience_review import ExecutionExperienceReviewEventRecord
from app.repositories.execution_experience_reviews import (
    ExecutionExperienceReviewRepository,
)
from app.repositories.trusted_execution_experiences import (
    TrustedExecutionExperienceRepository,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewLifecycleService,
)
from app.services.execution_experience_trust_lifecycle import (
    ExecutionExperienceTrustConflictError,
    ExecutionExperienceTrustLifecycleService,
    ExecutionExperienceTrustNotFoundError,
    ExecutionExperienceTrustValidationError,
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
    "approval_authority",
    "authorization_authority",
    "execution_authority",
    "retry_authority",
    "rollback_authority",
    "trust_authority",
    "learning_authority",
    "memory_write_authority",
    "routing_authority",
    "model_selection_authority",
    "policy_authority",
    "configuration_authority",
    "automatic_promotion",
    "automatic_learning",
    "automatic_execution",
)


def build_services(*, decision: str = "accept"):
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    scope = WorkspaceScope(WorkspaceId.PERSONAL)

    feedback_store = GovernedExecutionOutcomeFeedbackStore()
    runtime_store = GovernedExecutionExperienceRuntimeStore()
    integration = GovernedExecutionExperienceRuntimeIntegration(
        feedback_store=feedback_store,
        runtime_store=runtime_store,
    )
    feedback = feedback_for(
        approval_id=f"approval-d187-{decision}",
        request_id=f"request-d187-{decision}",
    )
    feedback_store.register(feedback)
    assert integration.try_integrate(feedback.approval_id)

    d186 = ExecutionExperienceReviewLifecycleService(
        repository=ExecutionExperienceReviewRepository(session, scope),
        runtime_store=runtime_store,
    )
    review = d186.capture(feedback.approval_id)
    assert review is not None
    if decision == "accept":
        review = d186.accept(review.id, 1, review.source_review_fingerprint)
    elif decision == "reject":
        review = d186.reject(review.id, 1, review.source_review_fingerprint)
    elif decision != "pending":
        raise AssertionError(decision)

    d187 = ExecutionExperienceTrustLifecycleService(
        review_repository=ExecutionExperienceReviewRepository(session, scope),
        trusted_repository=TrustedExecutionExperienceRepository(session, scope),
    )
    return engine, session, d186, d187, review


def promote(service, review):
    eligibility = service.evaluate(review.id)
    assert eligibility.proposal is not None
    return service.promote(
        review_id=review.id,
        expected_revision=2,
        source_record_fingerprint=eligibility.proposal.source_d186_record_fingerprint,
        promotion_fingerprint=eligibility.proposal.promotion_fingerprint,
    )


def test_d187_contract_version_and_vocabularies_are_exact():
    assert (
        D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION
        == "o-ai.governed-execution-experience-trust.v1"
    )
    assert get_args(GovernedExecutionExperienceTrustEligibility) == (
        "eligible_for_owner_promotion",
        "ineligible",
        "invalid_evidence",
    )
    assert get_args(GovernedExecutionExperienceTrustState) == (
        "TRUSTED",
        "REVOKED",
    )
    assert get_args(GovernedExecutionExperienceTrustEventType) == (
        "OWNER_PROMOTED",
        "OWNER_REVOKED",
    )


def test_d187_review_accepted_is_eligible_but_does_not_write_trust():
    engine, session, _, service, review = build_services()
    try:
        result = service.evaluate(review.id)
        assert result.eligibility == "eligible_for_owner_promotion"
        assert result.reason_code == "review_accepted"
        assert result.proposal is not None
        assert service.list(None, 1, 25).total == 0
        for field_name in AUTHORITY_FIELDS:
            assert getattr(result.proposal, field_name) is False
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("decision", ["pending", "reject"])
def test_d187_nonaccepted_reviews_are_ineligible(decision):
    engine, session, _, service, review = build_services(decision=decision)
    try:
        result = service.evaluate(review.id)
        assert result.eligibility == "ineligible"
        assert result.proposal is None
        assert service.list(None, 1, 25).total == 0
    finally:
        session.close()
        engine.dispose()


def test_d187_incoherent_accepted_history_is_invalid_evidence():
    engine, session, _, service, review = build_services()
    try:
        session.execute(
            delete(ExecutionExperienceReviewEventRecord).where(
                ExecutionExperienceReviewEventRecord.execution_experience_review_id
                == str(review.id),
                ExecutionExperienceReviewEventRecord.sequence == 2,
            )
        )
        session.commit()
        result = service.evaluate(review.id)
        assert result.eligibility == "invalid_evidence"
        assert result.proposal is None
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("source_classification", "execution_failed"),
        ("experience_outcome_class", "execution_failure"),
        ("experience_lesson_code", "authorized_execution_failed"),
        ("review_reason_code", "adverse_execution_outcome"),
        ("risk_class", "R1"),
        ("effect", "write"),
    ),
)
def test_d187_tampered_safe_lineage_is_invalid_evidence(field_name, bad_value):
    engine, session, _, service, review = build_services()
    try:
        record = service._review_repository.get(str(review.id))
        assert record is not None
        setattr(record, field_name, bad_value)
        with session.no_autoflush:
            result = service.evaluate(review.id)
            assert result.eligibility == "invalid_evidence"
            assert result.proposal is None
            assert service.list(None, 1, 25).total == 0
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def test_d187_explicit_promotion_creates_trusted_revision_one_and_owner_event():
    engine, session, _, service, review = build_services()
    try:
        trusted = promote(service, review)
        assert trusted.state == "TRUSTED"
        assert trusted.current_revision == 1
        assert trusted.source_review_id == review.id
        for field_name in AUTHORITY_FIELDS:
            assert getattr(trusted, field_name) is False
        history = service.history(trusted.id)
        assert [
            (item.sequence, item.event_type, item.from_state, item.to_state, item.actor)
            for item in history.items
        ] == [(1, "OWNER_PROMOTED", None, "TRUSTED", "OWNER")]
    finally:
        session.close()
        engine.dispose()


def test_d187_exact_duplicate_promotion_is_idempotent():
    engine, session, _, service, review = build_services()
    try:
        first = promote(service, review)
        eligibility = service.evaluate(review.id)
        assert eligibility.proposal is not None
        second = service.promote(
            review_id=review.id,
            expected_revision=2,
            source_record_fingerprint=eligibility.proposal.source_d186_record_fingerprint,
            promotion_fingerprint=eligibility.proposal.promotion_fingerprint,
        )
        assert first.id == second.id
        assert service.list(None, 1, 25).total == 1
        assert len(service.history(first.id).items) == 1
    finally:
        session.close()
        engine.dispose()


def test_d187_wrong_promotion_bindings_fail_closed():
    engine, session, _, service, review = build_services()
    try:
        eligibility = service.evaluate(review.id)
        assert eligibility.proposal is not None
        with pytest.raises(ExecutionExperienceTrustValidationError):
            service.promote(
                review_id=review.id,
                expected_revision=2,
                source_record_fingerprint="0" * 64,
                promotion_fingerprint=eligibility.proposal.promotion_fingerprint,
            )
        with pytest.raises(ExecutionExperienceTrustValidationError):
            service.promote(
                review_id=review.id,
                expected_revision=2,
                source_record_fingerprint=eligibility.proposal.source_d186_record_fingerprint,
                promotion_fingerprint="0" * 64,
            )
        assert service.list(None, 1, 25).total == 0
    finally:
        session.close()
        engine.dispose()


def test_d187_stale_review_revision_fails_closed():
    engine, session, _, service, review = build_services()
    try:
        eligibility = service.evaluate(review.id)
        assert eligibility.proposal is not None
        with pytest.raises(ExecutionExperienceTrustConflictError):
            service.promote(
                review_id=review.id,
                expected_revision=1,
                source_record_fingerprint=eligibility.proposal.source_d186_record_fingerprint,
                promotion_fingerprint=eligibility.proposal.promotion_fingerprint,
            )
    finally:
        session.close()
        engine.dispose()


def test_d187_owner_revoke_is_terminal_revision_two():
    engine, session, _, service, review = build_services()
    try:
        trusted = promote(service, review)
        revoked = service.revoke(
            trusted_id=trusted.id,
            expected_revision=1,
            promotion_fingerprint=trusted.promotion_fingerprint,
        )
        assert revoked.state == "REVOKED"
        assert revoked.current_revision == 2
        assert [item.event_type for item in service.history(trusted.id).items] == [
            "OWNER_PROMOTED",
            "OWNER_REVOKED",
        ]
        with pytest.raises(ExecutionExperienceTrustConflictError):
            service.revoke(
                trusted_id=trusted.id,
                expected_revision=1,
                promotion_fingerprint=trusted.promotion_fingerprint,
            )
    finally:
        session.close()
        engine.dispose()


def test_d187_cross_workspace_isolation_for_review_and_trusted_root():
    engine, session, _, personal, review = build_services()
    try:
        trusted = promote(personal, review)
        company_scope = WorkspaceScope(WorkspaceId.COMPANY)
        company = ExecutionExperienceTrustLifecycleService(
            review_repository=ExecutionExperienceReviewRepository(
                session,
                company_scope,
            ),
            trusted_repository=TrustedExecutionExperienceRepository(
                session,
                company_scope,
            ),
        )
        with pytest.raises(ExecutionExperienceTrustNotFoundError):
            company.evaluate(review.id)
        with pytest.raises(ExecutionExperienceTrustNotFoundError):
            company.get(trusted.id)
    finally:
        session.close()
        engine.dispose()
