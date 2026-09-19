from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.core.config import Settings
from app.db.session import create_database_engine, initialize_test_database
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.search.postgresql_hybrid import PostgreSQLHybridSearchAdapter
from app.search.postgresql_lexical import PostgreSQLLexicalSearch
from app.search.sqlite_fts5 import SQLiteFTS5SearchAdapter
from app.services.workspace_knowledge_root import (
    WorkspaceKnowledgeRootResolver,
)


class D93WorkspaceKnowledgeIsolationTests(unittest.TestCase):
    def test_workspace_roots_are_exact_and_non_overlapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            personal = Path(tmp) / "personal"
            company = Path(tmp) / "company"

            settings = Settings(
                oai_personal_knowledge_root=str(personal),
                oai_company_knowledge_root=str(company),
            )
            resolver = WorkspaceKnowledgeRootResolver(
                personal_root=settings.oai_personal_knowledge_root,
                company_root=settings.oai_company_knowledge_root,
            )

            self.assertEqual(
                resolver.resolve(
                    WorkspaceScope(WorkspaceId.PERSONAL)
                ),
                str(personal),
            )
            self.assertEqual(
                resolver.resolve(
                    WorkspaceScope(WorkspaceId.COMPANY)
                ),
                str(company),
            )

    def test_workspace_roots_reject_same_or_nested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "knowledge"

            with self.assertRaises(ValidationError):
                Settings(
                    oai_personal_knowledge_root=str(root),
                    oai_company_knowledge_root=str(root),
                )

            with self.assertRaises(ValidationError):
                Settings(
                    oai_personal_knowledge_root=str(root),
                    oai_company_knowledge_root=str(root / "company"),
                )

    def test_sqlite_search_filters_workspace_before_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = create_database_engine(
                f"sqlite:///{(Path(tmp) / 'knowledge.db').as_posix()}"
            )
            initialize_test_database(engine)

            with Session(engine) as session:
                adapter = SQLiteFTS5SearchAdapter(session)

                company = Document(
                    workspace_id="company",
                    source_path="company.txt",
                    file_name="company.txt",
                    file_extension=".txt",
                    mime_type="text/plain",
                    file_size=10,
                    content_hash="c" * 64,
                    status="indexed",
                    error_message=None,
                    indexed_at=None,
                )
                personal = Document(
                    workspace_id="personal",
                    source_path="personal.txt",
                    file_name="personal.txt",
                    file_extension=".txt",
                    mime_type="text/plain",
                    file_size=10,
                    content_hash="p" * 64,
                    status="indexed",
                    error_message=None,
                    indexed_at=None,
                )
                session.add_all([company, personal])
                session.flush()

                company_chunk = DocumentChunk(
                    document_id=company.id,
                    chunk_index=0,
                    content="shared workspace term",
                    source_locator="company",
                )
                personal_chunk = DocumentChunk(
                    document_id=personal.id,
                    chunk_index=0,
                    content="shared workspace term",
                    source_locator="personal",
                )
                session.add_all([company_chunk, personal_chunk])
                session.flush()
                adapter.index_chunks(company.id, [company_chunk])
                adapter.index_chunks(personal.id, [personal_chunk])

                personal_results = adapter.search(
                    "personal",
                    "shared workspace term",
                    1,
                )
                company_results = adapter.search(
                    "company",
                    "shared workspace term",
                    1,
                )

                self.assertEqual(len(personal_results), 1)
                self.assertEqual(
                    personal_results[0]["document_id"],
                    personal.id,
                )
                self.assertEqual(len(company_results), 1)
                self.assertEqual(
                    company_results[0]["document_id"],
                    company.id,
                )

            engine.dispose()

    def test_postgresql_lexical_passes_exact_workspace_predicate(self) -> None:
        session = MagicMock()
        rows = MagicMock()
        rows.mappings.return_value = []
        session.execute.return_value = rows

        search = PostgreSQLLexicalSearch(session)
        search.search("company", "pump pressure", 7)

        statement, parameters = session.execute.call_args.args

        self.assertIn(
            "documents.workspace_id = :workspace_id",
            str(statement),
        )
        self.assertEqual(parameters["workspace_id"], "company")
        self.assertEqual(parameters["limit"], 7)

    def test_hybrid_passes_identical_scope_to_both_providers(self) -> None:
        semantic = MagicMock()
        lexical = MagicMock()
        semantic.search.return_value = []
        lexical.search.return_value = []

        adapter = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )
        adapter.search("personal", "gearbox vibration", 5)

        semantic.search.assert_called_once_with(
            "personal",
            "gearbox vibration",
            5,
        )
        lexical.search.assert_called_once_with(
            "personal",
            "gearbox vibration",
            5,
        )


if __name__ == "__main__":
    unittest.main()
