from collections.abc import Sequence
from typing import Protocol


EmbeddingVector = list[float]


class EmbeddingPort(Protocol):
    """O-AI-owned contract for converting text into embedding vectors."""

    @property
    def dimensions(self) -> int:
        """Return the fixed number of dimensions produced by this provider."""
        ...

    def embed_query(
        self,
        text: str,
    ) -> EmbeddingVector:
        """Create one embedding vector for a search query."""
        ...

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[EmbeddingVector]:
        """Create embedding vectors for document content."""
        ...