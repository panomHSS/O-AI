import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import create_database_engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_chunk_embedding import (
    DocumentChunkEmbedding,
)
from app.readers import create_document_reader_registry
from app.repositories.knowledge import KnowledgeRepository
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)
from app.services.knowledge import KnowledgeService


DIMENSIONS = 1536


def vector(value: float) -> list[float]:
    values = [0.0] * DIMENSIONS
    values[0] = value
    values[1] = 1.0 - value
    return values


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.fail_documents = False

    @property
    def dimensions(self) -> int:
        return DIMENSIONS

    def embed_documents(
        self,
        texts,
    ) -> list[list[float]]:
        if self.fail_documents:
            raise RuntimeError(
                "Synthetic embedding failure."
            )

        return [
            vector(0.9 if "second" in text else 0.8)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        return vector(0.9)


class SemanticKnowledgeIndexingIntegrationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        database_url = os.environ.get(
            "OAI_DATABASE_URL"
        )

        if not database_url:
            raise unittest.SkipTest(
                "OAI_DATABASE_URL is not configured."
            )

        if not database_url.startswith("postgresql"):
            raise unittest.SkipTest(
                "Semantic indexing integration test "
                "requires PostgreSQL."
            )

        cls.engine = create_database_engine(
            database_url
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.root = (
            Path(self.temporary_directory.name)
            / "knowledge"
        )
        self.root.mkdir()

        self.session = Session(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        self.source_name = (
            "semantic-indexing-integration-note.txt"
        )

        self.embeddings = FakeEmbeddingProvider()

        search = PostgreSQLVectorSearchAdapter(
            self.session,
            self.embeddings,
        )

        repository = KnowledgeRepository(
            session=self.session,
            search=search,
        )

        self.service = KnowledgeService(
            repository,
            create_document_reader_registry(),
            str(self.root),
            1,
            40,
            10,
        )

    def tearDown(self) -> None:
        try:
            self.session.rollback()

            documents = self.session.scalars(
                select(Document).where(
                    Document.source_path
                    == self.source_name
                )
            ).all()

            for document in documents:
                self.session.delete(document)

            self.session.commit()
        finally:
            self.session.close()
            self.temporary_directory.cleanup()

    def _document(self) -> Document:
        document = self.session.scalar(
            select(Document).where(
                Document.source_path == self.source_name
            )
        )

        self.assertIsNotNone(document)
        return document

    def _embedding_count(
        self,
        document_id: str,
    ) -> int:
        return (
            self.session.scalar(
                select(
                    func.count(
                        DocumentChunkEmbedding.chunk_id
                    )
                ).where(
                    DocumentChunkEmbedding.document_id
                    == document_id
                )
            )
            or 0
        )

    def _chunk_contents(
        self,
        document_id: str,
    ) -> list[str]:
        return list(
            self.session.scalars(
                select(DocumentChunk.content)
                .where(
                    DocumentChunk.document_id
                    == document_id
                )
                .order_by(
                    DocumentChunk.chunk_index
                )
            )
        )

    def test_semantic_index_lifecycle_is_atomic(
        self,
    ) -> None:
        source = self.root / self.source_name
        source.write_text(
            "first semantic knowledge",
            encoding="utf-8",
        )

        first = self.service.scan()

        self.assertEqual(first.indexed, 1)

        document = self._document()
        document_id = document.id

        first_chunks = self._chunk_contents(
            document_id
        )

        self.assertGreater(
            len(first_chunks),
            0,
        )
        self.assertEqual(
            self._embedding_count(document_id),
            len(first_chunks),
        )

        source.write_text(
            "second semantic knowledge",
            encoding="utf-8",
        )

        second = self.service.scan()

        self.assertEqual(second.indexed, 1)

        second_chunks = self._chunk_contents(
            document_id
        )

        self.assertNotEqual(
            first_chunks,
            second_chunks,
        )
        self.assertTrue(
            any(
                "second" in content
                for content in second_chunks
            )
        )
        self.assertEqual(
            self._embedding_count(document_id),
            len(second_chunks),
        )

        self.embeddings.fail_documents = True

        source.write_text(
            "third semantic knowledge",
            encoding="utf-8",
        )

        failed = self.service.scan()

        self.assertEqual(failed.failed, 1)

        preserved_chunks = self._chunk_contents(
            document_id
        )

        self.assertEqual(
            preserved_chunks,
            second_chunks,
        )
        self.assertEqual(
            self._embedding_count(document_id),
            len(second_chunks),
        )

        self.service.delete_document(
            document_id
        )

        self.assertIsNone(
            self.session.get(
                Document,
                document_id,
            )
        )
        self.assertEqual(
            self._embedding_count(document_id),
            0,
        )


if __name__ == "__main__":
    unittest.main()