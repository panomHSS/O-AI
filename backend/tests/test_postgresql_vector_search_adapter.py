import unittest
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

from app.models.document_chunk_embedding import (
    DocumentChunkEmbedding,
)
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)


class PostgreSQLVectorSearchAdapterTests(unittest.TestCase):
    def test_adapter_exposes_required_operations(self) -> None:
        self.assertTrue(
            hasattr(
                PostgreSQLVectorSearchAdapter,
                "delete_document",
            )
        )
        self.assertTrue(
            hasattr(
                PostgreSQLVectorSearchAdapter,
                "index_chunks",
            )
        )
        self.assertTrue(
            hasattr(
                PostgreSQLVectorSearchAdapter,
                "search",
            )
        )

    def test_empty_chunk_sequence_does_not_embed(self) -> None:
        session = MagicMock()
        embeddings = MagicMock()

        adapter = PostgreSQLVectorSearchAdapter(
            session,
            embeddings,
        )

        adapter.index_chunks(
            "document-id",
            [],
        )

        embeddings.embed_documents.assert_not_called()
        session.add_all.assert_not_called()
        session.flush.assert_not_called()

    def test_index_chunks_embeds_chunk_content(self) -> None:
        session = MagicMock()
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        first_chunk = MagicMock()
        first_chunk.id = "chunk-1"
        first_chunk.content = "first content"

        second_chunk = MagicMock()
        second_chunk.id = "chunk-2"
        second_chunk.content = "second content"

        adapter = PostgreSQLVectorSearchAdapter(
            session,
            embeddings,
        )

        adapter.index_chunks(
            "document-id",
            [
                first_chunk,
                second_chunk,
            ],
        )

        embeddings.embed_documents.assert_called_once_with(
            [
                "first content",
                "second content",
            ]
        )

        stored = session.add_all.call_args.args[0]

        self.assertEqual(
            len(stored),
            2,
        )
        self.assertEqual(
            stored[0].chunk_id,
            "chunk-1",
        )
        self.assertEqual(
            stored[0].document_id,
            "document-id",
        )
        self.assertEqual(
            stored[0].embedding,
            [0.1, 0.2, 0.3],
        )

        session.flush.assert_called_once()

    def test_index_chunks_rejects_embedding_count_mismatch(
        self,
    ) -> None:
        session = MagicMock()
        embeddings = MagicMock()
        embeddings.embed_documents.return_value = []

        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.content = "content"

        adapter = PostgreSQLVectorSearchAdapter(
            session,
            embeddings,
        )

        with self.assertRaises(ValueError):
            adapter.index_chunks(
                "document-id",
                [chunk],
            )

        session.add_all.assert_not_called()

    def test_delete_document_does_not_commit(self) -> None:
        session = MagicMock()
        embeddings = MagicMock()

        adapter = PostgreSQLVectorSearchAdapter(
            session,
            embeddings,
        )

        adapter.delete_document(
            "document-id"
        )

        session.execute.assert_called_once()
        session.commit.assert_not_called()

    def test_vector_column_compiles_for_postgresql(self) -> None:
        compiled = str(
            DocumentChunkEmbedding.__table__.c.embedding.type.compile(
                dialect=postgresql.dialect()
            )
        )

        self.assertEqual(
            compiled,
            "VECTOR(1536)",
        )


if __name__ == "__main__":
    unittest.main()