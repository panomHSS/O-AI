import unittest

from app.search.base import KnowledgeSearchPort


class KnowledgeSearchContractTests(unittest.TestCase):
    def test_knowledge_search_port_exists(
        self,
    ) -> None:
        self.assertIsNotNone(
            KnowledgeSearchPort,
        )

    def test_contract_declares_required_operations(
        self,
    ) -> None:
        self.assertTrue(
            hasattr(
                KnowledgeSearchPort,
                "delete_document",
            )
        )
        self.assertTrue(
            hasattr(
                KnowledgeSearchPort,
                "index_chunks",
            )
        )
        self.assertTrue(
            hasattr(
                KnowledgeSearchPort,
                "search",
            )
        )


if __name__ == "__main__":
    unittest.main()
