from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.context import (
    ContextItem,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.core.config import get_settings
from app.db.session import (
    create_database_engine,
    initialize_test_database,
)
from app.db.verification import verify_database
from app.models.context_snapshot import (
    ContextSnapshotItemRecord,
    ContextSnapshotRecord,
)
from app.repositories.context_snapshots import (
    ContextSnapshotPersistenceError,
    ContextSnapshotRepository,
)
from app.repositories.conversations import ConversationRepository


UTC = timezone.utc
CAPTURED_AT = datetime(2026, 9, 19, 14, 0, tzinfo=UTC)
PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)
COMPANY = WorkspaceScope(WorkspaceId.COMPANY)


def _snapshot(
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
    items: tuple[ContextSnapshotItem, ...] | None = None,
) -> ContextSnapshot:
    actual_items = items or ()
    digest = compute_context_snapshot_digest(
        workspace_scope=workspace_scope,
        captured_at=CAPTURED_AT,
        items=actual_items,
    )
    return ContextSnapshot(
        workspace_scope=workspace_scope,
        captured_at=CAPTURED_AT,
        items=actual_items,
        snapshot_digest=digest,
    )


def _snapshot_item(
    *,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    layer: ContextLayer = ContextLayer.KNOWLEDGE,
    source_id: str = "chunk-1",
    text_value: str = "knowledge",
    label: str | None = "knowledge",
) -> ContextSnapshotItem:
    source = ContextSourceRef(
        workspace_id=workspace_id,
        layer=layer,
        source_id=source_id,
    )
    item = ContextItem(
        source=source,
        text=text_value,
        label=label,
    )
    provenance = ContextSourceProvenance(
        source=source,
        content_sha256=context_text_sha256(text_value),
        parent_source_id="parent-1",
        version_ref="1",
        source_locator="page:1",
        source_timestamp=CAPTURED_AT,
    )
    return ContextSnapshotItem(
        item=item,
        provenance=provenance,
    )


@pytest.fixture
def session() -> Session:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    initialize_test_database(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    with SessionLocal() as value:
        yield value
    engine.dispose()


def _assistant_message(
    session: Session,
    *,
    workspace_scope: WorkspaceScope = PERSONAL,
):
    conversations = ConversationRepository(
        session,
        workspace_scope,
    )
    conversation = conversations.create("Snapshot test")
    conversations.add_message(
        conversation,
        "user",
        "hello",
    )
    assistant = conversations.add_message(
        conversation,
        "assistant",
        "reply",
    )
    return conversations, conversation, assistant


def test_repository_round_trips_exact_d96_snapshot(
    session: Session,
) -> None:
    _, _, assistant = _assistant_message(session)
    items = (
        _snapshot_item(
            layer=ContextLayer.CONVERSATION,
            source_id="message-before",
            text_value='{"content":"before","role":"user"}',
            label="conversation_user",
        ),
        _snapshot_item(
            layer=ContextLayer.KNOWLEDGE,
            source_id="chunk-1",
            text_value="ข้อมูล",
            label="knowledge",
        ),
    )
    snapshot = _snapshot(items=items)
    repository = ContextSnapshotRepository(session, PERSONAL)

    record = repository.add_snapshot(assistant, snapshot)
    session.commit()
    session.expire_all()

    loaded = repository.get_for_message(assistant.id)

    assert record.message_id == assistant.id
    assert loaded == snapshot
    assert loaded is not None
    assert [item.item.source.layer for item in loaded.items] == [
        ContextLayer.CONVERSATION,
        ContextLayer.KNOWLEDGE,
    ]


def test_repository_persists_valid_empty_snapshot(
    session: Session,
) -> None:
    _, _, assistant = _assistant_message(session)
    repository = ContextSnapshotRepository(session, PERSONAL)
    snapshot = _snapshot()

    repository.add_snapshot(assistant, snapshot)
    session.commit()

    loaded = repository.get_for_message(assistant.id)
    assert loaded == snapshot
    assert session.scalar(
        select(func.count(ContextSnapshotItemRecord.id))
    ) == 0


def test_repository_rejects_non_assistant_attachment(
    session: Session,
) -> None:
    conversations = ConversationRepository(session, PERSONAL)
    conversation = conversations.create("User only")
    user = conversations.add_message(conversation, "user", "hello")

    with pytest.raises(
        ContextSnapshotPersistenceError,
        match="context_snapshot_assistant_required",
    ):
        ContextSnapshotRepository(
            session,
            PERSONAL,
        ).add_snapshot(user, _snapshot())


def test_repository_enforces_exact_workspace_on_write_and_read(
    session: Session,
) -> None:
    _, _, assistant = _assistant_message(session)
    personal_repository = ContextSnapshotRepository(session, PERSONAL)
    company_repository = ContextSnapshotRepository(session, COMPANY)

    with pytest.raises(
        ContextSnapshotPersistenceError,
        match="context_snapshot_workspace_mismatch",
    ):
        company_repository.add_snapshot(assistant, _snapshot())

    personal_repository.add_snapshot(assistant, _snapshot())
    session.commit()

    assert company_repository.get_for_message(assistant.id) is None
    assert personal_repository.get_for_message(assistant.id) is not None


def test_repository_rejects_second_snapshot_for_same_message(
    session: Session,
) -> None:
    _, _, assistant = _assistant_message(session)
    repository = ContextSnapshotRepository(session, PERSONAL)
    snapshot = _snapshot()

    repository.add_snapshot(assistant, snapshot)

    with pytest.raises(
        ContextSnapshotPersistenceError,
        match="context_snapshot_already_exists",
    ):
        repository.add_snapshot(assistant, snapshot)


def test_conversation_delete_cascades_snapshot_and_items(
    session: Session,
) -> None:
    conversations, conversation, assistant = _assistant_message(session)
    repository = ContextSnapshotRepository(session, PERSONAL)
    snapshot = _snapshot(
        items=(_snapshot_item(),)
    )
    repository.add_snapshot(assistant, snapshot)
    session.commit()

    conversations.delete(conversation)
    conversations.commit()

    assert session.scalar(
        select(func.count(ContextSnapshotRecord.id))
    ) == 0
    assert session.scalar(
        select(func.count(ContextSnapshotItemRecord.id))
    ) == 0


class TestD97ContextSnapshotMigration:
    D92_REVISION = "0012_workspace_persistence"
    D97_REVISION = "0013_context_snapshot_persistence"

    def setup_method(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "d97.db"
        )
        self.database_url = (
            f"sqlite:///{self.database_path.as_posix()}"
        )
        self.previous_database_url = os.environ.get(
            "OAI_DATABASE_URL"
        )
        os.environ["OAI_DATABASE_URL"] = self.database_url
        get_settings.cache_clear()
        self.engine = None

    def teardown_method(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = (
                self.previous_database_url
            )
        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def _config(self) -> Config:
        repository_root = Path(__file__).resolve().parents[2]
        return Config(str(repository_root / "alembic.ini"))

    def _upgrade(self, target: str) -> None:
        command.upgrade(self._config(), target)

    def _downgrade(self, target: str) -> None:
        command.downgrade(self._config(), target)

    def _open_engine(self) -> None:
        self.engine = create_database_engine(self.database_url)

    def _insert_conversation_and_assistant(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO conversations "
                    "(id, title, created_at, updated_at, workspace_id) "
                    "VALUES ('conversation-1', 'Test', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'personal')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO messages "
                    "(id, conversation_id, role, content, created_at) "
                    "VALUES ('assistant-1', 'conversation-1', "
                    "'assistant', 'reply', CURRENT_TIMESTAMP)"
                )
            )

    def _insert_snapshot(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO context_snapshots "
                    "(id, message_id, contract_version, captured_at, "
                    "snapshot_digest, created_at) "
                    "VALUES ('snapshot-1', 'assistant-1', '1', "
                    "CURRENT_TIMESTAMP, :digest, CURRENT_TIMESTAMP)"
                ),
                {"digest": "a" * 64},
            )

    def test_upgrade_from_d92_adds_empty_snapshot_tables_without_backfill(
        self,
    ) -> None:
        self._upgrade(self.D92_REVISION)
        self._open_engine()
        self._insert_conversation_and_assistant()
        self.engine.dispose()
        self.engine = None

        self._upgrade(self.D97_REVISION)
        self._open_engine()
        inspector = inspect(self.engine)

        assert {
            "context_snapshots",
            "context_snapshot_items",
        }.issubset(set(inspector.get_table_names()))
        with self.engine.connect() as connection:
            assert connection.scalar(
                text("SELECT COUNT(*) FROM context_snapshots")
            ) == 0
            assert connection.scalar(
                text("SELECT COUNT(*) FROM context_snapshot_items")
            ) == 0
            assert connection.scalar(
                text("SELECT COUNT(*) FROM messages")
            ) == 1
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == self.D97_REVISION

    def test_fresh_head_passes_database_verification(self) -> None:
        self._upgrade(self.D97_REVISION)
        result = verify_database(self.database_url)
        assert result.revision == self.D97_REVISION

    def test_snapshot_constraints_are_enforced(self) -> None:
        self._upgrade(self.D97_REVISION)
        self._open_engine()
        self._insert_conversation_and_assistant()
        self._insert_snapshot()

        with pytest.raises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO context_snapshots "
                        "(id, message_id, contract_version, captured_at, "
                        "snapshot_digest, created_at) "
                        "VALUES ('snapshot-2', 'assistant-1', '1', "
                        "CURRENT_TIMESTAMP, :digest, CURRENT_TIMESTAMP)"
                    ),
                    {"digest": "b" * 64},
                )

        with pytest.raises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO context_snapshot_items "
                        "(id, snapshot_id, item_order, layer, source_id, "
                        "text, content_sha256) "
                        "VALUES ('item-1', 'snapshot-1', 0, 'knowledge', "
                        "'chunk-1', 'text', :digest)"
                    ),
                    {"digest": "c" * 64},
                )

        with pytest.raises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO context_snapshot_items "
                        "(id, snapshot_id, item_order, layer, source_id, "
                        "text, content_sha256) "
                        "VALUES ('item-2', 'snapshot-1', 1, 'other', "
                        "'chunk-1', 'text', :digest)"
                    ),
                    {"digest": "d" * 64},
                )

    def test_empty_downgrade_to_d92_is_allowed(self) -> None:
        self._upgrade(self.D97_REVISION)
        self._downgrade(self.D92_REVISION)
        self._open_engine()

        assert "context_snapshots" not in inspect(
            self.engine
        ).get_table_names()
        with self.engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == self.D92_REVISION

    def test_downgrade_refuses_when_snapshot_data_exists(
        self,
    ) -> None:
        self._upgrade(self.D97_REVISION)
        self._open_engine()
        self._insert_conversation_and_assistant()
        self._insert_snapshot()
        self.engine.dispose()
        self.engine = None

        with pytest.raises(
            RuntimeError,
            match="d97_context_snapshot_downgrade_data",
        ):
            self._downgrade(self.D92_REVISION)
