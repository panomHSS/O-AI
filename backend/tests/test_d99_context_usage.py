from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.ai import AI_ADAPTER_CONTRACT_VERSION, AIRequest, AIResult
from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.context_usage import ContextUsage
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.session import create_database_engine, initialize_test_database
from app.repositories.context_snapshots import ContextSnapshotRepository
from app.repositories.conversations import ConversationRepository
from app.schemas.context_usage import ContextUsageResponse
from app.services.chat import ChatService
from app.services.context_usage import context_usage_from_snapshot
from app.services.conversations import ConversationService
from tests.d97_context_chat_fixture import (
    build_context_aware_conversation_service,
)


UTC = timezone.utc
PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


class RecordingAdapter:
    adapter_id = "test.adapter"
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        return AIResult(content="reply")


@pytest.fixture
def session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    initialize_test_database(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with SessionLocal() as value:
        yield value
    engine.dispose()


def _snapshot(
    scope: WorkspaceScope,
    layers: tuple[ContextLayer, ...],
) -> ContextSnapshot:
    captured_at = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    items: list[ContextSnapshotItem] = []

    for index, layer in enumerate(layers, start=1):
        source = ContextSourceRef(
            workspace_id=scope.workspace_id,
            layer=layer,
            source_id=f"{layer.value}-{index}",
        )
        item = ContextItem(
            source=source,
            text=f"private-{layer.value}-{index}",
            label=layer.value,
        )
        items.append(
            ContextSnapshotItem(
                item=item,
                provenance=ContextSourceProvenance(
                    source=source,
                    content_sha256=context_text_sha256(item.text),
                ),
            )
        )

    frozen = tuple(items)
    return ContextSnapshot(
        workspace_scope=scope,
        captured_at=captured_at,
        items=frozen,
        snapshot_digest=compute_context_snapshot_digest(
            workspace_scope=scope,
            captured_at=captured_at,
            items=frozen,
        ),
    )


def test_usage_contract_requires_exact_total_and_utc() -> None:
    with pytest.raises(ValueError, match="context_usage_total_mismatch"):
        ContextUsage(
            captured_at=datetime(2026, 9, 19, 12, 0, tzinfo=UTC),
            total_items=2,
            conversation_items=1,
            project_items=0,
            memory_items=0,
            knowledge_items=0,
        )

    with pytest.raises(ValueError, match="context_usage_captured_at_invalid"):
        ContextUsage(
            captured_at=datetime(2026, 9, 19, 12, 0),
            total_items=0,
            conversation_items=0,
            project_items=0,
            memory_items=0,
            knowledge_items=0,
        )


def test_snapshot_projection_counts_only_fixed_layers() -> None:
    usage = context_usage_from_snapshot(
        _snapshot(
            PERSONAL,
            (
                ContextLayer.CONVERSATION,
                ContextLayer.CONVERSATION,
                ContextLayer.PROJECT,
                ContextLayer.MEMORY,
                ContextLayer.KNOWLEDGE,
                ContextLayer.KNOWLEDGE,
            ),
        )
    )

    assert usage.total_items == 6
    assert usage.conversation_items == 2
    assert usage.project_items == 1
    assert usage.memory_items == 1
    assert usage.knowledge_items == 2


def test_repository_distinguishes_missing_empty_and_populated_snapshot(
    session: Session,
) -> None:
    conversations = ConversationRepository(session, PERSONAL)
    conversation = conversations.create("D99")

    missing = conversations.add_message(conversation, "assistant", "pre-d97")
    empty = conversations.add_message(conversation, "assistant", "empty")
    populated = conversations.add_message(
        conversation,
        "assistant",
        "populated",
    )

    snapshots = ContextSnapshotRepository(session, PERSONAL)
    snapshots.add_snapshot(empty, _snapshot(PERSONAL, ()))
    snapshots.add_snapshot(
        populated,
        _snapshot(
            PERSONAL,
            (
                ContextLayer.CONVERSATION,
                ContextLayer.PROJECT,
                ContextLayer.KNOWLEDGE,
            ),
        ),
    )
    conversations.commit()

    assert snapshots.get_usage_for_message(missing.id) is None

    empty_usage = snapshots.get_usage_for_message(empty.id)
    assert empty_usage is not None
    assert empty_usage.total_items == 0

    populated_usage = snapshots.get_usage_for_message(populated.id)
    assert populated_usage is not None
    assert populated_usage.total_items == 3
    assert populated_usage.conversation_items == 1
    assert populated_usage.project_items == 1
    assert populated_usage.memory_items == 0
    assert populated_usage.knowledge_items == 1


def test_cross_workspace_snapshot_usage_is_not_visible(
    session: Session,
) -> None:
    conversations = ConversationRepository(session, PERSONAL)
    conversation = conversations.create("Personal only")
    assistant = conversations.add_message(conversation, "assistant", "reply")
    personal = ContextSnapshotRepository(session, PERSONAL)
    personal.add_snapshot(
        assistant,
        _snapshot(PERSONAL, (ContextLayer.KNOWLEDGE,)),
    )
    conversations.commit()

    company = ContextSnapshotRepository(session, COMPANY)
    assert company.get_usage_for_message(assistant.id) is None


def test_response_projection_exposes_counts_not_snapshot_content() -> None:
    response = ContextUsageResponse.from_usage(
        context_usage_from_snapshot(
            _snapshot(
                PERSONAL,
                (ContextLayer.MEMORY, ContextLayer.KNOWLEDGE),
            )
        )
    )
    payload = response.model_dump()

    assert set(payload) == {
        "captured_at",
        "total_items",
        "conversation_items",
        "project_items",
        "memory_items",
        "knowledge_items",
    }
    serialized = response.model_dump_json()
    assert "private-" not in serialized
    assert "source_id" not in serialized
    assert "snapshot_digest" not in serialized
    assert "content_sha256" not in serialized
    assert "source_locator" not in serialized


def test_conversation_detail_preserves_missing_vs_empty_snapshot(
    session: Session,
) -> None:
    conversations = ConversationRepository(session, PERSONAL)
    conversation = conversations.create("Restore")
    user = conversations.add_message(conversation, "user", "hello")
    legacy = conversations.add_message(conversation, "assistant", "legacy")
    empty = conversations.add_message(conversation, "assistant", "empty")
    snapshots = ContextSnapshotRepository(session, PERSONAL)
    snapshots.add_snapshot(empty, _snapshot(PERSONAL, ()))
    conversations.commit()

    service = ConversationService(
        repository=conversations,
        chat_service=ChatService(provider=object()),  # type: ignore[arg-type]
        context_message_limit=20,
        context_snapshot_repository=snapshots,
    )
    detail = service.get_conversation(UUID(conversation.id))

    by_id = {str(message.id): message for message in detail.messages}
    assert by_id[user.id].context_usage is None
    assert by_id[legacy.id].context_usage is None
    assert by_id[empty.id].context_usage is not None
    assert by_id[empty.id].context_usage.total_items == 0


def test_normal_d97_turn_returns_same_turn_context_usage(
    session: Session,
) -> None:
    adapter = RecordingAdapter()
    service = build_context_aware_conversation_service(
        session=session,
        workspace_scope=PERSONAL,
        chat_service=ChatService(provider=object()),  # type: ignore[arg-type]
        context_message_limit=20,
    )

    result = service.send_context_message(
        "first turn has empty prior Context",
        ai_adapter=adapter,
    )

    assert len(adapter.requests) == 1
    assert result.context_usage is not None
    assert result.context_usage.total_items == 0

    restored = service.get_conversation(result.conversation_id)
    assistant = restored.messages[-1]
    assert assistant.role == "assistant"
    assert assistant.context_usage is not None
    assert assistant.context_usage.total_items == 0
