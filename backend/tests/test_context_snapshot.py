from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.contracts.context import (
    ContextBundle,
    ContextItem,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_provenance import (
    ContextSnapshot,
    compute_context_snapshot_digest,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.db.base import Base
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.memory import Memory
from app.models.memory_version import MemoryVersion
from app.models.message import Message
from app.models.project import Project
from app.services.context_provenance_sources import (
    ContextProvenanceSourceError,
    ContextSourceObservation,
    ConversationProvenanceSource,
    KnowledgeProvenanceSource,
    MemoryProvenanceSource,
    ProjectProvenanceSource,
)
from app.services.context_snapshot import ContextSnapshotError, ContextSnapshotService
from app.services.context_sources import (
    conversation_context_projection,
    knowledge_context_projection,
    memory_context_projection,
    project_context_projection,
)
from app.services.memory_resolver import decode_memory_context_value
from app.services.project_context import (
    ProjectContext,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 19, 11, 0, tzinfo=UTC)


class FixedClock:
    def now_utc(self) -> datetime:
        return NOW


class FakeSource:
    def __init__(
        self,
        observation: ContextSourceObservation | None = None,
        *,
        error: str | None = None,
    ) -> None:
        self.observation = observation
        self.error = error
        self.calls = 0

    def observe(self, item: ContextItem) -> ContextSourceObservation:
        self.calls += 1
        if self.error is not None:
            raise ContextProvenanceSourceError(self.error)
        if self.observation is None:
            raise AssertionError("unexpected source call")
        return self.observation


def _item(
    layer: ContextLayer,
    source_id: str,
    text: str,
    label: str | None,
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextItem:
    return ContextItem(
        source=ContextSourceRef(
            workspace_id=workspace_id,
            layer=layer,
            source_id=source_id,
        ),
        text=text,
        label=label,
    )


def _observation(
    item: ContextItem,
    *,
    text: str | None = None,
    label: str | None | object = ...,
    parent_source_id: str | None = None,
    version_ref: str | None = None,
    source_locator: str | None = None,
    source_timestamp: datetime | None = NOW,
) -> ContextSourceObservation:
    actual_label = item.label if label is ... else label
    return ContextSourceObservation(
        source=item.source,
        text=item.text if text is None else text,
        label=actual_label,  # type: ignore[arg-type]
        parent_source_id=parent_source_id,
        version_ref=version_ref,
        source_locator=source_locator,
        source_timestamp=source_timestamp,
    )


def _service(
    *,
    conversation: FakeSource | None = None,
    project: FakeSource | None = None,
    memory: FakeSource | None = None,
    knowledge: FakeSource | None = None,
    clock: object | None = None,
) -> ContextSnapshotService:
    return ContextSnapshotService(
        conversation_source=conversation or FakeSource(),
        project_source=project or FakeSource(),
        memory_source=memory or FakeSource(),
        knowledge_source=knowledge or FakeSource(),
        clock=clock or FixedClock(),  # type: ignore[arg-type]
    )


def test_snapshot_capture_preserves_bundle_order_and_provenance() -> None:
    conversation_item = _item(
        ContextLayer.CONVERSATION,
        "message-1",
        '{"content":"hello","role":"user"}',
        "conversation_user",
    )
    project_item = _item(
        ContextLayer.PROJECT,
        "project-1",
        '{"current_revision":2,"objective":"ship","status":"ACTIVE","title":"Alpha"}',
        "project_current",
    )
    memory_item = _item(
        ContextLayer.MEMORY,
        "version-1",
        '{"key":"alpha","value":"yes","value_type":"STRING"}',
        "memory",
    )
    knowledge_item = _item(
        ContextLayer.KNOWLEDGE,
        "chunk-1",
        "knowledge text",
        "knowledge",
    )

    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=(
            conversation_item,
            project_item,
            memory_item,
            knowledge_item,
        ),
    )
    service = _service(
        conversation=FakeSource(
            _observation(
                conversation_item,
                parent_source_id="conversation-1",
                source_timestamp=NOW - timedelta(minutes=4),
            )
        ),
        project=FakeSource(
            _observation(
                project_item,
                version_ref="2",
                source_timestamp=NOW - timedelta(minutes=3),
            )
        ),
        memory=FakeSource(
            _observation(
                memory_item,
                parent_source_id="memory-1",
                version_ref="1",
                source_timestamp=NOW - timedelta(minutes=2),
            )
        ),
        knowledge=FakeSource(
            _observation(
                knowledge_item,
                parent_source_id="document-1",
                version_ref="a" * 64,
                source_locator="page:1",
                source_timestamp=NOW - timedelta(minutes=1),
            )
        ),
    )

    snapshot = service.capture(bundle)

    assert isinstance(snapshot, ContextSnapshot)
    assert snapshot.captured_at == NOW
    assert [entry.item.source.layer for entry in snapshot.items] == [
        ContextLayer.CONVERSATION,
        ContextLayer.PROJECT,
        ContextLayer.MEMORY,
        ContextLayer.KNOWLEDGE,
    ]
    assert snapshot.items[0].provenance.parent_source_id == "conversation-1"
    assert snapshot.items[1].provenance.version_ref == "2"
    assert snapshot.items[2].provenance.parent_source_id == "memory-1"
    assert snapshot.items[3].provenance.source_locator == "page:1"
    assert snapshot.snapshot_digest == compute_context_snapshot_digest(
        workspace_scope=snapshot.workspace_scope,
        captured_at=snapshot.captured_at,
        items=snapshot.items,
    )


def test_empty_bundle_captures_without_source_calls() -> None:
    conversation = FakeSource()
    project = FakeSource()
    memory = FakeSource()
    knowledge = FakeSource()
    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.COMPANY),
        items=(),
    )

    snapshot = _service(
        conversation=conversation,
        project=project,
        memory=memory,
        knowledge=knowledge,
    ).capture(bundle)

    assert snapshot.items == ()
    assert conversation.calls == 0
    assert project.calls == 0
    assert memory.calls == 0
    assert knowledge.calls == 0


@pytest.mark.parametrize(
    ("changed_text", "changed_label"),
    (
        ("changed", ...),
        (None, "other"),
    ),
)
def test_verify_before_freeze_rejects_changed_projection(
    changed_text: str | None,
    changed_label: str | object,
) -> None:
    item = _item(
        ContextLayer.KNOWLEDGE,
        "chunk-1",
        "original",
        "knowledge",
    )
    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=(item,),
    )
    source = FakeSource(
        _observation(
            item,
            text=changed_text,
            label=changed_label,
        )
    )

    with pytest.raises(
        ContextSnapshotError,
        match="context_snapshot_source_changed",
    ):
        _service(knowledge=source).capture(bundle)


def test_verify_before_freeze_rejects_source_substitution() -> None:
    item = _item(
        ContextLayer.KNOWLEDGE,
        "chunk-1",
        "original",
        "knowledge",
    )
    other = _item(
        ContextLayer.KNOWLEDGE,
        "chunk-2",
        "original",
        "knowledge",
    )
    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=(item,),
    )

    with pytest.raises(
        ContextSnapshotError,
        match="context_snapshot_source_mismatch",
    ):
        _service(
            knowledge=FakeSource(_observation(other))
        ).capture(bundle)


def test_source_failure_is_bounded_and_stops_capture() -> None:
    project_item = _item(
        ContextLayer.PROJECT,
        "project-1",
        "project",
        "project_current",
    )
    memory_item = _item(
        ContextLayer.MEMORY,
        "memory-version-1",
        "memory",
        "memory",
    )
    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=(project_item, memory_item),
    )
    project = FakeSource(error="context_snapshot_source_unavailable")
    memory = FakeSource(_observation(memory_item))

    with pytest.raises(
        ContextSnapshotError,
        match="context_snapshot_source_unavailable",
    ):
        _service(
            project=project,
            memory=memory,
        ).capture(bundle)

    assert project.calls == 1
    assert memory.calls == 0


class BadClock:
    def now_utc(self) -> datetime:
        return datetime(2026, 9, 19, 18, 0)


def test_snapshot_capture_requires_utc_clock() -> None:
    bundle = ContextBundle(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        items=(),
    )

    with pytest.raises(
        ContextSnapshotError,
        match="context_snapshot_timestamp_invalid",
    ):
        _service(clock=BadClock()).capture(bundle)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value
    engine.dispose()


def _scope(
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> WorkspaceScope:
    return WorkspaceScope(workspace_id)


def test_conversation_provenance_reobserves_exact_workspace(
    session: Session,
) -> None:
    conversation = Conversation(
        id="conversation-personal",
        title="Personal",
        workspace_id="personal",
    )
    message = Message(
        id="message-personal",
        conversation_id=conversation.id,
        role="user",
        content="hello",
        created_at=NOW - timedelta(hours=1),
    )
    other_conversation = Conversation(
        id="conversation-company",
        title="Company",
        workspace_id="company",
    )
    other_message = Message(
        id="message-company",
        conversation_id=other_conversation.id,
        role="user",
        content="company",
        created_at=NOW,
    )
    session.add_all(
        [conversation, message, other_conversation, other_message]
    )
    session.flush()

    text, label = conversation_context_projection(
        message.role,
        message.content,
    )
    item = _item(
        ContextLayer.CONVERSATION,
        message.id,
        text,
        label,
    )
    observation = ConversationProvenanceSource(
        session,
        _scope(),
    ).observe(item)

    assert observation.parent_source_id == conversation.id
    assert observation.text == text
    assert observation.label == label
    assert observation.source_timestamp.utcoffset() == timedelta(0)

    company_text, company_label = conversation_context_projection(
        other_message.role,
        other_message.content,
    )
    company_item = _item(
        ContextLayer.CONVERSATION,
        other_message.id,
        company_text,
        company_label,
    )
    with pytest.raises(
        ContextProvenanceSourceError,
        match="context_snapshot_source_unavailable",
    ):
        ConversationProvenanceSource(
            session,
            _scope(),
        ).observe(company_item)


def test_project_provenance_reuses_d95_projection_and_revision(
    session: Session,
) -> None:
    project = Project(
        id="project-1",
        title="Alpha",
        objective="Ship safely",
        status="ACTIVE",
        current_summary="Current",
        next_action="Test",
        current_revision=3,
        workspace_id="personal",
        updated_at=NOW - timedelta(hours=2),
    )
    session.add(project)
    session.flush()

    context = ProjectContext(
        title="Alpha",
        objective="Ship safely",
        status="ACTIVE",
        current_summary="Current",
        next_action="Test",
        current_revision=3,
    )
    item = _item(
        ContextLayer.PROJECT,
        project.id,
        project_context_projection(context),
        "project_current",
    )
    observation = ProjectProvenanceSource(
        session,
        _scope(),
    ).observe(item)

    assert observation.text == item.text
    assert observation.version_ref == "3"
    assert observation.source_timestamp.utcoffset() == timedelta(0)


def test_memory_provenance_requires_still_active_confirmed_version(
    session: Session,
) -> None:
    memory = Memory(
        id="memory-1",
        key="alpha.project",
        value='"yes"',
        value_type="STRING",
        state="CONFIRMED",
        current_version=1,
        workspace_id="personal",
    )
    session.add(memory)
    session.flush()

    version = MemoryVersion(
        id="version-1",
        memory_id=memory.id,
        version=1,
        key=memory.key,
        value=memory.value,
        value_type=memory.value_type,
        state="CONFIRMED",
        change_reason="initial",
        created_at=NOW - timedelta(hours=3),
    )
    session.add(version)
    session.flush()
    memory.active_version_id = version.id
    session.flush()

    value = decode_memory_context_value(version.value)
    assert value is not None
    item = _item(
        ContextLayer.MEMORY,
        version.id,
        memory_context_projection(
            key=version.key,
            value=value,
            value_type=version.value_type,
        ),
        "memory",
    )
    source = MemoryProvenanceSource(session, _scope())
    observation = source.observe(item)

    assert observation.parent_source_id == memory.id
    assert observation.version_ref == "1"
    assert observation.text == item.text

    replacement = MemoryVersion(
        id="version-2",
        memory_id=memory.id,
        version=2,
        key=memory.key,
        value='"no"',
        value_type="STRING",
        state="CONFIRMED",
        change_reason="replace",
        created_at=NOW,
    )
    session.add(replacement)
    session.flush()
    memory.active_version_id = replacement.id
    memory.current_version = 2
    session.flush()

    with pytest.raises(
        ContextProvenanceSourceError,
        match="context_snapshot_source_unavailable",
    ):
        source.observe(item)


def test_knowledge_provenance_requires_indexed_exact_workspace_document(
    session: Session,
) -> None:
    document = Document(
        id="document-1",
        source_path="docs/alpha.txt",
        file_name="alpha.txt",
        file_extension=".txt",
        mime_type="text/plain",
        file_size=10,
        content_hash="a" * 64,
        status="indexed",
        indexed_at=NOW - timedelta(hours=4),
        workspace_id="personal",
    )
    chunk = DocumentChunk(
        id="chunk-1",
        document_id=document.id,
        chunk_index=0,
        content="knowledge text",
        source_locator="line:1",
    )
    session.add_all([document, chunk])
    session.flush()

    text, label = knowledge_context_projection(chunk.content)
    item = _item(
        ContextLayer.KNOWLEDGE,
        chunk.id,
        text,
        label,
    )
    source = KnowledgeProvenanceSource(session, _scope())
    observation = source.observe(item)

    assert observation.parent_source_id == document.id
    assert observation.version_ref == "a" * 64
    assert observation.source_locator == "line:1"
    assert observation.text == chunk.content

    document.status = "missing"
    session.flush()
    with pytest.raises(
        ContextProvenanceSourceError,
        match="context_snapshot_source_unavailable",
    ):
        source.observe(item)


def test_real_source_change_is_detected_before_freeze(
    session: Session,
) -> None:
    project = Project(
        id="project-drift",
        title="Before",
        objective="Ship",
        status="ACTIVE",
        current_revision=1,
        workspace_id="personal",
        updated_at=NOW - timedelta(minutes=5),
    )
    session.add(project)
    session.flush()

    selected_context = ProjectContext(
        title="Before",
        objective="Ship",
        status="ACTIVE",
        current_summary=None,
        next_action=None,
        current_revision=1,
    )
    selected = _item(
        ContextLayer.PROJECT,
        project.id,
        project_context_projection(selected_context),
        "project_current",
    )
    bundle = ContextBundle(
        workspace_scope=_scope(),
        items=(selected,),
    )

    project.title = "After"
    project.current_revision = 2
    project.updated_at = NOW
    session.flush()

    service = ContextSnapshotService(
        conversation_source=ConversationProvenanceSource(
            session,
            _scope(),
        ),
        project_source=ProjectProvenanceSource(
            session,
            _scope(),
        ),
        memory_source=MemoryProvenanceSource(
            session,
            _scope(),
        ),
        knowledge_source=KnowledgeProvenanceSource(
            session,
            _scope(),
        ),
        clock=FixedClock(),
    )

    with pytest.raises(
        ContextSnapshotError,
        match="context_snapshot_source_changed",
    ):
        service.capture(bundle)
