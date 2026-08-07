from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


class SQLiteFTS5SearchAdapter:
    """SQLite FTS5 implementation of O-AI knowledge search."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        self._session.execute(
            text(
                "DELETE FROM document_chunks_fts "
                "WHERE document_id = :document_id"
            ),
            {"document_id": document_id},
        )

    def index_chunks(
        self,
        document_id: str,
        chunks: Sequence[DocumentChunk],
    ) -> None:
        if not chunks:
            return

        self._session.execute(
            text(
                "INSERT INTO document_chunks_fts "
                "(content, document_id, chunk_id, source_locator) "
                "VALUES "
                "(:content, :document_id, :chunk_id, :source_locator)"
            ),
            [
                {
                    "content": chunk.content,
                    "document_id": document_id,
                    "chunk_id": chunk.id,
                    "source_locator": chunk.source_locator,
                }
                for chunk in chunks
            ],
        )

    def search(
        self,
        match_query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        statement = text(
            "SELECT documents.id AS document_id, "
            "documents.file_name, documents.source_path, "
            "documents.file_extension, "
            "document_chunks.id AS chunk_id, "
            "document_chunks.content, "
            "document_chunks.source_locator, "
            "snippet(document_chunks_fts, 0, '[', ']', '...', 16) "
            "AS excerpt, "
            "-bm25(document_chunks_fts) AS relevance_score "
            "FROM document_chunks_fts "
            "JOIN document_chunks "
            "ON document_chunks.id = document_chunks_fts.chunk_id "
            "JOIN documents "
            "ON documents.id = document_chunks.document_id "
            "WHERE document_chunks_fts MATCH :match_query "
            "AND documents.status = 'indexed' "
            "ORDER BY relevance_score DESC "
            "LIMIT :limit"
        )

        return [
            dict(row)
            for row in self._session.execute(
                statement,
                {
                    "match_query": match_query,
                    "limit": limit,
                },
            ).mappings()
        ]
