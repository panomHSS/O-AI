from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.embeddings.base import EmbeddingPort
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_chunk_embedding import DocumentChunkEmbedding


class PostgreSQLVectorSearchAdapter:
    """PostgreSQL pgvector workspace-scoped knowledge search."""

    def __init__(
        self,
        session: Session,
        embeddings: EmbeddingPort,
    ) -> None:
        self._session = session
        self._embeddings = embeddings

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        self._session.execute(
            delete(DocumentChunkEmbedding).where(
                DocumentChunkEmbedding.document_id == document_id
            )
        )

    def index_chunks(
        self,
        document_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        if not chunks:
            return

        vectors = self._embeddings.embed_documents(
            [chunk.content for chunk in chunks]
        )

        if len(vectors) != len(chunks):
            raise ValueError(
                "Embedding count does not match chunk count."
            )

        self._session.add_all(
            [
                DocumentChunkEmbedding(
                    chunk_id=chunk.id,
                    document_id=document_id,
                    embedding=vector,
                )
                for chunk, vector in zip(
                    chunks,
                    vectors,
                    strict=True,
                )
            ]
        )

        self._session.flush()

    def search(
        self,
        workspace_id: str,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        query_vector = self._embeddings.embed_query(query)

        distance = (
            DocumentChunkEmbedding.embedding.cosine_distance(
                query_vector
            )
        )

        statement = (
            select(
                Document.id.label("document_id"),
                Document.file_name,
                Document.source_path,
                Document.file_extension,
                DocumentChunk.id.label("chunk_id"),
                DocumentChunk.content,
                DocumentChunk.source_locator,
                distance.label("distance"),
            )
            .join(
                DocumentChunk,
                DocumentChunk.document_id == Document.id,
            )
            .join(
                DocumentChunkEmbedding,
                DocumentChunkEmbedding.chunk_id == DocumentChunk.id,
            )
            .where(
                Document.status == "indexed",
                Document.workspace_id == workspace_id,
            )
            .order_by(distance.asc())
            .limit(limit)
        )

        rows = self._session.execute(statement).mappings()

        return [
            {
                "document_id": row["document_id"],
                "file_name": row["file_name"],
                "source_path": row["source_path"],
                "file_extension": row["file_extension"],
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "source_locator": row["source_locator"],
                "excerpt": row["content"],
                "relevance_score": 1.0 - float(row["distance"]),
            }
            for row in rows
        ]
