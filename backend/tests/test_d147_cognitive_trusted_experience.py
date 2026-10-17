from __future__ import annotations

from contextlib import contextmanager
from dataclasses import fields

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.cognitive_trusted_experience import (
    D147_REFERENCE_BASELINE,
    CognitiveTrustedExperienceProposal,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.models.trusted_experience import (
    TrustedExperienceEventRecord,
    TrustedExperienceRecord,
)
from app.repositories.trusted_experiences import TrustedExperienceRepository
from app.services.trusted_experience_lifecycle import (
    TrustedExperienceConflictError,
    TrustedExperienceLifecycleService,
    TrustedExperienceNotFoundError,
)
from tests.test_d146_cognitive_outcome_quality_feedback import candidate_for_lesson


@contextmanager
def service_context(workspace_id: WorkspaceId = WorkspaceId.PERSONAL):
    engine = create_engine("sqlite:///:memory:")
    TrustedExperienceRecord.__table__.create(engine)
    TrustedExperienceEventRecord.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        service = TrustedExperienceLifecycleService(
            TrustedExperienceRepository(
                session,
                WorkspaceScope(workspace_id=workspace_id),
            )
        )
        yield service
    finally:
        session.close()
        engine.dispose()


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        with service_context() as service:
            result = service.evaluate(candidate_for_lesson("verified_success"))
            assert result.eligibility == "eligible_for_owner_review"
            assert result.reason_code == "verified_success"
            assert result.reference_baseline == D147_REFERENCE_BASELINE
            assert result.proposal is not None
    elif slot == 1:
        with service_context() as service:
            result = service.evaluate(candidate_for_lesson("bounded_insufficiency"))
            assert result.eligibility == "ineligible"
            assert result.reason_code == "bounded_insufficiency"
            assert result.proposal is None
    elif slot == 2:
        lesson = ("critic_exhausted", "invalid_cognition", "terminal_failure")[variant % 3]
        with service_context() as service:
            result = service.evaluate(candidate_for_lesson(lesson))
            assert result.eligibility == "ineligible"
            assert result.reason_code == "adverse_outcome"
            assert result.proposal is None
    elif slot == 3:
        with service_context() as service:
            result = service.evaluate(object())
            assert result.eligibility == "invalid_evidence"
            assert result.reason_code == "invalid_evidence"
            assert result.proposal is None
    elif slot == 4:
        with service_context() as service:
            left = service.evaluate(candidate_for_lesson("verified_success")).proposal
            right = service.evaluate(candidate_for_lesson("verified_success")).proposal
            assert left is not None and right is not None
            assert left.proposal_fingerprint == right.proposal_fingerprint
            assert len(left.proposal_fingerprint) == 64
    elif slot == 5:
        with service_context() as service:
            proposal = service.evaluate(candidate_for_lesson("verified_success")).proposal
            assert proposal is not None
            names = {field.name for field in fields(CognitiveTrustedExperienceProposal)}
            for forbidden in (
                "turn_id", "request_id", "conversation_id", "project_id",
                "prompt", "response", "context", "memory", "knowledge",
                "chain_of_thought",
            ):
                assert forbidden not in names
    elif slot == 6:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            assert record.state == "PENDING_REVIEW"
            assert record.current_revision == 1
            history = service.history(record.id)
            assert [item.event_type for item in history.items] == ["PROPOSED"]
            assert history.items[0].actor == "SYSTEM"
    elif slot == 7:
        lesson = ("bounded_insufficiency", "critic_exhausted", "invalid_cognition")[variant % 3]
        with service_context() as service:
            assert service.capture_candidate(candidate_for_lesson(lesson)) is None
            assert service.list(None, 1, 25).total == 0
    elif slot == 8:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            trusted = service.approve(record.id, 1, f"approve {variant}")
            assert trusted.state == "TRUSTED"
            assert trusted.current_revision == 2
            assert [e.event_type for e in service.history(record.id).items] == [
                "PROPOSED", "APPROVED"
            ]
    elif slot == 9:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            rejected = service.reject(record.id, 1, f"reject {variant}")
            assert rejected.state == "REJECTED"
            assert rejected.current_revision == 2
    elif slot == 10:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            trusted = service.approve(record.id, 1, "owner approved")
            revoked = service.revoke(trusted.id, 2, f"revoke {variant}")
            assert revoked.state == "REVOKED"
            assert revoked.current_revision == 3
            assert [e.event_type for e in service.history(record.id).items] == [
                "PROPOSED", "APPROVED", "REVOKED"
            ]
    elif slot == 11:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            service.approve(record.id, 1, "owner approved")
            with pytest.raises(TrustedExperienceConflictError):
                service.approve(record.id, 1, "stale")
    elif slot == 12:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            with pytest.raises(TrustedExperienceConflictError):
                service.revoke(record.id, 1, "not trusted")
    elif slot == 13:
        engine = create_engine("sqlite:///:memory:")
        TrustedExperienceRecord.__table__.create(engine)
        TrustedExperienceEventRecord.__table__.create(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        personal_session = Session()
        company_session = Session()
        try:
            personal = TrustedExperienceLifecycleService(
                TrustedExperienceRepository(
                    personal_session,
                    WorkspaceScope(workspace_id=WorkspaceId.PERSONAL),
                )
            )
            company = TrustedExperienceLifecycleService(
                TrustedExperienceRepository(
                    company_session,
                    WorkspaceScope(workspace_id=WorkspaceId.COMPANY),
                )
            )
            record = personal.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            with pytest.raises(TrustedExperienceNotFoundError):
                company.get(record.id)
        finally:
            personal_session.close()
            company_session.close()
            engine.dispose()
    elif slot == 14:
        with service_context() as service:
            first = service.capture_candidate(candidate_for_lesson("verified_success"))
            second = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert first is not None and second is not None
            service.approve(first.id, 1, "approve")
            service.reject(second.id, 1, "reject")
            assert service.diagnostic_counts() == {
                "PENDING_REVIEW": 0,
                "TRUSTED": 1,
                "REJECTED": 1,
                "REVOKED": 0,
            }
    else:
        with service_context() as service:
            record = service.capture_candidate(candidate_for_lesson("verified_success"))
            assert record is not None
            service.approve(record.id, 1, "approve")
            service.revoke(record.id, 2, "revoke")
            history = service.history(record.id)
            assert [item.sequence for item in history.items] == [1, 2, 3]
            assert [item.actor for item in history.items] == [
                "SYSTEM", "OWNER", "OWNER"
            ]


@pytest.mark.parametrize("case", range(1, 97), ids=[f"F{i:02d}" for i in range(1, 97)])
def test_d147_functional_matrix(case: int) -> None:
    run_case(case)
