from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, delete, func, select, text
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.readers.base import SourceSection


class KnowledgeRepository:
    """SQLAlchemy and SQLite FTS operations for local document knowledge."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, source_path: str) -> Document | None:
        statement: Select[tuple[Document]] = select(Document).where(Document.source_path == source_path).options(selectinload(Document.chunks))
        return self._session.scalar(statement)

    def get(self, document_id: str) -> Document | None:
        statement: Select[tuple[Document]] = select(Document).where(Document.id == document_id).options(selectinload(Document.chunks))
        return self._session.scalar(statement)

    def list(self, page: int, page_size: int, status: str | None) -> tuple[Sequence[Document], int]:
        filters = [Document.status == status] if status else []
        statement: Select[tuple[Document]] = select(Document).where(*filters).order_by(Document.updated_at.desc(), Document.id.desc()).offset((page - 1) * page_size).limit(page_size)
        total = self._session.scalar(select(func.count(Document.id)).where(*filters)) or 0
        return self._session.scalars(statement).all(), total

    def create_failed(self, metadata: dict[str, object], error_message: str) -> Document:
        document = Document(**metadata, status="failed", error_message=error_message, indexed_at=None)
        self._session.add(document)
        self._session.flush()
        return document

    def replace_index(self, document: Document | None, metadata: dict[str, object], sections: list[SourceSection], indexed_at: datetime) -> Document:
        target = document or Document(**metadata, status="indexed", error_message=None, indexed_at=indexed_at)
        if document is not None:
            for key, value in metadata.items():
                setattr(target, key, value)
            target.status = "indexed"
            target.error_message = None
            target.indexed_at = indexed_at
            self._session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == target.id))
            self._session.execute(text("DELETE FROM document_chunks_fts WHERE document_id = :document_id"), {"document_id": target.id})
        else:
            self._session.add(target)
            self._session.flush()

        chunks = [DocumentChunk(document_id=target.id, chunk_index=index, content=section.text, source_locator=section.source_locator) for index, section in enumerate(sections)]
        self._session.add_all(chunks)
        self._session.flush()
        self._session.execute(
            text("INSERT INTO document_chunks_fts (content, document_id, chunk_id, source_locator) VALUES (:content, :document_id, :chunk_id, :source_locator)"),
            [{"content": chunk.content, "document_id": target.id, "chunk_id": chunk.id, "source_locator": chunk.source_locator} for chunk in chunks],
        )
        return target

    def record_failure(self, document: Document | None, metadata: dict[str, object], error_message: str) -> None:
        if document is None:
            self.create_failed(metadata, error_message)
        else:
            document.error_message = error_message
            if document.status != "indexed":
                document.status = "failed"

    def mark_missing(self, discovered_paths: set[str]) -> None:
        documents = self._session.scalars(select(Document).where(Document.status == "indexed")).all()
        for document in documents:
            if document.source_path not in discovered_paths:
                document.status = "missing"
                document.error_message = "Source file is no longer available under the knowledge root."

    def search(self, match_query: str, limit: int) -> list[dict[str, object]]:
        statement = text(
            "SELECT documents.id AS document_id, documents.file_name, documents.source_path, "
            "document_chunks.source_locator, snippet(document_chunks_fts, 0, '[', ']', '...', 16) AS excerpt, "
            "-bm25(document_chunks_fts) AS relevance_score "
            "FROM document_chunks_fts "
            "JOIN document_chunks ON document_chunks.id = document_chunks_fts.chunk_id "
            "JOIN documents ON documents.id = document_chunks.document_id "
            "WHERE document_chunks_fts MATCH :match_query AND documents.status = 'indexed' "
            "ORDER BY relevance_score DESC LIMIT :limit"
        )
        return [dict(row) for row in self._session.execute(statement, {"match_query": match_query, "limit": limit}).mappings()]

    def delete(self, document: Document) -> None:
        self._session.execute(text("DELETE FROM document_chunks_fts WHERE document_id = :document_id"), {"document_id": document.id})
        self._session.delete(document)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()
