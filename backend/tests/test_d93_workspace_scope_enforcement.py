from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.api.workspace_scope import (
    WorkspaceRequestError,
    get_workspace_scope,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.repositories.conversations import ConversationRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.memories import MemoryRepository
from app.repositories.projects import ProjectRepository


class _SearchStub:
    def delete_document(self, document_id: str) -> None:
        _ = document_id

    def index_chunks(self, document_id: str, chunks) -> None:
        _ = (document_id, chunks)

    def search(self, query: str, limit: int) -> list[dict[str, object]]:
        _ = (query, limit)
        return []


class D93WorkspaceScopeBatch01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "d93.db"
        self.database_url = f"sqlite:///{self.database_path.as_posix()}"
        self.previous_database_url = os.environ.get("OAI_DATABASE_URL")
        os.environ["OAI_DATABASE_URL"] = self.database_url
        get_settings.cache_clear()

        repository_root = Path(__file__).resolve().parents[2]
        command.upgrade(
            Config(str(repository_root / "alembic.ini")),
            "head",
        )
        self.engine = create_database_engine(self.database_url)

        self.personal = WorkspaceScope(WorkspaceId.PERSONAL)
        self.company = WorkspaceScope(WorkspaceId.COMPANY)

    def tearDown(self) -> None:
        self.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("OAI_DATABASE_URL", None)
        else:
            os.environ["OAI_DATABASE_URL"] = self.previous_database_url
        get_settings.cache_clear()
        self.temporary_directory.cleanup()

    def test_exact_request_workspace_contract(self) -> None:
        self.assertEqual(
            get_workspace_scope("personal").workspace_id,
            WorkspaceId.PERSONAL,
        )
        self.assertEqual(
            get_workspace_scope("company").workspace_id,
            WorkspaceId.COMPANY,
        )

        with self.assertRaisesRegex(
            WorkspaceRequestError,
            "workspace_required",
        ):
            get_workspace_scope(None)

        for invalid in (
            "",
            "Personal",
            "COMPANY",
            " personal",
            "company ",
            "legacy",
            "default",
            "unknown",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(
                    WorkspaceRequestError,
                    "workspace_id_invalid",
                ):
                    get_workspace_scope(invalid)

    def test_project_scope_create_read_list_and_legacy_quarantine(self) -> None:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            personal = ProjectRepository(session, self.personal)
            company = ProjectRepository(session, self.company)

            p = personal.create("Personal", "Personal objective")
            c = company.create("Company", "Company objective")
            personal.commit()

            self.assertEqual(p.workspace_id, "personal")
            self.assertEqual(c.workspace_id, "company")
            self.assertIsNone(personal.get(c.id))
            self.assertIsNone(company.get(p.id))
            self.assertEqual([item.id for item in personal.list(1, 25, None)[0]], [p.id])
            self.assertEqual([item.id for item in company.list(1, 25, None)[0]], [c.id])

            session.execute(
                text(
                    "INSERT INTO projects "
                    "(id, title, objective, status, current_revision, created_at, updated_at, workspace_id) "
                    "VALUES ('legacy-project', 'Legacy', 'Legacy objective', 'ACTIVE', 1, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)"
                )
            )
            session.commit()
            self.assertIsNone(personal.get("legacy-project"))
            self.assertIsNone(company.get("legacy-project"))

    def test_conversation_scope_and_project_lookup_are_exact(self) -> None:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            personal_projects = ProjectRepository(session, self.personal)
            company_projects = ProjectRepository(session, self.company)
            p = personal_projects.create("P", "P objective")
            c = company_projects.create("C", "C objective")
            personal_projects.commit()

            personal = ConversationRepository(session, self.personal)
            company = ConversationRepository(session, self.company)
            cp = personal.create("Personal chat", p.id)
            cc = company.create("Company chat", c.id)
            personal.commit()

            self.assertEqual(cp.workspace_id, "personal")
            self.assertEqual(cc.workspace_id, "company")
            self.assertTrue(personal.project_exists(p.id))
            self.assertFalse(personal.project_exists(c.id))
            self.assertTrue(company.project_exists(c.id))
            self.assertFalse(company.project_exists(p.id))
            self.assertIsNone(personal.get(cc.id))
            self.assertIsNone(company.get(cp.id))

            session.execute(
                text(
                    "INSERT INTO conversations "
                    "(id, title, created_at, updated_at, project_id, workspace_id) "
                    "VALUES ('legacy-conversation', 'Legacy', CURRENT_TIMESTAMP, "
                    "CURRENT_TIMESTAMP, NULL, NULL)"
                )
            )
            session.commit()
            self.assertIsNone(personal.get("legacy-conversation"))
            self.assertIsNone(company.get("legacy-conversation"))

    def test_memory_scope_supports_same_key_without_cross_visibility(self) -> None:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            personal = MemoryRepository(session, self.personal)
            company = MemoryRepository(session, self.company)

            p = personal.create("profile.name", '"Personal"', "STRING", "PENDING")
            c = company.create("profile.name", '"Company"', "STRING", "PENDING")
            personal.commit()

            self.assertEqual(p.workspace_id, "personal")
            self.assertEqual(c.workspace_id, "company")
            self.assertIsNone(personal.get(c.id))
            self.assertIsNone(company.get(p.id))
            self.assertEqual(personal.list(None, 1, 25)[1], 1)
            self.assertEqual(company.list(None, 1, 25)[1], 1)

            session.execute(
                text(
                    "INSERT INTO memories "
                    "(id, key, value, value_type, state, current_version, "
                    "created_at, updated_at, workspace_id) "
                    "VALUES ('legacy-memory', 'legacy.key', 'value', 'STRING', "
                    "'PENDING', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)"
                )
            )
            session.commit()
            self.assertIsNone(personal.get("legacy-memory"))
            self.assertIsNone(company.get("legacy-memory"))

    def test_knowledge_scope_supports_same_path_and_mark_missing_isolated(self) -> None:
        from sqlalchemy.orm import Session

        metadata = {
            "source_path": "shared/file.txt",
            "file_name": "file.txt",
            "file_extension": ".txt",
            "mime_type": "text/plain",
            "file_size": 5,
            "content_hash": "a" * 64,
        }

        with Session(self.engine) as session:
            personal = KnowledgeRepository(
                session,
                _SearchStub(),
                self.personal,
            )
            company = KnowledgeRepository(
                session,
                _SearchStub(),
                self.company,
            )

            p = personal.create_failed(metadata, "personal failure")
            c = company.create_failed(
                {**metadata, "content_hash": "b" * 64},
                "company failure",
            )
            personal.commit()

            self.assertEqual(p.workspace_id, "personal")
            self.assertEqual(c.workspace_id, "company")
            self.assertEqual(personal.get_by_path("shared/file.txt").id, p.id)
            self.assertEqual(company.get_by_path("shared/file.txt").id, c.id)
            self.assertIsNone(personal.get(c.id))
            self.assertIsNone(company.get(p.id))

            p.status = "indexed"
            c.status = "indexed"
            personal.commit()
            personal.mark_missing(set())
            personal.commit()

            self.assertEqual(p.status, "missing")
            self.assertEqual(c.status, "indexed")

            session.execute(
                text(
                    "INSERT INTO documents "
                    "(id, source_path, file_name, file_extension, mime_type, "
                    "file_size, content_hash, status, created_at, updated_at, workspace_id) "
                    "VALUES ('legacy-document', 'legacy/file.txt', 'file.txt', '.txt', "
                    "'text/plain', 5, :hash, 'indexed', CURRENT_TIMESTAMP, "
                    "CURRENT_TIMESTAMP, NULL)"
                ),
                {"hash": "c" * 64},
            )
            session.commit()
            self.assertIsNone(personal.get("legacy-document"))
            self.assertIsNone(company.get("legacy-document"))


if __name__ == "__main__":
    unittest.main()
