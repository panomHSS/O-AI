import unittest
from unittest.mock import MagicMock

from app.search.factory import (
    create_knowledge_search,
)
from app.search.postgresql_vector import (
    PostgreSQLVectorSearchAdapter,
)
from app.search.sqlite_fts5 import (
    SQLiteFTS5SearchAdapter,
)


class KnowledgeSearchFactoryTests(
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

    def test_creates_sqlite_adapter(self) -> None:
        session = self._session_with_dialect(
            "sqlite"
        )

        search = create_knowledge_search(
            session
        )

        self.assertIsInstance(
            search,
            SQLiteFTS5SearchAdapter,
        )

    def test_creates_postgresql_adapter(
        self,
    ) -> None:
        session = self._session_with_dialect(
            "postgresql"
        )
        embeddings = MagicMock()

        search = create_knowledge_search(
            session,
            embeddings=embeddings,
        )

        self.assertIsInstance(
            search,
            PostgreSQLVectorSearchAdapter,
        )

    def test_postgresql_requires_embeddings(
        self,
    ) -> None:
        session = self._session_with_dialect(
            "postgresql"
        )

        with self.assertRaisesRegex(
            ValueError,
            "requires an embedding provider",
        ):
            create_knowledge_search(
                session
            )

    def test_rejects_unsupported_dialect(
        self,
    ) -> None:
        session = self._session_with_dialect(
            "mysql"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported knowledge-search "
            "database dialect",
        ):
            create_knowledge_search(
                session
            )


if __name__ == "__main__":
    unittest.main()