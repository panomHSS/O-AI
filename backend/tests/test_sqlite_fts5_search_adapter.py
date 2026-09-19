from tests.workspace_fixture import TEST_WORKSPACE_ID

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine, initialize_test_database
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.search.sqlite_fts5 import SQLiteFTS5SearchAdapter


class SQLiteFTS5SearchAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = (
            Path(self.temporary_directory.name) / "oai.db"
        )
        self.engine = create_database_engine(
            f"sqlite:///{database_path.as_posix()}"
        )
        initialize_test_database(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        self.session = self.Session()
        self.adapter = SQLiteFTS5SearchAdapter(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def _create_document_with_chunk(self):
        document = Document(
            workspace_id=TEST_WORKSPACE_ID,
            source_path="knowledge/test.txt",
            file_name="test.txt",
            file_extension=".txt",
            mime_type="text/plain",
            file_size=100,
            content_hash="test-hash",
            status="indexed",
            error_message=None,
            indexed_at=None,
        )
        self.session.add(document)
        self.session.flush()

        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content="sovereign searchable knowledge",
            source_locator="section-1",
        )
        self.session.add(chunk)
        self.session.flush()

        return document, chunk

    def test_indexed_chunk_can_be_searched(self) -> None:
        document, chunk = self._create_document_with_chunk()

        self.adapter.index_chunks(document.id, [chunk])

        results = self.adapter.search(TEST_WORKSPACE_ID, "searchable", 10)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["document_id"], document.id)
        self.assertEqual(results[0]["chunk_id"], chunk.id)
        self.assertEqual(results[0]["file_name"], "test.txt")
        self.assertEqual(
            results[0]["source_locator"],
            "section-1",
        )
        self.assertIn("searchable", results[0]["excerpt"])
        self.assertIsNotNone(results[0]["relevance_score"])

    def test_delete_document_removes_only_search_index(self) -> None:
        document, chunk = self._create_document_with_chunk()
        self.adapter.index_chunks(document.id, [chunk])

        self.adapter.delete_document(document.id)

        results = self.adapter.search(TEST_WORKSPACE_ID, "searchable", 10)
        stored_chunk = self.session.scalar(
            select(DocumentChunk).where(
                DocumentChunk.id == chunk.id
            )
        )

        self.assertEqual(results, [])
        self.assertIsNotNone(stored_chunk)

    def test_index_chunks_accepts_empty_sequence(self) -> None:
        self.adapter.index_chunks("missing-document", [])

        count = self.session.scalar(
            text("SELECT count(*) FROM document_chunks_fts")
        )

        self.assertEqual(count, 0)

    def test_adapter_does_not_commit_transaction(self) -> None:
        document, chunk = self._create_document_with_chunk()
        self.adapter.index_chunks(document.id, [chunk])

        self.session.rollback()

        count = self.session.scalar(
            text("SELECT count(*) FROM document_chunks_fts")
        )

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
