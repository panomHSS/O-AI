import unittest
from unittest.mock import MagicMock

from app.search.postgresql_hybrid import (
    PostgreSQLHybridSearchAdapter,
)


class PostgreSQLHybridSearchAdapterTests(
    unittest.TestCase
):
    def test_search_combines_semantic_and_lexical_results(
        self,
    ) -> None:
        semantic = MagicMock()
        lexical = MagicMock()

        semantic.search.return_value = [
            {
                "chunk_id": "semantic-only",
                "content": "semantic result",
            },
            {
                "chunk_id": "both",
                "content": "shared result",
            },
        ]

        lexical.search.return_value = [
            {
                "chunk_id": "both",
                "content": "shared result",
            },
            {
                "chunk_id": "lexical-only",
                "content": "lexical result",
            },
        ]

        adapter = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )

        results = adapter.search(
            "pump pressure problem",
            3,
        )

        semantic.search.assert_called_once_with(
            "pump pressure problem",
            3,
        )
        lexical.search.assert_called_once_with(
            "pump pressure problem",
            3,
        )

        self.assertEqual(
            results[0]["chunk_id"],
            "both",
        )

        self.assertEqual(
            {
                result["chunk_id"]
                for result in results
            },
            {
                "both",
                "semantic-only",
                "lexical-only",
            },
        )

    def test_indexing_delegates_to_semantic_provider(
        self,
    ) -> None:
        semantic = MagicMock()
        lexical = MagicMock()

        adapter = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )

        chunks = [
            MagicMock(),
            MagicMock(),
        ]

        adapter.index_chunks(
            "document-1",
            chunks,
        )

        semantic.index_chunks.assert_called_once_with(
            "document-1",
            chunks,
        )

    def test_delete_delegates_to_semantic_provider(
        self,
    ) -> None:
        semantic = MagicMock()
        lexical = MagicMock()

        adapter = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )

        adapter.delete_document(
            "document-1"
        )

        semantic.delete_document.assert_called_once_with(
            "document-1"
        )

    def test_search_limit_is_applied_after_fusion(
        self,
    ) -> None:
        semantic = MagicMock()
        lexical = MagicMock()

        semantic.search.return_value = [
            {"chunk_id": "a"},
            {"chunk_id": "b"},
        ]

        lexical.search.return_value = [
            {"chunk_id": "c"},
            {"chunk_id": "d"},
        ]

        adapter = PostgreSQLHybridSearchAdapter(
            semantic=semantic,
            lexical=lexical,
        )

        results = adapter.search(
            "gearbox vibration",
            2,
        )

        self.assertEqual(
            len(results),
            2,
        )


if __name__ == "__main__":
    unittest.main()