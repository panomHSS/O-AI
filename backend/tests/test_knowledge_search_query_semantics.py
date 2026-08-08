import tempfile
import unittest
from pathlib import Path

from app.services.knowledge import KnowledgeService


class RecordingKnowledgeRepository:
    def __init__(self) -> None:
        self.search_query: str | None = None
        self.search_limit: int | None = None

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        self.search_query = query
        self.search_limit = limit
        return []


class KnowledgeSearchQuerySemanticsTests(
    unittest.TestCase
):
    def test_service_passes_normalized_natural_query(
        self,
    ) -> None:
        repository = RecordingKnowledgeRepository()

        with tempfile.TemporaryDirectory() as directory:
            service = KnowledgeService(
                repository,
                readers=None,
                root=Path(directory),
                max_file_size_mb=1,
                chunk_size=100,
                chunk_overlap=10,
            )

            response = service.search(
                "pump   pressure problem",
                7,
            )

        self.assertEqual(
            repository.search_query,
            "pump pressure problem",
        )
        self.assertEqual(
            repository.search_limit,
            7,
        )
        self.assertEqual(
            response.query,
            "pump pressure problem",
        )


if __name__ == "__main__":
    unittest.main()