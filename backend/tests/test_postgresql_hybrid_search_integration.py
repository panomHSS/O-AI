import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.session import create_database_engine
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.search.postgresql_hybrid import (
    PostgreSQLHybridSearchAdapter,
)
from app.search.postgresql_lexical import (
    PostgreSQLLexicalSearch,
)
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
            "hydraulic instability":
                vector(1.0, 0.0),
            "pump pressure problem":
                vector(0.9, 0.1),
            "pump pressure seal":
                vector(0.0, 1.0),
        }

        return [
            mapping[text]
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if text != "pump pressure problem":
            raise ValueError(
                f"Unexpected test query: {text}"
            )

        return vector(1.0, 0.0)


class PostgreSQLHybridSearchIntegrationTests(
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
                "Hybrid integration test requires "
                "PostgreSQL."
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

        if self.transaction.is_active:
            self.transaction.rollback()

        self.connection.close()

    def test_hybrid_search_fuses_semantic_and_lexical_results(
        self,
    ) -> None:
        now = datetime.now(timezone.utc)
        document_id = str(uuid4())

        document = Document(
            id=document_id,
            source_path=(
                f"integration/{document_id}.txt"
            ),
            file_name="hybrid-test.txt",
            file_extension=".txt",
            mime_type="text/plain",
            file_size=100,
            content_hash="b" * 64,
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
                content="hydraulic instability",
                source_locator="semantic-only",
                created_at=now,
            ),
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=1,
                content="pump pressure problem",
                source_locator="shared",
                created_at=now,
            ),
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=2,
                content="pump pressure seal",
                source_locator="lexical-only",
                created_at=now,
            ),
        ]

        self.session.add(document)
        self.session.add_all(chunks)
        self.session.flush()

        semantic = PostgreSQLVectorSearchAdapter(
            self.session,
            FakeEmbeddingProvider(),
        )

        lexical = PostgreSQLLexicalSearch(
            self.session
        )

        hybrid = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )

        hybrid.index_chunks(
            document_id,
            chunks,
        )

        results = hybrid.search(
            "pump pressure problem",
            limit=3,
        )

        chunk_ids = [
            result["chunk_id"]
            for result in results
        ]

        self.assertEqual(
            len(chunk_ids),
            len(set(chunk_ids)),
        )

        locators = [
            result["source_locator"]
            for result in results
        ]

        self.assertEqual(
            locators[0],
            "shared",
        )

        self.assertIn(
            "semantic-only",
            locators,
        )

        self.assertIn(
            "lexical-only",
            locators,
        )


if __name__ == "__main__":
    unittest.main()