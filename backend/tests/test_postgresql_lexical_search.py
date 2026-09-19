from tests.workspace_fixture import TEST_WORKSPACE_ID

import unittest
from unittest.mock import MagicMock

from app.search.postgresql_lexical import (
    PostgreSQLLexicalSearch,
)


class PostgreSQLLexicalSearchTests(unittest.TestCase):
    def test_search_accepts_natural_language_query(
        self,
    ) -> None:
        session = MagicMock()

        rows = MagicMock()
        rows.mappings.return_value = []

        session.execute.return_value = rows

        search = PostgreSQLLexicalSearch(session)

        results = search.search(TEST_WORKSPACE_ID,
            "pump pressure problem",
            10,
        )

        self.assertEqual(results, [])

        statement, parameters = (
            session.execute.call_args.args
        )

        self.assertEqual(
            parameters["query"],
            "pump pressure problem",
        )
        self.assertEqual(
            parameters["limit"],
            10,
        )

        compiled = str(statement)

        self.assertIn(
            "websearch_to_tsquery",
            compiled,
        )
        self.assertIn(
            "to_tsvector",
            compiled,
        )

    def test_search_returns_provider_neutral_records(
        self,
    ) -> None:
        session = MagicMock()

        row = {
            "document_id": "document-1",
            "file_name": "pump.txt",
            "source_path": "pump.txt",
            "file_extension": ".txt",
            "chunk_id": "chunk-1",
            "content": "centrifugal pump pressure problem",
            "source_locator": "section:pump",
            "relevance_score": 0.75,
        }

        rows = MagicMock()
        rows.mappings.return_value = [row]

        session.execute.return_value = rows

        search = PostgreSQLLexicalSearch(session)

        results = search.search(TEST_WORKSPACE_ID,
            "pump pressure",
            5,
        )

        self.assertEqual(
            results,
            [row],
        )

    def test_search_limits_candidates(
        self,
    ) -> None:
        session = MagicMock()

        rows = MagicMock()
        rows.mappings.return_value = []

        session.execute.return_value = rows

        search = PostgreSQLLexicalSearch(session)

        search.search(TEST_WORKSPACE_ID,
            "gearbox vibration",
            7,
        )

        _, parameters = (
            session.execute.call_args.args
        )

        self.assertEqual(
            parameters["limit"],
            7,
        )


if __name__ == "__main__":
    unittest.main()