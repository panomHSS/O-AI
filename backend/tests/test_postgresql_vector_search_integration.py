import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.session import create_database_engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)


DIMENSIONS = 1536


def vector(
    first: float,
    second: float,
) -> list[float]:
    values = [0.0] * DIMENSIONS
    values[0] = first
    values[1] = second
    return values


class FakeEmbeddingProvider:
    @property
    def dimensions(self) -> int:
        return DIMENSIONS

    def embed_documents(
        self,
        texts,
    ) -> list[list[float]]:
        mapping = {
            "alpha": vector(1.0, 0.0),
            "near alpha": vector(0.9, 0.1),
            "beta": vector(0.0, 1.0),
        }
        return [mapping[text] for text in texts]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if text != "find alpha":
            raise ValueError(
                f"Unexpected test query: {text}"
            )

        return vector(1.0, 0.0)


class PostgreSQLVectorSearchIntegrationTests(
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

        if not database_url.startswith(
            "postgresql"
        ):
            raise unittest.SkipTest(
                "PostgreSQL integration test requires "
                "a PostgreSQL OAI_DATABASE_URL."
            )

        cls.engine = create_database_engine(
            database_url
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.connection = self.engine.connect()
        self.transaction = (
            self.connection.begin()
        )
        self.session = Session(
            bind=self.connection,
            autoflush=False,
            expire_on_commit=False,
        )

    def tearDown(self) -> None:
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def test_pgvector_indexes_and_ranks_chunks(
        self,
    ) -> None:
        now = datetime.now(timezone.utc)
        document_id = str(uuid4())

        document = Document(
            id=document_id,
            source_path=(
                f"integration/{document_id}.txt"
            ),
            file_name="vector-test.txt",
            file_extension=".txt",
            mime_type="text/plain",
            file_size=100,
            content_hash="a" * 64,
            status="indexed",
            created_at=now,
            updated_at=now,
            indexed_at=now,
        )

        chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=0,
                content="alpha",
                source_locator="chunk:0",
                created_at=now,
            ),
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=1,
                content="near alpha",
                source_locator="chunk:1",
                created_at=now,
            ),
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=2,
                content="beta",
                source_locator="chunk:2",
                created_at=now,
            ),
        ]

        self.session.add(document)
        self.session.add_all(chunks)
        self.session.flush()

        adapter = PostgreSQLVectorSearchAdapter(
            self.session,
            FakeEmbeddingProvider(),
        )

        adapter.index_chunks(
            document_id,
            chunks,
        )

        results = adapter.search(
            "find alpha",
            limit=3,
        )

        self.assertEqual(
            len(results),
            3,
        )

        self.assertEqual(
            [
                result["content"]
                for result in results
            ],
            [
                "alpha",
                "near alpha",
                "beta",
            ],
        )

        self.assertGreater(
            results[0]["relevance_score"],
            results[1]["relevance_score"],
        )

        self.assertGreater(
            results[1]["relevance_score"],
            results[2]["relevance_score"],
        )

        adapter.delete_document(
            document_id
        )
        self.session.flush()

        remaining = adapter.search(
            "find alpha",
            limit=3,
        )

        self.assertEqual(
            remaining,
            [],
        )


if __name__ == "__main__":
    unittest.main()