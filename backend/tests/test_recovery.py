"""End-to-end tests for isolated SQLite recovery primitives."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.recovery import (
    REPOSITORY_ROOT,
    RecoveryError,
    _guard,
    backup,
    fingerprint,
    restore,
    validate_memory_invariants,
    verify,
)
from app.repositories.memories import MemoryRepository
from app.schemas.memories import ArchiveMemoryRequest, CreateMemoryRequest, DecisionRequest
from app.services.memories import MemoryService


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.db"
        self._upgrade(self.source, "head")
        self._populate_source()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _populate_source(self) -> None:
        """Create representative non-owner test data without application services."""
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) "
                "VALUES ('conversation-1', 'recovery test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            connection.executemany(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) "
                "VALUES (?, 'conversation-1', ?, ?, CURRENT_TIMESTAMP)",
                [
                    ("message-user-1", "user", "test question"),
                    ("message-assistant-1", "assistant", "test answer"),
                ],
            )
            connection.execute(
                "INSERT INTO message_citations "
                "(id, message_id, citation_order, citation_id, document_id, file_name, "
                "source_path, source_locator, excerpt, excerpt_hash, confidence, evidence_type, created_at) "
                "VALUES ('citation-1', 'message-assistant-1', 1, 'C1', 'document-1', "
                "'test.txt', 'test.txt', 'line 1', 'citation snapshot', 'a' || "
                "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', "
                "0.9, 'document_chunk', CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO documents "
                "(id, source_path, file_name, file_extension, mime_type, file_size, content_hash, "
                "status, error_message, created_at, updated_at, indexed_at) "
                "VALUES ('document-1', 'test.txt', 'test.txt', '.txt', 'text/plain', 12, "
                "'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', "
                "'indexed', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO document_chunks "
                "(id, document_id, chunk_index, content, source_locator, created_at) "
                "VALUES ('chunk-1', 'document-1', 0, 'recovery indexed content', 'line 1', CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO document_chunks_fts (content, document_id, chunk_id, source_locator) "
                "VALUES ('recovery indexed content', 'document-1', 'chunk-1', 'line 1')"
            )
            connection.execute(
                "INSERT INTO memories "
                "(id, key, value, value_type, state, current_version, active_version_id, "
                "pending_version_id, created_at, updated_at) "
                "VALUES ('memory-1', 'recovery_preference', '\"active\"', 'STRING', "
                "'CONFIRMED', 2, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            connection.executemany(
                "INSERT INTO memory_versions "
                "(id, memory_id, version, key, value, value_type, state, change_reason, "
                "decision_comment, evidence_snapshot, created_by, proposed_by, proposed_at, "
                "decided_by, decided_at, created_at) "
                "VALUES (?, 'memory-1', ?, 'recovery_preference', ?, 'STRING', ?, "
                "'owner test', NULL, NULL, 'owner', 'owner', CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP)",
                [
                    ("memory-version-1", 1, '\"active\"', "CONFIRMED", "owner", "CURRENT_TIMESTAMP"),
                    ("memory-version-2", 2, '\"pending\"', "PENDING", None, None),
                ],
            )
            connection.execute(
                "UPDATE memories SET active_version_id = 'memory-version-1', "
                "pending_version_id = 'memory-version-2' WHERE id = 'memory-1'"
            )
            connection.executemany(
                "INSERT INTO memories "
                "(id, key, value, value_type, state, current_version, active_version_id, "
                "pending_version_id, created_at, updated_at) "
                "VALUES (?, ?, '\"active\"', 'STRING', ?, 2, NULL, NULL, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                [
                    ("memory-2", "recovery_rejected", "CONFIRMED"),
                    ("memory-3", "recovery_archived", "ARCHIVED"),
                ],
            )
            connection.executemany(
                "INSERT INTO memory_versions "
                "(id, memory_id, version, key, value, value_type, state, change_reason, "
                "decision_comment, evidence_snapshot, created_by, proposed_by, proposed_at, "
                "decided_by, decided_at, created_at) "
                "VALUES (?, ?, ?, ?, '\"snapshot\"', 'STRING', ?, 'owner test', "
                "NULL, NULL, 'owner', 'owner', CURRENT_TIMESTAMP, NULL, NULL, CURRENT_TIMESTAMP)",
                [
                    ("memory-version-3", "memory-2", 1, "recovery_rejected", "CONFIRMED"),
                    ("memory-version-4", "memory-2", 2, "recovery_rejected", "REJECTED"),
                    ("memory-version-5", "memory-3", 1, "recovery_archived", "CONFIRMED"),
                    ("memory-version-6", "memory-3", 2, "recovery_archived", "ARCHIVED"),
                ],
            )
            connection.executemany(
                "UPDATE memories SET active_version_id = ? WHERE id = ?",
                [("memory-version-3", "memory-2"), ("memory-version-5", "memory-3")],
            )
            connection.commit()

    def _upgrade(self, database: Path, revision: str) -> None:
        previous_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
        get_settings.cache_clear()
        try:
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            command.upgrade(config, revision)
        finally:
            if previous_database_url is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()

    def _copy_source(self, name: str) -> Path:
        target = self.root / name
        backup(self.source, target)
        return target

    def _assert_rejected(self, database: Path) -> None:
        with self.assertRaises(RecoveryError):
            verify(database)

    def test_isolated_backup_restore_preserves_representative_state(self) -> None:
        before = fingerprint(self.source)
        backup_artifact = backup(self.source, self.root / "backup.db")
        restored_artifact = restore(backup_artifact.path, self.root / "restored.db")

        self.assertTrue(backup_artifact.verified)
        self.assertTrue(restored_artifact.verified)
        self.assertEqual(before, backup_artifact.fingerprint)
        self.assertEqual(before, restored_artifact.fingerprint)
        self.assertEqual(before, fingerprint(self.source))
        with closing(sqlite3.connect(restored_artifact.path)) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM document_chunks_fts WHERE document_chunks_fts MATCH 'indexed'"
                ).fetchone()[0],
                1,
            )
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute(
                    "UPDATE memory_versions SET change_reason = 'changed' "
                    "WHERE id = 'memory-version-1'"
                )

    def test_verify_immutability_probe_leaves_database_unchanged(self) -> None:
        before = fingerprint(self.source)
        with closing(sqlite3.connect(self.source, uri=False)) as connection:
            counts_before = connection.execute(
                "SELECT (SELECT count(*) FROM memories), "
                "(SELECT count(*) FROM memory_versions)"
            ).fetchone()
        validate_memory_invariants(self.source)
        with closing(sqlite3.connect(self.source, uri=False)) as connection:
            counts_after = connection.execute(
                "SELECT (SELECT count(*) FROM memories), "
                "(SELECT count(*) FROM memory_versions)"
            ).fetchone()
        self.assertEqual(counts_before, counts_after)
        self.assertEqual(before, fingerprint(self.source))

    def test_unsafe_paths_are_rejected(self) -> None:
        with self.assertRaises(RecoveryError):
            backup(self.source, self.source)
        existing = self.root / "existing.db"
        existing.touch()
        with self.assertRaises(RecoveryError):
            backup(self.source, existing)
        with self.assertRaises(RecoveryError):
            restore(self.source, existing)
        with self.assertRaises(RecoveryError):
            backup(Path("data/oai.db"), self.root / "x.db")

        configured_destination = self.root / "configured-production.db"
        previous_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{configured_destination.as_posix()}"
        get_settings.cache_clear()
        try:
            with self.assertRaises(RecoveryError):
                backup(self.source, configured_destination)
        finally:
            if previous_database_url is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()

    def test_path_guards_are_stable_outside_repository_root(self) -> None:
        production_path = REPOSITORY_ROOT / "data" / "oai.db"
        original_cwd = Path.cwd()
        original_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = "sqlite:///./data/oai.db"
        get_settings.cache_clear()
        try:
            os.chdir(self.root)
            with self.assertRaises(RecoveryError):
                _guard(Path("data") / ".." / "data" / "oai.db")
            with self.assertRaises(RecoveryError):
                _guard(production_path)
            with self.assertRaises(RecoveryError):
                _guard(REPOSITORY_ROOT / "data" / "." / "oai.db")
        finally:
            os.chdir(original_cwd)
            if original_database_url is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = original_database_url
            get_settings.cache_clear()

    def test_absolute_configured_sqlite_path_is_protected(self) -> None:
        configured_path = self.root / "configured-production.db"
        previous_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = f"sqlite:///{configured_path.as_posix()}"
        get_settings.cache_clear()
        try:
            with self.assertRaises(RecoveryError):
                _guard(configured_path)
        finally:
            if previous_database_url is None:
                os.environ.pop("OAI_DATABASE_URL", None)
            else:
                os.environ["OAI_DATABASE_URL"] = previous_database_url
            get_settings.cache_clear()

    def test_normalized_source_and_destination_aliases_are_rejected(self) -> None:
        alias = self.root / "nested" / ".." / "source.db"
        with self.assertRaises(RecoveryError):
            backup(self.source, alias)

    def test_failed_backup_cleans_only_its_owned_temporary_artifact(self) -> None:
        destination = self.root / "failed-backup.db"
        before = fingerprint(self.source)
        with patch("app.db.recovery.verify", side_effect=RecoveryError("forced failure")):
            with self.assertRaises(RecoveryError):
                backup(self.source, destination)
        self.assertFalse(destination.exists())
        self.assertEqual([], list(self.root.glob(".failed-backup.db.*.partial")))
        self.assertEqual(before, fingerprint(self.source))

    def test_invalid_schema_foreign_key_and_revision_are_rejected(self) -> None:
        invalid = self.root / "invalid.db"
        invalid.write_text("not a database", encoding="utf-8")
        with self.assertRaises(RecoveryError):
            verify(invalid)
        invalid_destination = self.root / "invalid-copy.db"
        with self.assertRaises(RecoveryError):
            backup(invalid, invalid_destination)
        self.assertFalse(invalid_destination.exists())

        foreign_key_violation = self.root / "foreign-key-violation.db"
        backup(self.source, foreign_key_violation)
        with closing(sqlite3.connect(foreign_key_violation)) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) "
                "VALUES ('orphan-message', 'missing-conversation', 'user', 'test', CURRENT_TIMESTAMP)"
            )
            connection.commit()
        with self.assertRaises(RecoveryError):
            verify(foreign_key_violation)

        wrong_revision = self.root / "wrong-revision.db"
        backup(self.source, wrong_revision)
        with closing(sqlite3.connect(wrong_revision)) as connection:
            connection.execute("UPDATE alembic_version SET version_num = 'wrong_revision'")
            connection.commit()
        with self.assertRaises(RecoveryError):
            verify(wrong_revision)

    def test_memory_invariant_corruption_is_rejected(self) -> None:
        corruptions = (
            ("cross-active.db", "UPDATE memories SET active_version_id = 'memory-version-3' WHERE id = 'memory-1'"),
            (
                "cross-pending.db",
                (
                    "UPDATE memories SET pending_version_id = NULL WHERE id = 'memory-1'",
                    "UPDATE memories SET pending_version_id = 'memory-version-2' WHERE id = 'memory-2'",
                ),
            ),
            ("active-pending.db", "UPDATE memories SET active_version_id = 'memory-version-2' WHERE id = 'memory-1'"),
            ("pending-confirmed.db", "UPDATE memories SET pending_version_id = 'memory-version-1' WHERE id = 'memory-1'"),
            ("bad-current-version.db", "UPDATE memories SET current_version = 9 WHERE id = 'memory-1'"),
            ("archived-pending.db", "UPDATE memories SET state = 'ARCHIVED' WHERE id = 'memory-1'"),
            (
                "archived-null-active-mixed-history.db",
                "UPDATE memories SET active_version_id = NULL WHERE id = 'memory-3'",
            ),
        )
        for filename, statement in corruptions:
            with self.subTest(filename=filename):
                database = self._copy_source(filename)
                with closing(sqlite3.connect(database)) as connection:
                    connection.execute("PRAGMA foreign_keys = OFF")
                    if isinstance(statement, tuple):
                        for item in statement:
                            connection.execute(item)
                    else:
                        connection.execute(statement)
                    connection.commit()
                self._assert_rejected(database)

    def test_migration_shaped_archived_memory_is_accepted(self) -> None:
        historical = self.root / "historical-archived.db"
        self._upgrade(historical, "0003_personal_memory")
        with closing(sqlite3.connect(historical)) as connection:
            connection.execute(
                "INSERT INTO memories "
                "(id, key, value, value_type, state, created_at, updated_at) "
                "VALUES ('historical-archived', 'historical_archived', '\"archived\"', "
                "'STRING', 'ARCHIVED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            connection.commit()
        self._upgrade(historical, "head")
        with closing(sqlite3.connect(historical)) as connection:
            state = connection.execute(
                "SELECT state, active_version_id, pending_version_id, current_version FROM memories "
                "WHERE id = 'historical-archived'"
            ).fetchone()
            version_state = connection.execute(
                "SELECT state FROM memory_versions WHERE memory_id = 'historical-archived'"
            ).fetchone()
        self.assertEqual(("ARCHIVED", None, None, 1), state)
        self.assertEqual(("ARCHIVED",), version_state)
        self.assertTrue(verify(historical).verified)

    def test_current_service_archived_memory_is_accepted(self) -> None:
        database = self.root / "service-archived.db"
        self._upgrade(database, "head")
        engine = create_engine(f"sqlite:///{database.as_posix()}")
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        with session_factory() as session:
            service = MemoryService(MemoryRepository(session))
            created = service.create(
                CreateMemoryRequest(
                    key="service_archived",
                    value="archive me",
                    value_type="STRING",
                    change_reason="test create",
                )
            )
            memory_id = UUID(str(created.id))
            service.approve(memory_id, 1, DecisionRequest(decision_comment="test approve"))
            archived = service.archive(memory_id, ArchiveMemoryRequest(change_reason="test archive"))
        engine.dispose()
        self.assertEqual("ARCHIVED", archived.state)
        self.assertTrue(verify(database).verified)

    def test_missing_or_replaced_immutability_trigger_is_rejected(self) -> None:
        missing = self._copy_source("missing-trigger.db")
        with closing(sqlite3.connect(missing)) as connection:
            connection.execute("DROP TRIGGER trg_memory_versions_immutable")
            connection.commit()
        self._assert_rejected(missing)

        replaced = self._copy_source("replaced-trigger.db")
        with closing(sqlite3.connect(replaced)) as connection:
            connection.execute("DROP TRIGGER trg_memory_versions_immutable")
            connection.execute(
                "CREATE TRIGGER trg_memory_versions_immutable "
                "BEFORE UPDATE ON memory_versions BEGIN SELECT 1; END"
            )
            connection.commit()
        self._assert_rejected(replaced)

    def test_citation_attached_to_user_message_is_rejected(self) -> None:
        database = self._copy_source("citation-user-message.db")
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "INSERT INTO message_citations "
                "(id, message_id, citation_order, citation_id, document_id, file_name, "
                "source_path, source_locator, excerpt, excerpt_hash, confidence, evidence_type, created_at) "
                "VALUES ('citation-user', 'message-user-1', 1, 'C-user', 'document-1', "
                "'test.txt', 'test.txt', 'line 1', 'snapshot', "
                "'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', "
                "0.5, 'document_chunk', CURRENT_TIMESTAMP)"
            )
            connection.commit()
        self._assert_rejected(database)
