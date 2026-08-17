from collections.abc import Sequence
from typing import Protocol

from app.models.document_chunk import DocumentChunk


class KnowledgeSearchPort(Protocol):
    """O-AI-owned contract for derived knowledge search."""

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        """Remove one document from the derived search index."""

    def index_chunks(
        self,
        document_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        """Index authoritative document chunks for search."""

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return ranked knowledge-search results."""
        