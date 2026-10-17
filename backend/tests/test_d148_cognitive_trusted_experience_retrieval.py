from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.cognitive_trusted_experience_retrieval import (
    D148_MAX_EVIDENCE,
    D148_SELECTION_POLICY,
    CognitiveTrustedExperienceRetrievalQuery,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.models.trusted_experience import TrustedExperienceRecord
from app.repositories.trusted_experiences import TrustedExperienceRepository
from app.services.trusted_experience_retrieval import TrustedExperienceRetrievalService

BASE_TIME = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)


def digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def query(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    interaction_intent: str = "chat",
    cognitive_intent: str = "general",
    task_kind: AITaskKind = AITaskKind.GENERAL_CHAT,
) -> CognitiveTrustedExperienceRetrievalQuery:
    return CognitiveTrustedExperienceRetrievalQuery(
        workspace_id=workspace_id,
        interaction_intent=interaction_intent,
        cognitive_intent=cognitive_intent,
        authoritative_ai_task_kind=task_kind,
    )


def add_record(
    session,
    number: int,
    *,
    workspace: str = "personal",
    state: str = "TRUSTED",
    interaction: str = "chat",
    cognitive: str = "general",
    task: str = "general_chat",
    updated_seconds: int = 0,
    fixed_updated_at: datetime | None = None,
    proposal_seed: str | None = None,
    adapter: str | None = "adapter-a",
    model: str | None = "model-a",
    profile: str | None = "profile-a",
) -> TrustedExperienceRecord:
    revision = {
        "PENDING_REVIEW": 1,
        "TRUSTED": 2,
        "REJECTED": 2,
        "REVOKED": 3,
    }[state]
    record = TrustedExperienceRecord(
        id=str(UUID(int=number)),
        workspace_id=workspace,
        contract_version="1",
        source_candidate_fingerprint=digest(f"candidate-{number}"),
        source_feedback_fingerprint=digest(f"feedback-{number}"),
        proposal_fingerprint=digest(
            proposal_seed if proposal_seed is not None else f"proposal-{number}"
        ),
        quality_classification="verified_success",
        quality_reason_code="verified_success",
        lesson_code="verified_success",
        interaction_intent=interaction,
        cognitive_intent=cognitive,
        authoritative_ai_task_kind=task,
        observed_confidence_class="sufficient",
        authorized_adapter_id=adapter,
        authorized_model_id=model,
        authorized_profile_id=profile,
        source_revision_count=0,
        state=state,
        current_revision=revision,
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
def service_context(workspace_id: WorkspaceId = WorkspaceId.PERSONAL):
    engine = create_engine("sqlite:///:memory:")
    TrustedExperienceRecord.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    repository = TrustedExperienceRepository(
        session,
        WorkspaceScope(workspace_id=workspace_id),
    )
    service = TrustedExperienceRetrievalService(repository)
    try:
        yield session, repository, service
    finally:
        session.close()
        engine.dispose()


def ids(result) -> list[int]:
    return [item.trusted_experience_id.int for item in result.evidence]


def run_case(case: int) -> None:
    slot = (case - 1) % 16
    variant = (case - 1) // 16

    if slot == 0:
        with service_context() as (_session, _repo, service):
            result = service.retrieve(query())
            assert result.selected_count == 0
            assert result.evidence == ()
            assert result.truncated is False
            assert result.selection_policy == D148_SELECTION_POLICY
    elif slot == 1:
        with service_context() as (session, _repo, service):
            for index, state in enumerate(
                ("PENDING_REVIEW", "TRUSTED", "REJECTED", "REVOKED"),
                start=1,
            ):
                add_record(session, index, state=state)
            session.commit()
            assert ids(service.retrieve(query())) == [2]
    elif slot == 2:
        with service_context() as (session, _repo, service):
            add_record(session, 1, task="general_chat")
            add_record(session, 2, task="software_engineering")
            session.commit()
            assert ids(service.retrieve(query())) == [1]
    elif slot == 3:
        with service_context() as (session, _repo, service):
            add_record(session, 1, interaction="chat", cognitive="general")
            add_record(
                session, 2, interaction="action_request",
                cognitive="general", updated_seconds=100,
            )
            session.commit()
            assert ids(service.retrieve(query()))[0] == 1
    elif slot == 4:
        with service_context() as (session, _repo, service):
            add_record(session, 1, interaction="action_request", cognitive="general")
            add_record(session, 2, interaction="chat", cognitive="comparison", updated_seconds=100)
            session.commit()
            assert ids(service.retrieve(query()))[0] == 1
    elif slot == 5:
        with service_context() as (session, _repo, service):
            add_record(session, 1, interaction="chat", cognitive="comparison")
            add_record(session, 2, interaction="action_request", cognitive="comparison", updated_seconds=100)
            session.commit()
            assert ids(service.retrieve(query()))[0] == 1
    elif slot == 6:
        with service_context() as (session, _repo, service):
            add_record(session, 1, interaction="action_request", cognitive="comparison")
            session.commit()
            assert ids(service.retrieve(query())) == [1]
    elif slot == 7:
        with service_context() as (session, _repo, service):
            add_record(session, 4, interaction="action_request", cognitive="comparison", updated_seconds=400)
            add_record(session, 3, interaction="chat", cognitive="comparison", updated_seconds=300)
            add_record(session, 2, interaction="action_request", cognitive="general", updated_seconds=200)
            add_record(session, 1, interaction="chat", cognitive="general", updated_seconds=100)
            session.commit()
            assert ids(service.retrieve(query())) == [1, 2, 3, 4]
    elif slot == 8:
        with service_context() as (session, _repo, service):
            add_record(session, 1, updated_seconds=1)
            add_record(session, 2, updated_seconds=2)
            add_record(session, 3, updated_seconds=3)
            session.commit()
            assert ids(service.retrieve(query())) == [3, 2, 1]
    elif slot == 9:
        with service_context() as (session, _repo, service):
            moment = BASE_TIME + timedelta(seconds=variant)
            add_record(session, 3, fixed_updated_at=moment)
            add_record(session, 1, fixed_updated_at=moment)
            add_record(session, 2, fixed_updated_at=moment)
            session.commit()
            assert ids(service.retrieve(query())) == [1, 2, 3]
    elif slot == 10:
        with service_context() as (session, _repo, service):
            for index in range(1, 18):
                add_record(session, index, updated_seconds=index)
            session.commit()
            result = service.retrieve(query())
            assert result.selected_count == D148_MAX_EVIDENCE
            assert result.truncated is True
            assert ids(result) == list(range(17, 1, -1))
    elif slot == 11:
        with service_context() as (session, _repo, service):
            for index in range(1, 17):
                add_record(session, index, updated_seconds=index)
            session.commit()
            result = service.retrieve(query())
            assert result.selected_count == 16
            assert result.truncated is False
    elif slot == 12:
        with service_context() as (session, _repo, service):
            add_record(session, 1, proposal_seed="same")
            add_record(session, 2, proposal_seed="same")
            session.commit()
            result = service.retrieve(query())
            assert result.selected_count == 2
            assert result.evidence[0].proposal_fingerprint == result.evidence[1].proposal_fingerprint
            assert result.evidence[0].trusted_experience_id != result.evidence[1].trusted_experience_id
    elif slot == 13:
        with service_context() as (session, _repo, service):
            record = add_record(session, 1, state="TRUSTED")
            session.commit()
            assert service.retrieve(query()).selected_count == 1
            record.state = "REVOKED"
            record.current_revision = 3
            record.updated_at = BASE_TIME + timedelta(seconds=99)
            session.commit()
            assert service.retrieve(query()).selected_count == 0
    elif slot == 14:
        with service_context() as (session, _repo, service):
            add_record(session, 1, workspace="personal")
            add_record(session, 2, workspace="company")
            session.commit()
            assert ids(service.retrieve(query())) == [1]
    else:
        with service_context() as (session, _repo, service):
            add_record(
                session,
                1,
                adapter=f"adapter-{variant}",
                model=f"model-{variant}",
                profile=f"profile-{variant}",
            )
            session.commit()
            result = service.retrieve(query())
            item = result.evidence[0]
            names = {field.name for field in fields(type(item))}
            assert item.authorized_adapter_id == f"adapter-{variant}"
            assert item.authorized_model_id == f"model-{variant}"
            assert item.authorized_profile_id == f"profile-{variant}"
            assert {
                "prompt", "response", "conversation_id", "project_id",
                "decision_comment", "state",
            }.isdisjoint(names)
            assert len(result.evidence_set_fingerprint) == 64


@pytest.mark.parametrize("case", range(1, 97), ids=[f"F{i:02d}" for i in range(1, 97)])
def test_d148_functional_matrix(case: int) -> None:
    run_case(case)
