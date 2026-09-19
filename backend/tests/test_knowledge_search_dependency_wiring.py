from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import unittest
from unittest.mock import MagicMock, patch

from app.api.dependencies import (
    get_knowledge_repository,
)
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)
from app.search.sqlite_fts5 import (
    SQLiteFTS5SearchAdapter,
)
from app.search.postgresql_hybrid import (
    PostgreSQLHybridSearchAdapter,
)
from app.search.postgresql_lexical import (
    PostgreSQLLexicalSearch,
)


class KnowledgeSearchDependencyWiringTests(
    unittest.TestCase
):
    def _session_with_dialect(
        self,
        dialect_name: str,
    ) -> MagicMock:
        session = MagicMock()
        session.get_bind.return_value.dialect.name = (
            dialect_name
        )
        return session

    @patch(
        "app.api.dependencies.get_embedding_provider"
    )
    def test_sqlite_does_not_create_embedding_provider(
        self,
        get_embedding_provider: MagicMock,
    ) -> None:
        session = self._session_with_dialect(
            "sqlite"
        )

        repository = get_knowledge_repository(session, TEST_WORKSPACE_SCOPE)

        get_embedding_provider.assert_not_called()

        self.assertIsInstance(
            repository._search,
            SQLiteFTS5SearchAdapter,
        )

    @patch(
        "app.api.dependencies.get_embedding_provider"
    )
    def test_postgresql_creates_embedding_provider(
        self,
        get_embedding_provider: MagicMock,
    ) -> None:
        session = self._session_with_dialect(
            "postgresql"
        )
        embeddings = MagicMock()

        get_embedding_provider.return_value = embeddings

        repository = get_knowledge_repository(session, TEST_WORKSPACE_SCOPE)

        get_embedding_provider.assert_called_once_with()

        self.assertIsInstance(
            repository._search,
            PostgreSQLHybridSearchAdapter,
        )

        self.assertIsInstance(
            repository._search._semantic,
            PostgreSQLVectorSearchAdapter,
        )

        self.assertIsInstance(
            repository._search._lexical,
            PostgreSQLLexicalSearch,
        )

        self.assertIs(
            repository._search._semantic._embeddings,
            embeddings,
        )

if __name__ == "__main__":
    unittest.main()