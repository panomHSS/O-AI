from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.db.verification import DatabaseVerificationError, verify_database


D91_REVISION = "0011_automation_foundation"
D92_REVISION = "0012_workspace_persistence"
ROOT_TABLES = ("conversations", "projects", "memories", "documents")
CHILD_TABLES = (
    "messages",
    "message_citations",
    "memory_versions",
    "project_revisions",
    "project_update_proposals",
    "project_action_execution_proposals",
    "document_chunks",
)


class D92WorkspaceMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "d92.db"
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

    def _upgrade(self, target: str = "head") -> None:
        command.upgrade(self._config(), target)

    def _downgrade(self, target: str) -> None:
        command.downgrade(self._config(), target)

    def _open_engine(self) -> None:
        self.engine = create_database_engine(self.database_url)

    def _insert_legacy_roots(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id, title, objective, status, current_revision, created_at, updated_at) "
                    "VALUES ('legacy-project', 'Legacy project', 'Keep it', 'ACTIVE', 1, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO conversations "
                    "(id, title, created_at, updated_at, project_id) "
                    "VALUES ('legacy-conversation', 'Legacy conversation', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'legacy-project')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO memories "
                    "(id, key, value, value_type, state, current_version, "
                    "created_at, updated_at) "
                    "VALUES ('legacy-memory', 'legacy.key', 'value', 'STRING', "
                    "'PENDING', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, source_path, file_name, file_extension, mime_type, "
                    "file_size, content_hash, status, created_at, updated_at) "
                    "VALUES ('legacy-document', 'legacy/file.txt', 'file.txt', "
                    "'.txt', 'text/plain', 5, :hash, 'indexed', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"hash": "a" * 64},
            )

    def _insert_memory(
        self,
        *,
        row_id: str,
        key: str,
        workspace_id: str | None,
    ) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO memories "
                    "(id, key, value, value_type, state, current_version, "
                    "created_at, updated_at, workspace_id) "
                    "VALUES (:id, :key, 'value', 'STRING', 'PENDING', 1, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :workspace_id)"
                ),
                {
                    "id": row_id,
                    "key": key,
                    "workspace_id": workspace_id,
                },
            )

    def _insert_document(
        self,
        *,
        row_id: str,
        source_path: str,
        workspace_id: str | None,
    ) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, source_path, file_name, file_extension, mime_type, "
                    "file_size, content_hash, status, created_at, updated_at, "
                    "workspace_id) "
                    "VALUES (:id, :source_path, 'file.txt', '.txt', "
                    "'text/plain', 5, :hash, 'indexed', CURRENT_TIMESTAMP, "
                    "CURRENT_TIMESTAMP, :workspace_id)"
                ),
                {
                    "id": row_id,
                    "source_path": source_path,
                    "hash": row_id.encode("utf-8").hex().ljust(64, "0")[:64],
                    "workspace_id": workspace_id,
                },
            )

    def test_upgrade_preserves_legacy_rows_as_unscoped(self) -> None:
        self._upgrade(D91_REVISION)
        self._open_engine()
        self._insert_legacy_roots()
        self.engine.dispose()
        self.engine = None

        self._upgrade()
        self._open_engine()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.scalar(text("SELECT version_num FROM alembic_version")),
                D92_REVISION,
            )
            for table_name in ROOT_TABLES:
                self.assertIsNone(
                    connection.scalar(
                        text(
                            f"SELECT workspace_id FROM {table_name} LIMIT 1"
                        )
                    )
                )
            self.assertEqual(
                connection.scalar(
                    text(
                        "SELECT project_id FROM conversations "
                        "WHERE id = 'legacy-conversation'"
                    )
                ),
                "legacy-project",
            )
            self.assertEqual(
                connection.scalar(
                    text(
                        "SELECT key FROM memories WHERE id = 'legacy-memory'"
                    )
                ),
                "legacy.key",
            )
            self.assertEqual(
                connection.scalar(
                    text(
                        "SELECT source_path FROM documents "
                        "WHERE id = 'legacy-document'"
                    )
                ),
                "legacy/file.txt",
            )

    def test_fresh_schema_scopes_only_four_root_tables(self) -> None:
        self._upgrade()
        self._open_engine()
        inspector = inspect(self.engine)

        for table_name in ROOT_TABLES:
            columns = {
                column["name"]: column
                for column in inspector.get_columns(table_name)
            }
            self.assertIn("workspace_id", columns)
            self.assertTrue(columns["workspace_id"]["nullable"])
            self.assertIsNone(columns["workspace_id"].get("default"))

        for table_name in CHILD_TABLES:
            self.assertNotIn(
                "workspace_id",
                {
                    column["name"]
                    for column in inspector.get_columns(table_name)
                },
            )

    def test_workspace_check_constraints_are_exact(self) -> None:
        self._upgrade()
        self._open_engine()

        with self.engine.connect() as connection:
            for table_name in ROOT_TABLES:
                sql = connection.scalar(
                    text(
                        "SELECT sql FROM sqlite_schema "
                        "WHERE type = 'table' AND name = :table_name"
                    ),
                    {"table_name": table_name},
                )
                normalized = " ".join(sql.upper().split())
                self.assertIn(
                    "WORKSPACE_ID IS NULL OR WORKSPACE_ID IN "
                    "('PERSONAL', 'COMPANY')",
                    normalized,
                )

        self._insert_legacy_roots()
        for table_name in ROOT_TABLES:
            with self.assertRaises(IntegrityError):
                with self.engine.begin() as connection:
                    connection.execute(
                        text(
                            f"UPDATE {table_name} "
                            "SET workspace_id = 'Personal'"
                        )
                    )

    def test_memory_uniqueness_is_legacy_and_workspace_scoped(self) -> None:
        self._upgrade()
        self._open_engine()

        self._insert_memory(
            row_id="m-personal",
            key="shared.key",
            workspace_id="personal",
        )
        self._insert_memory(
            row_id="m-company",
            key="shared.key",
            workspace_id="company",
        )

        with self.assertRaises(IntegrityError):
            self._insert_memory(
                row_id="m-personal-duplicate",
                key="shared.key",
                workspace_id="personal",
            )

        self._insert_memory(
            row_id="m-legacy",
            key="legacy.unique",
            workspace_id=None,
        )
        with self.assertRaises(IntegrityError):
            self._insert_memory(
                row_id="m-legacy-duplicate",
                key="legacy.unique",
                workspace_id=None,
            )

    def test_document_uniqueness_is_legacy_and_workspace_scoped(self) -> None:
        self._upgrade()
        self._open_engine()

        self._insert_document(
            row_id="d-personal",
            source_path="shared/file.txt",
            workspace_id="personal",
        )
        self._insert_document(
            row_id="d-company",
            source_path="shared/file.txt",
            workspace_id="company",
        )

        with self.assertRaises(IntegrityError):
            self._insert_document(
                row_id="d-personal-duplicate",
                source_path="shared/file.txt",
                workspace_id="personal",
            )

        self._insert_document(
            row_id="d-legacy",
            source_path="legacy/file.txt",
            workspace_id=None,
        )
        with self.assertRaises(IntegrityError):
            self._insert_document(
                row_id="d-legacy-duplicate",
                source_path="legacy/file.txt",
                workspace_id=None,
            )

    def test_downgrade_refuses_scoped_data_then_allows_unscoped(self) -> None:
        self._upgrade()
        self._open_engine()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO conversations "
                    "(id, title, created_at, updated_at, workspace_id) "
                    "VALUES ('scoped-conversation', 'Scoped', "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'personal')"
                )
            )
        self.engine.dispose()
        self.engine = None

        with self.assertRaisesRegex(
            RuntimeError,
            "d92_workspace_downgrade_scoped_data",
        ):
            self._downgrade(D91_REVISION)

        self._open_engine()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE conversations SET workspace_id = NULL "
                    "WHERE id = 'scoped-conversation'"
                )
            )
        self.engine.dispose()
        self.engine = None

        self._downgrade(D91_REVISION)
        self._open_engine()
        inspector = inspect(self.engine)
        for table_name in ROOT_TABLES:
            self.assertNotIn(
                "workspace_id",
                {
                    column["name"]
                    for column in inspector.get_columns(table_name)
                },
            )
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.scalar(text("SELECT version_num FROM alembic_version")),
                D91_REVISION,
            )

    def test_database_verification_requires_exact_d92_schema(self) -> None:
        self._upgrade()
        result = verify_database(self.database_url)
        self.assertEqual(result.revision, D92_REVISION)

        self._open_engine()
        with self.engine.begin() as connection:
            connection.execute(text("DROP INDEX ix_projects_workspace_id"))
        self.engine.dispose()
        self.engine = None

        with self.assertRaises(DatabaseVerificationError):
            verify_database(self.database_url)


if __name__ == "__main__":
    unittest.main()
