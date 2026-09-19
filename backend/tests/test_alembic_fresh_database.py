import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.models.message_citation import MessageCitation
from app.models.memory import Memory


REVISION = "0013_context_snapshot_persistence"

EXPECTED_TABLES = {
    "alembic_version",
    "context_snapshots",
    "context_snapshot_items",
    "conversations",
    "messages",
    "message_citations",
    "documents",
    "document_chunks",
    "document_chunks_fts",
    "memories",
    "memory_versions",
    "projects",
    "project_revisions",
    "project_action_execution_proposals",
    "execution_audit_events",
    "oauth_credentials",
    "automation_definitions",
    "automation_runs",
}

EXPECTED_INDEXES = {
    "context_snapshots": set(),
    "context_snapshot_items": {"ix_context_snapshot_items_snapshot_id"},
    "conversations": {
        "ix_conversations_updated_at",
        "ix_conversations_project_id",
        "ix_conversations_workspace_id",
    },    "documents": {"ix_documents_source_path", "ix_documents_content_hash", "ix_documents_status", "ix_documents_updated_at", "ix_documents_workspace_id", "uq_documents_legacy_source_path", "uq_documents_workspace_source_path"},
    "document_chunks": {"ix_document_chunks_document_id"},
    "message_citations": {"ix_message_citations_message_id"},
    "project_action_execution_proposals": {"ix_project_action_execution_proposals_project_id", "ix_project_action_execution_proposals_conversation_id"},
    "execution_audit_events": {"ix_execution_audit_events_request_id", "ix_execution_audit_events_occurred_at"},
    "memories": {"ix_memories_key", "ix_memories_state", "ix_memories_updated_at", "ix_memories_workspace_id", "uq_memories_legacy_key", "uq_memories_workspace_key"},
    "memory_versions": {"ix_memory_versions_memory_id"},
    "projects": {"ix_projects_status", "ix_projects_updated_at", "ix_projects_workspace_id"},
    "project_revisions": {"ix_project_revisions_project_id"},
    "automation_definitions": {
        "ix_automation_definitions_status_due",
    },
    "automation_runs": {
        "ix_automation_runs_automation_due",
    },
}


class AlembicFreshDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "fresh-oai.db"
        self.database_url = f"sqlite:///{self.database_path.as_posix()}"
        self.previous_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = self.database_url
        get_settings.cache_clear()
        self.engine = None

    def tearDown(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = self.previous_database_url
        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def _config(self) -> Config:
        repository_root = Path(__file__).resolve().parents[2]
        return Config(str(repository_root / "alembic.ini"))

    def _upgrade_to_head(self, target: str = "head") -> None:
        command.upgrade(self._config(), target)

    def test_fresh_database_upgrade_creates_current_schema_and_is_idempotent(self) -> None:
        self._upgrade_to_head()
        self.engine = create_database_engine(self.database_url)
        inspector = inspect(self.engine)

        self.assertTrue(EXPECTED_TABLES.issubset(set(inspector.get_table_names())))
        execution_columns = {
            column["name"]
            for column in inspector.get_columns(
                "project_action_execution_proposals"
            )
        }

        self.assertEqual(
            execution_columns,
            {
                "id",
                "project_id",
                "conversation_id",
                "project_revision",
                "source_action",
                "steps",
                "status",
                "approved",
                "executed",
            },
        )

        execution_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "project_action_execution_proposals"
            )
        }

        self.assertEqual(
            execution_indexes,
            {
                "ix_project_action_execution_proposals_project_id",
                "ix_project_action_execution_proposals_conversation_id",
            },
        )

        audit_columns = {
            column["name"]
            for column in inspector.get_columns(
                "execution_audit_events"
            )
        }
        self.assertEqual(
            audit_columns,
            {
                "id",
                "contract_version",
                "request_id",
                "stage",
                "action",
                "status",
                "occurred_at",
                "target_kind",
                "adapter_id",
                "reason_code",
                "plan_digest",
            },
        )
        audit_indexes = {
            index["name"]
            for index in inspector.get_indexes(
                "execution_audit_events"
            )
        }
        self.assertEqual(
            audit_indexes,
            {
                "ix_execution_audit_events_request_id",
                "ix_execution_audit_events_occurred_at",
            },
        )

        oauth_columns = {
            column["name"]
            for column in inspector.get_columns("oauth_credentials")
        }
        self.assertEqual(
            oauth_columns,
            {
                "profile_id",
                "provider_id",
                "plugin_id",
                "plugin_version",
                "capability_name",
                "encrypted_refresh_token",
                "encryption_nonce",
                "cipher_version",
                "granted_scopes",
                "status",
                "refresh_token_expires_at",
                "created_at",
                "updated_at",
            },
        )
        self.assertTrue(
            {
                "access_token",
                "refresh_token",
                "client_secret",
                "authorization_code",
            }.isdisjoint(oauth_columns)
        )
        self.assertEqual(
            {
                index["name"]
                for index in inspector.get_indexes("oauth_credentials")
            },
            set(),
        )

        automation_definition_columns = {
            column["name"]
            for column in inspector.get_columns("automation_definitions")
        }
        self.assertEqual(
            automation_definition_columns,
            {
                "id",
                "contract_version",
                "kind",
                "message",
                "schedule_kind",
                "run_at_iso",
                "daily_local_time",
                "timezone",
                "max_runs",
                "definition_digest",
                "status",
                "approval_expires_at",
                "approved_at",
                "terminal_at",
                "next_due_at_utc",
                "created_at",
                "updated_at",
            },
        )
        automation_run_columns = {
            column["name"]
            for column in inspector.get_columns("automation_runs")
        }
        self.assertEqual(
            automation_run_columns,
            {
                "id",
                "automation_id",
                "definition_digest",
                "due_at_utc",
                "status",
                "claimed_at",
                "delivered_at",
                "created_at",
                "updated_at",
            },
        )
        run_unique_constraints = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints("automation_runs")
        }
        self.assertIn(
            ("automation_id", "due_at_utc"),
            run_unique_constraints,
        )
        run_foreign_keys = inspector.get_foreign_keys("automation_runs")
        self.assertEqual(len(run_foreign_keys), 1)
        self.assertEqual(
            run_foreign_keys[0]["constrained_columns"],
            ["automation_id"],
        )
        self.assertEqual(
            run_foreign_keys[0]["referred_table"],
            "automation_definitions",
        )
        self.assertEqual(
            run_foreign_keys[0]["options"].get("ondelete"),
            "RESTRICT",
        )

        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), REVISION)
            self.assertEqual(connection.scalar(text("PRAGMA foreign_keys")), 1)

        for table_name, expected_indexes in EXPECTED_INDEXES.items():
            actual_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            self.assertTrue(expected_indexes.issubset(actual_indexes))

        self._assert_foreign_key(inspector, "messages", "conversation_id", "conversations")
        self._assert_foreign_key(inspector, "document_chunks", "document_id", "documents")
        self._assert_foreign_key(inspector, "message_citations", "message_id", "messages")

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO document_chunks_fts (content, document_id, chunk_id, source_locator) "
                    "VALUES (:content, :document_id, :chunk_id, :source_locator)"
                ),
                {"content": "alembic searchable knowledge", "document_id": "document-1", "chunk_id": "chunk-1", "source_locator": "page 1"},
            )
            self.assertEqual(
                connection.scalar(text("SELECT count(*) FROM document_chunks_fts WHERE document_chunks_fts MATCH 'searchable'")),
                1,
            )

        before = set(inspector.get_table_names())
        self._upgrade_to_head()
        self.assertEqual(before, set(inspect(self.engine).get_table_names()))
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), REVISION)

    def test_current_orm_can_read_and_write_migrated_schema(self) -> None:
        self._upgrade_to_head()
        self.engine = create_database_engine(self.database_url)
        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        now = datetime.now(timezone.utc)

        with Session.begin() as session:
            conversation = Conversation(id="conversation-1", title="Migrated conversation", created_at=now, updated_at=now)
            document = Document(
                id="document-1", source_path="notes/example.txt", file_name="example.txt", file_extension=".txt",
                mime_type="text/plain", file_size=5, content_hash="a" * 64, status="indexed", created_at=now, updated_at=now,
            )
            session.add_all([
                conversation,
                document,
                Message(id="message-1", conversation=conversation, role="user", content="Hello", created_at=now),
                DocumentChunk(id="chunk-1", document=document, chunk_index=0, content="Hello", source_locator="line 1", created_at=now),
                MessageCitation(id="citation-1", message_id="message-1", citation_order=1, citation_id="S1", document_id="document-1", file_name="example.txt", source_path="notes/example.txt", source_locator="line 1", excerpt="Hello", excerpt_hash="a" * 64, confidence=0.9, evidence_type="document_chunk", created_at=now),
                Memory(id="memory-1", key="profile.name", value="\"Ada\"", value_type="STRING", state="CONFIRMED", created_at=now, updated_at=now),
            ])

        with Session() as session:
            self.assertEqual(session.scalar(select(Message.content)), "Hello")
            self.assertEqual(session.scalar(select(DocumentChunk.content)), "Hello")
            self.assertEqual(session.scalar(select(MessageCitation.excerpt)), "Hello")
            self.assertEqual(session.scalar(select(Memory.key)), "profile.name")

        with Session.begin() as session:
            session.delete(session.get(Conversation, "conversation-1"))
            session.delete(session.get(Document, "document-1"))

        with Session() as session:
            self.assertEqual(session.scalar(select(func.count(Message.id))), 0)
            self.assertEqual(session.scalar(select(func.count(DocumentChunk.id))), 0)
            self.assertEqual(session.scalar(select(func.count(MessageCitation.id))), 0)

    def test_versioning_upgrade_preserves_existing_memory_lifecycle(self) -> None:
        self._upgrade_to_head("0003_personal_memory")
        self.engine = create_database_engine(self.database_url)
        now = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO memories (id, key, value, value_type, state, created_at, updated_at) VALUES ('confirmed', 'profile.confirmed', '\"Ada\"', 'STRING', 'CONFIRMED', :now, :now)"), {"now": now})
            connection.execute(text("INSERT INTO memories (id, key, value, value_type, state, created_at, updated_at) VALUES ('pending', 'profile.pending', '42', 'INTEGER', 'PENDING', :now, :now)"), {"now": now})
        self.engine.dispose()
        self.engine = None

        self._upgrade_to_head()
        self.engine = create_database_engine(self.database_url)
        with self.engine.connect() as connection:
            confirmed = connection.execute(text("SELECT active_version_id, pending_version_id FROM memories WHERE id = 'confirmed'")).one()
            pending = connection.execute(text("SELECT active_version_id, pending_version_id FROM memories WHERE id = 'pending'")).one()
            self.assertIsNotNone(confirmed[0])
            self.assertIsNone(confirmed[1])
            self.assertIsNone(pending[0])
            self.assertIsNotNone(pending[1])
            self.assertEqual(connection.scalar(text("SELECT state FROM memory_versions WHERE memory_id = 'confirmed'")), "CONFIRMED")
            self.assertEqual(connection.scalar(text("SELECT state FROM memory_versions WHERE memory_id = 'pending'")), "PENDING")

    def test_versioning_migration_protects_snapshot_content(self) -> None:
        self._upgrade_to_head()
        self.engine = create_database_engine(self.database_url)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO memories (id, key, value, value_type, state, current_version, created_at, updated_at) VALUES ('immutable-memory', 'profile.immutable', '\"Ada\"', 'STRING', 'PENDING', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
            connection.execute(text("INSERT INTO memory_versions (id, memory_id, version, key, value, value_type, state, change_reason, created_by, proposed_by, proposed_at, created_at) VALUES ('immutable-version', 'immutable-memory', 1, 'profile.immutable', '\"Ada\"', 'STRING', 'PENDING', 'Created', 'owner', 'owner', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
            connection.execute(text("UPDATE memories SET pending_version_id = 'immutable-version' WHERE id = 'immutable-memory'"))
            with self.assertRaises(IntegrityError):
                connection.execute(text("UPDATE memory_versions SET value = '\"Changed\"' WHERE id = 'immutable-version'"))

    def test_project_backbone_upgrade_preserves_existing_conversations_with_null_project(self) -> None:
        self._upgrade_to_head("0004_memory_versioning")
        self.engine = create_database_engine(self.database_url)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO conversations (id, title, created_at, updated_at) VALUES ('pre-project', 'Existing', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        self.engine.dispose()
        self.engine = None
        self._upgrade_to_head()
        self.engine = create_database_engine(self.database_url)
        with self.engine.connect() as connection:
            self.assertIsNone(connection.scalar(text("SELECT project_id FROM conversations WHERE id = 'pre-project'")))
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM projects")), 0)

    def _assert_foreign_key(self, inspector, table_name: str, column_name: str, target_table: str) -> None:
        foreign_keys = inspector.get_foreign_keys(table_name)
        matching = [foreign_key for foreign_key in foreign_keys if foreign_key["constrained_columns"] == [column_name]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["referred_table"], target_table)
        self.assertEqual(matching[0]["options"].get("ondelete"), "CASCADE")
