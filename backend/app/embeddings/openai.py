import logging
from collections.abc import Sequence

from openai import OpenAI

from app.embeddings.base import EmbeddingVector


logger = logging.getLogger(__name__)


class EmbeddingConfigurationError(RuntimeError):
    """Raised when embedding configuration is incomplete or invalid."""


class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider cannot complete a request."""


class OpenAIEmbeddingAdapter:
    """OpenAI implementation of the O-AI embedding contract."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None,
        dimensions: int,
    ) -> None:
        if not api_key:
            raise EmbeddingConfigurationError(
                "Embeddings are not configured. "
                "Please set OPENAI_API_KEY."
            )

        if not model:
            raise EmbeddingConfigurationError(
                "Embeddings are not configured. "
                "Please set OAI_EMBEDDING_MODEL."
            )

        if dimensions <= 0:
            raise EmbeddingConfigurationError(
                "Embedding dimensions must be positive."
            )

        self._model = model
        self._dimensions = dimensions
        self._client = OpenAI(api_key=api_key)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        vectors = self._embed([text])

        if len(vectors) != 1:
            raise EmbeddingProviderError(
                "Embedding provider returned an unexpected result."
            )

        return vectors[0]

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[EmbeddingVector]:
        if not texts:
            return []

        return self._embed(list(texts))

    def _embed(
        self,
        texts: list[str],
    ) -> list[EmbeddingVector]:
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
        except Exception:
            logger.exception("OpenAI embedding request failed")
            raise EmbeddingProviderError(
                "Embedding service is temporarily unavailable."
            ) from None

        vectors = [
            list(item.embedding)
            for item in response.data
        ]

        if len(vectors) != len(texts):
            raise EmbeddingProviderError(
                "Embedding provider returned an unexpected result."
            )

        if any(
            len(vector) != self._dimensions
            for vector in vectors
        ):
            raise EmbeddingProviderError(
                "Embedding provider returned an unexpected dimension."
            )

        return vectors