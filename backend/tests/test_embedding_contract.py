import unittest

from app.embeddings.base import EmbeddingPort


class EmbeddingContractTests(unittest.TestCase):
    def test_embedding_port_exists(
        self,
    ) -> None:
        self.assertIsNotNone(
            EmbeddingPort,
        )

    def test_contract_declares_dimensions(
        self,
    ) -> None:
        self.assertTrue(
            hasattr(
                EmbeddingPort,
                "dimensions",
            )
        )

    def test_contract_declares_query_embedding(
        self,
    ) -> None:
        self.assertTrue(
            hasattr(
                EmbeddingPort,
                "embed_query",
            )
        )

    def test_contract_declares_document_embedding(
        self,
    ) -> None:
        self.assertTrue(
            hasattr(
                EmbeddingPort,
                "embed_documents",
            )
        )


if __name__ == "__main__":
    unittest.main()