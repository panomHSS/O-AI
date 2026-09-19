from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.context_provenance import SystemContextSnapshotClock
from app.contracts.context_resolution import Utf8ByteBudgetCounter
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.session import create_database_engine, initialize_test_database
from app.models.context_snapshot import ContextSnapshotRecord
from app.models.message import Message
from app.repositories.context_snapshots import (
    ContextSnapshotPersistenceError,
    ContextSnapshotRepository,
)
from app.repositories.conversations import ConversationRepository
from app.services.chat import ChatService
from app.services.context_chat import build_context_chat_budget_policy
from app.services.context_provenance_sources import (
    ConversationProvenanceSource,
    KnowledgeProvenanceSource,
    MemoryProvenanceSource,
    ProjectProvenanceSource,
)
from app.services.context_resolver import ContextResolutionError, ContextResolver
from app.services.context_snapshot import ContextSnapshotService
from app.services.context_sources import ConversationContextSource
from app.services.conversations import ConversationService
from app.services.project_context import ProjectContextUnavailableError


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


class EmptySource:
    def candidates(self, request, candidate_limit):
        del request, candidate_limit
        return ()


class RecordingAdapter:
    adapter_id = "test.adapter"
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return AIResult(content="context-aware reply")


class FailingResolver:
    def resolve(self, request):
        del request
        raise ContextResolutionError("context_knowledge_unavailable")


class FailingSnapshotRepository:
    def add_snapshot(self, message, snapshot):
        del message, snapshot
        raise ContextSnapshotPersistenceError(
            "context_snapshot_persistence_failed"
        )


@pytest.fixture
def session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    initialize_test_database(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with SessionLocal() as value:
        yield value
    engine.dispose()


def _service(
    session: Session,
    *,
    resolver=None,
    snapshot_repository=None,
) -> ConversationService:
    repository = ConversationRepository(session, PERSONAL)
    empty = EmptySource()
    actual_resolver = resolver or ContextResolver(
        conversation_source=ConversationContextSource(repository),
        project_source=empty,
        memory_source=empty,
        knowledge_source=empty,
        policy=build_context_chat_budget_policy(
            conversation_message_limit=20,
            memory_max_items=8,
        ),
        counter=Utf8ByteBudgetCounter(),
    )
    snapshot_service = ContextSnapshotService(
        conversation_source=ConversationProvenanceSource(session, PERSONAL),
        project_source=ProjectProvenanceSource(session, PERSONAL),
        memory_source=MemoryProvenanceSource(session, PERSONAL),
        knowledge_source=KnowledgeProvenanceSource(session, PERSONAL),
        clock=SystemContextSnapshotClock(),
    )
    return ConversationService(
        repository=repository,
        chat_service=ChatService(provider=object()),  # type: ignore[arg-type]
        context_message_limit=20,
        context_resolver=actual_resolver,
        context_snapshot_service=snapshot_service,
        context_snapshot_repository=(
            snapshot_repository
            or ContextSnapshotRepository(session, PERSONAL)
        ),
    )


def test_current_user_message_is_not_selected_as_same_turn_history(
    session: Session,
) -> None:
    repository = ConversationRepository(session, PERSONAL)
    conversation = repository.create("Existing")
    repository.add_message(conversation, "user", "prior user")
    repository.add_message(conversation, "assistant", "prior assistant")
    repository.commit()

    adapter = RecordingAdapter()
    service = _service(session)
    result = service.send_context_message(
        "CURRENT UNIQUE MESSAGE",
        UUID(conversation.id),
        ai_adapter=adapter,
    )

    assert result.reply == "context-aware reply"
    assert len(adapter.requests) == 1
    provider_input = adapter.requests[0].content
    assert "prior user" in provider_input
    assert "prior assistant" in provider_input
    assert provider_input.count("CURRENT UNIQUE MESSAGE") == 1
    assert "Conversation context:" not in provider_input
    assert "PERSONAL MEMORY SAFETY INSTRUCTIONS" not in provider_input
    assert "OWNER-CONTROLLED PROJECT CONTEXT" not in provider_input

    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at, Message.id)
    ).all()
    assert [item.role for item in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    stored = ContextSnapshotRepository(
        session,
        PERSONAL,
    ).get_for_message(messages[-1].id)
    assert stored is not None
    assert [item.item.source.source_id for item in stored.items] == [
        messages[0].id,
        messages[1].id,
    ]


def test_new_conversation_uses_empty_l1_then_persists_empty_snapshot(
    session: Session,
) -> None:
    adapter = RecordingAdapter()
    service = _service(session)
    result = service.send_context_message(
        "first turn",
        ai_adapter=adapter,
    )

    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [item.role for item in messages] == ["user", "assistant"]
    assert len(adapter.requests) == 1
    assert adapter.requests[0].content.count("first turn") == 1
    snapshot = ContextSnapshotRepository(
        session,
        PERSONAL,
    ).get_for_message(messages[-1].id)
    assert snapshot is not None
    assert snapshot.items == ()
    assert result.memories_used == ()


def test_context_preparation_failure_rolls_back_new_turn_and_skips_provider(
    session: Session,
) -> None:
    adapter = RecordingAdapter()
    service = _service(session, resolver=FailingResolver())

    with pytest.raises(
        ContextResolutionError,
        match="context_knowledge_unavailable",
    ):
        service.send_context_message(
            "must not persist",
            ai_adapter=adapter,
        )

    assert adapter.requests == []
    assert session.scalar(select(func.count(Message.id))) == 0


def test_provider_failure_keeps_user_but_no_assistant_or_snapshot(
    session: Session,
) -> None:
    adapter = RecordingAdapter(RuntimeError("provider failed"))
    service = _service(session)

    with pytest.raises(RuntimeError, match="provider failed"):
        service.send_context_message(
            "persist user",
            ai_adapter=adapter,
        )

    assert len(adapter.requests) == 1
    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [(item.role, item.content) for item in messages] == [
        ("user", "persist user")
    ]
    assert session.scalar(
        select(func.count(ContextSnapshotRecord.id))
    ) == 0


def test_completion_persistence_failure_never_retries_provider(
    session: Session,
) -> None:
    adapter = RecordingAdapter()
    service = _service(
        session,
        snapshot_repository=FailingSnapshotRepository(),
    )

    with pytest.raises(
        ContextSnapshotPersistenceError,
        match="context_snapshot_persistence_failed",
    ):
        service.send_context_message(
            "one provider call",
            ai_adapter=adapter,
        )

    assert len(adapter.requests) == 1
    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [(item.role, item.content) for item in messages] == [
        ("user", "one provider call")
    ]
    assert session.scalar(
        select(func.count(ContextSnapshotRecord.id))
    ) == 0


class FailingProjectResolver:
    def resolve(self, request):
        del request
        raise ContextResolutionError(
            "context_project_unavailable"
        )


def test_project_context_unavailable_preserves_existing_safe_domain_error(
    session: Session,
) -> None:
    adapter = RecordingAdapter()
    service = _service(
        session,
        resolver=FailingProjectResolver(),
    )

    with pytest.raises(
        ProjectContextUnavailableError,
        match="Project context is unavailable.",
    ):
        service.send_context_message(
            "status",
            ai_adapter=adapter,
        )

    assert adapter.requests == []
    assert session.scalar(
        select(func.count(Message.id))
    ) == 0
