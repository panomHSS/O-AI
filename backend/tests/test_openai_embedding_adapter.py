import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.embeddings.openai import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    OpenAIEmbeddingAdapter,
)


class OpenAIEmbeddingAdapterTests(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        with self.assertRaises(EmbeddingConfigurationError):
            OpenAIEmbeddingAdapter(
                api_key=None,
                model="embedding-model",
                dimensions=3,
            )

    def test_requires_model(self) -> None:
        with self.assertRaises(EmbeddingConfigurationError):
            OpenAIEmbeddingAdapter(
                api_key="test-key",
                model=None,
                dimensions=3,
            )

    def test_requires_positive_dimensions(self) -> None:
        with self.assertRaises(EmbeddingConfigurationError):
            OpenAIEmbeddingAdapter(
                api_key="test-key",
                model="embedding-model",
                dimensions=0,
            )

    @patch("app.embeddings.openai.OpenAI")
    def test_exposes_configured_dimensions(
        self,
        openai_class: MagicMock,
    ) -> None:
        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        self.assertEqual(
            adapter.dimensions,
            3,
        )
        openai_class.assert_called_once_with(
            api_key="test-key",
        )

    @patch("app.embeddings.openai.OpenAI")
    def test_embeds_query(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1, 0.2, 0.3],
                )
            ]
        )

        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        result = adapter.embed_query(
            "sugar mill",
        )

        self.assertEqual(
            result,
            [0.1, 0.2, 0.3],
        )
        client.embeddings.create.assert_called_once_with(
            model="embedding-model",
            input=["sugar mill"],
            dimensions=3,
        )

    @patch("app.embeddings.openai.OpenAI")
    def test_embeds_documents(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1, 0.2, 0.3],
                ),
                SimpleNamespace(
                    embedding=[0.4, 0.5, 0.6],
                ),
            ]
        )

        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        result = adapter.embed_documents(
            [
                "first chunk",
                "second chunk",
            ]
        )

        self.assertEqual(
            result,
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ],
        )

    @patch("app.embeddings.openai.OpenAI")
    def test_empty_document_batch_does_not_call_provider(
        self,
        openai_class: MagicMock,
    ) -> None:
        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        result = adapter.embed_documents([])

        self.assertEqual(
            result,
            [],
        )
        openai_class.return_value.embeddings.create.assert_not_called()

    @patch("app.embeddings.openai.OpenAI")
    def test_rejects_unexpected_embedding_dimensions(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1, 0.2],
                )
            ]
        )

        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        with self.assertRaises(EmbeddingProviderError):
            adapter.embed_query(
                "dimension mismatch",
            )

    @patch("app.embeddings.openai.OpenAI")
    def test_rejects_unexpected_result_count(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.embeddings.create.return_value = SimpleNamespace(
            data=[]
        )

        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        with self.assertRaises(EmbeddingProviderError):
            adapter.embed_query(
                "missing embedding",
            )

    @patch("app.embeddings.openai.OpenAI")
    def test_translates_provider_failure(
        self,
        openai_class: MagicMock,
    ) -> None:
        client = openai_class.return_value
        client.embeddings.create.side_effect = RuntimeError(
            "provider failure"
        )

        adapter = OpenAIEmbeddingAdapter(
            api_key="test-key",
            model="embedding-model",
            dimensions=3,
        )

        with self.assertRaises(EmbeddingProviderError):
            adapter.embed_query(
                "test query",
            )


if __name__ == "__main__":
    unittest.main()