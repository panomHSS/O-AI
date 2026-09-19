from collections.abc import Sequence
from typing import Protocol

from app.models.document_chunk import DocumentChunk
from app.search.fusion import reciprocal_rank_fusion


SearchRecord = dict[str, object]


class SearchProvider(Protocol):
    def search(
        self,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[SearchRecord]:
        ...


class SemanticSearchProvider(SearchProvider, Protocol):
    def delete_document(
        self,
        document_id: str,
    ) -> None:
        ...

    def index_chunks(
        self,
        document_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        ...


class PostgreSQLHybridSearchAdapter:
    """Combine exact-workspace PostgreSQL semantic and lexical retrieval."""

    def __init__(
        self,
        *,
        semantic: SemanticSearchProvider,
        lexical: SearchProvider,
    ) -> None:
        self._semantic = semantic
        self._lexical = lexical

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        self._semantic.delete_document(document_id)

    def index_chunks(
        self,
        document_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        self._semantic.index_chunks(document_id, chunks)

    def search(
        self,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[SearchRecord]:
        semantic_results = self._semantic.search(
            workspace_id,
            query,
            limit,
        )

        lexical_results = self._lexical.search(
            workspace_id,
            query,
            limit,
        )

        return reciprocal_rank_fusion(
            semantic_results,
            lexical_results,
            limit=limit,
        )
