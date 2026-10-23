from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.governed_execution_experience_retrieval import (
    D188_MAX_EVIDENCE,
    D188_SELECTION_POLICY,
    TrustedExecutionExperienceRetrievalQuery,
)
from app.contracts.governed_execution_experience_trust import (
    D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION,
    compute_governed_execution_experience_trust_promotion_fingerprint,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.models.trusted_execution_experience import (
    TrustedExecutionExperienceRecord,
)
from app.repositories.trusted_execution_experiences import (
    TrustedExecutionExperienceRepository,
)
from app.services.trusted_execution_experience_retrieval import (
    TrustedExecutionExperienceRetrievalService,
)

BASE_TIME = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def query(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    target_kind: str = "tool",
    capability_id: str = "capability.read",
    adapter_id: str = "adapter-a",
    operation: str = "read",
    effect: str = "read",
    risk_class: str = "R0",
) -> TrustedExecutionExperienceRetrievalQuery:
    return TrustedExecutionExperienceRetrievalQuery(
        workspace_id=workspace_id,
        target_kind=target_kind,
        capability_id=capability_id,
        adapter_id=adapter_id,
        operation=operation,
        effect=effect,
        risk_class=risk_class,
    )


def add_record(
    session,
    number: int,
    *,
    workspace: str = "personal",
    state: str = "TRUSTED",
    target_kind: str = "tool",
    capability_id: str = "capability.read",
    adapter_id: str = "adapter-a",
    operation: str = "read",
    effect: str = "read",
    risk_class: str = "R0",
    updated_seconds: int = 0,
    fixed_updated_at: datetime | None = None,
) -> TrustedExecutionExperienceRecord:
    workspace_id = WorkspaceId(workspace)
    conversation_id = UUID(int=1000 + number)
    source_turn_id = f"turn-{number}"
    source_artifact_digest = digest(f"artifact-{number}")
    intent_digest = digest(f"intent-{number}")
    approval_id = f"approval-{number}"
    execution_request_id = f"request-{number}"
    plan_digest = digest(f"plan-{number}")
    source_feedback_fingerprint = digest(f"feedback-{number}")
    source_candidate_fingerprint = digest(f"candidate-{number}")
    source_review_fingerprint = digest(f"review-{number}")
    source_d186_record_fingerprint = digest(f"d186-{number}")
    promotion_fingerprint = (
        compute_governed_execution_experience_trust_promotion_fingerprint(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            source_turn_id=source_turn_id,
            source_artifact_digest=source_artifact_digest,
            intent_digest=intent_digest,
            approval_id=approval_id,
            execution_request_id=execution_request_id,
            plan_digest=plan_digest,
            source_feedback_fingerprint=source_feedback_fingerprint,
            source_candidate_fingerprint=source_candidate_fingerprint,
            source_review_fingerprint=source_review_fingerprint,
            source_d186_record_fingerprint=source_d186_record_fingerprint,
            target_kind=target_kind,
            capability_id=capability_id,
            adapter_id=adapter_id,
            operation=operation,
            effect=effect,
            risk_class=risk_class,
            source_classification="execution_succeeded",
            experience_outcome_class="success",
            experience_lesson_code="authorized_execution_succeeded",
            review_reason_code="authorized_execution_succeeded",
        )
    )
    record = TrustedExecutionExperienceRecord(
        id=str(UUID(int=number)),
        workspace_id=workspace,
        source_review_id=str(UUID(int=2000 + number)),
        conversation_id=str(conversation_id),
        source_turn_id=source_turn_id,
        source_artifact_digest=source_artifact_digest,
        intent_digest=intent_digest,
        approval_id=approval_id,
        execution_request_id=execution_request_id,
        plan_digest=plan_digest,
        source_feedback_fingerprint=source_feedback_fingerprint,
        source_candidate_fingerprint=source_candidate_fingerprint,
        source_review_fingerprint=source_review_fingerprint,
        source_d186_record_fingerprint=source_d186_record_fingerprint,
        target_kind=target_kind,
        capability_id=capability_id,
        adapter_id=adapter_id,
        operation=operation,
        effect=effect,
        risk_class=risk_class,
        source_classification="execution_succeeded",
        experience_outcome_class="success",
        experience_lesson_code="authorized_execution_succeeded",
        review_reason_code="authorized_execution_succeeded",
        promotion_fingerprint=promotion_fingerprint,
        contract_version=(
            D187_GOVERNED_EXECUTION_EXPERIENCE_TRUST_CONTRACT_VERSION
        ),
        state=state,
        current_revision=1 if state == "TRUSTED" else 2,
        created_at=BASE_TIME,
        updated_at=(
            fixed_updated_at
            if fixed_updated_at is not None
            else BASE_TIME + timedelta(seconds=updated_seconds)
        ),
    )
    session.add(record)
    session.flush()
    return record


@contextmanager
def service_context(
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    repository = TrustedExecutionExperienceRepository(
        session,
        WorkspaceScope(workspace_id=workspace_id),
    )
    service = TrustedExecutionExperienceRetrievalService(repository)
    try:
        yield session, repository, service
    finally:
        session.close()
        engine.dispose()


def ids(result) -> list[int]:
    return [
        item.trusted_execution_experience_id.int
        for item in result.evidence
    ]


def test_d188_empty_retrieval_is_bounded_and_deterministic():
    with service_context() as (_session, _repository, service):
        result = service.retrieve(query())
        assert result.evidence == ()
        assert result.selected_count == 0
        assert result.truncated is False
        assert result.max_evidence == 16
        assert result.selection_policy == D188_SELECTION_POLICY
        assert len(result.evidence_set_fingerprint) == 64


def test_d188_only_current_trusted_root_is_retrievable():
    with service_context() as (session, _repository, service):
        add_record(session, 1, state="TRUSTED")
        add_record(session, 2, state="REVOKED")
        session.commit()
        assert ids(service.retrieve(query())) == [1]


@pytest.mark.parametrize(
    ("field_name", "different"),
    (
        ("target_kind", "module"),
        ("capability_id", "different.capability"),
        ("effect", "none"),
    ),
)
def test_d188_primary_match_is_exact(field_name: str, different: str):
    with service_context() as (session, _repository, service):
        add_record(session, 1, **{field_name: different})
        add_record(session, 2)
        session.commit()
        assert ids(service.retrieve(query())) == [2]


def test_d188_workspace_isolation_is_exact():
    with service_context() as (session, _repository, service):
        add_record(session, 1, workspace="personal")
        add_record(session, 2, workspace="company")
        session.commit()
        assert ids(service.retrieve(query())) == [1]

    with service_context(WorkspaceId.PERSONAL) as (
        _session,
        _repository,
        service,
    ):
        with pytest.raises(ValueError, match="workspace_mismatch"):
            service.retrieve(query(workspace_id=WorkspaceId.COMPANY))


def test_d188_frozen_relevance_tiers_then_time_then_id():
    with service_context() as (session, _repository, service):
        add_record(
            session, 4, adapter_id="other", operation="other",
            updated_seconds=400,
        )
        add_record(
            session, 3, adapter_id="adapter-a", operation="other",
            updated_seconds=300,
        )
        add_record(
            session, 2, adapter_id="other", operation="read",
            updated_seconds=200,
        )
        add_record(
            session, 1, adapter_id="adapter-a", operation="read",
            updated_seconds=100,
        )
        session.commit()
        assert ids(service.retrieve(query())) == [1, 2, 3, 4]

        moment = BASE_TIME + timedelta(seconds=999)
        add_record(session, 6, fixed_updated_at=moment)
        add_record(session, 5, fixed_updated_at=moment)
        session.commit()
        assert ids(service.retrieve(query()))[:2] == [5, 6]


def test_d188_bounded_selection_uses_fixed_limit():
    with service_context() as (session, _repository, service):
        for number in range(1, 18):
            add_record(session, number, updated_seconds=number)
        session.commit()
        result = service.retrieve(query())
        assert result.selected_count == D188_MAX_EVIDENCE == 16
        assert result.truncated is True
        assert ids(result) == list(range(17, 1, -1))


def test_d188_rejects_non_r0_or_write_query_before_repository_use():
    for kwargs in (
        {"risk_class": "R1"},
        {"effect": "write"},
        {"target_kind": "external"},
    ):
        with pytest.raises(ValueError):
            query(**kwargs)


def test_d188_tampered_promotion_fingerprint_fails_closed():
    with service_context() as (session, _repository, service):
        record = add_record(session, 1)
        session.commit()
        record.promotion_fingerprint = "0" * 64
        session.commit()
        with pytest.raises(
            ValueError,
            match="trusted_execution_experience_retrieval_evidence_invalid",
        ):
            service.retrieve(query())
