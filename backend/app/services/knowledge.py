import hashlib
import logging
import mimetypes
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.db.base import utc_now
from app.models.document import Document
from app.readers.base import DocumentExtractionError, SourceSection
from app.readers.registry import DocumentReaderRegistry
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    DocumentChunkSummary, DocumentDetailResponse, DocumentListResponse, DocumentSummaryResponse,
    KnowledgeSearchResponse, KnowledgeSearchResult,
)

logger = logging.getLogger(__name__)


class KnowledgeDocumentNotFoundError(Exception):
    pass


class KnowledgeRootUnavailableError(Exception):
    pass


class KnowledgeScanConflictError(Exception):
    pass


class KnowledgeSearchValidationError(Exception):
    pass


@dataclass(frozen=True)
class ScanCounts:
    discovered: int = 0
    indexed: int = 0
    unchanged: int = 0
    unsupported: int = 0
    failed: int = 0


class KnowledgeService:
    """Coordinates safe local discovery, reader extraction, and SQLite indexing."""

    _scan_lock = threading.Lock()

    def __init__(self, repository: KnowledgeRepository, readers: DocumentReaderRegistry, root: str, max_file_size_mb: int, chunk_size: int, chunk_overlap: int) -> None:
        self._repository = repository
        self._readers = readers
        self._root = Path(root)
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def scan(self) -> ScanCounts:
        if not self._scan_lock.acquire(blocking=False):
            raise KnowledgeScanConflictError("A knowledge scan is already in progress.")
        try:
            root = self._resolve_root()
            discovered_paths: set[str] = set()
            counts = ScanCounts()
            for path in self._discover(root):
                source_path = path.relative_to(root).as_posix()
                discovered_paths.add(source_path)
                counts = ScanCounts(**{**counts.__dict__, "discovered": counts.discovered + 1})
                reader = self._readers.get(path)
                if reader is None:
                    counts = ScanCounts(**{**counts.__dict__, "unsupported": counts.unsupported + 1})
                    continue
                if path.stat().st_size > self._max_file_size:
                    self._record_failure(path, source_path, "The file exceeds the configured maximum size.", current=None)
                    counts = ScanCounts(**{**counts.__dict__, "failed": counts.failed + 1})
                    continue
                content_hash = self._hash_file(path)
                current = self._repository.get_by_path(source_path)
                if current is not None and current.content_hash == content_hash and current.status == "indexed":
                    counts = ScanCounts(**{**counts.__dict__, "unchanged": counts.unchanged + 1})
                    continue
                try:
                    sections = reader.extract(path)
                    chunks = self._chunk_sections(sections)
                    if not chunks:
                        raise DocumentExtractionError("The document produced no indexable text.")
                    self._repository.replace_index(current, self._metadata(path, source_path, content_hash), chunks, utc_now())
                    self._repository.commit()
                    counts = ScanCounts(**{**counts.__dict__, "indexed": counts.indexed + 1})
                except Exception as error:
                    self._repository.rollback()
                    logger.warning("Knowledge extraction failed for %s", source_path, exc_info=error)
                    self._record_failure(path, source_path, self._safe_error(error), current=current)
                    counts = ScanCounts(**{**counts.__dict__, "failed": counts.failed + 1})
            self._repository.mark_missing(discovered_paths)
            self._repository.commit()
            return counts
        except Exception:
            self._repository.rollback()
            raise
        finally:
            self._scan_lock.release()

    def list_documents(self, page: int, page_size: int, status: str | None) -> DocumentListResponse:
        documents, total = self._repository.list(page, page_size, status)
        return DocumentListResponse(items=[self._summary(document) for document in documents], page=page, page_size=page_size, total=total)

    def get_document(self, document_id: UUID) -> DocumentDetailResponse:
        document = self._require_document(document_id)
        chunks = sorted(document.chunks, key=lambda item: item.chunk_index)
        return DocumentDetailResponse(**self._summary(document).model_dump(), chunk_count=len(chunks), chunks=[DocumentChunkSummary(chunk_index=item.chunk_index, source_locator=item.source_locator) for item in chunks])

    def delete_document(self, document_id: UUID) -> None:
        document = self._require_document(document_id)
        try:
            self._repository.delete(document)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def search(self, query: str, limit: int) -> KnowledgeSearchResponse:
        terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
        if not terms:
            raise KnowledgeSearchValidationError("Search query must contain letters or numbers.")
        match_query = " AND ".join(f'"{term}"' for term in terms)
        try:
            records = self._repository.search(match_query, limit)
        except Exception as error:
            logger.warning("Knowledge search query failed", exc_info=error)
            raise KnowledgeSearchValidationError("Search query could not be processed.") from None
        return KnowledgeSearchResponse(query=" ".join(terms), items=[KnowledgeSearchResult(**record) for record in records])

    def _record_failure(self, path: Path, source_path: str, message: str, current: Document | None = None) -> None:
        current = current or self._repository.get_by_path(source_path)
        try:
            content_hash = current.content_hash if current is not None else hashlib.sha256(f"unindexed:{source_path}".encode()).hexdigest()
            self._repository.record_failure(current, self._metadata(path, source_path, content_hash), message)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _resolve_root(self) -> Path:
        root = self._root.resolve(strict=False)
        if not root.is_dir():
            raise KnowledgeRootUnavailableError("The configured knowledge folder is not available.")
        return root

    def _discover(self, root: Path):
        for candidate in root.rglob("*"):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                resolved = candidate.resolve(strict=True)
                relative = resolved.relative_to(root)
            except (OSError, ValueError):
                continue
            if any(part.startswith(".") for part in relative.parts):
                continue
            if resolved.suffix.lower() in {".db", ".sqlite", ".wal", ".shm"}:
                continue
            yield resolved

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _metadata(path: Path, source_path: str, content_hash: str) -> dict[str, object]:
        mime_type, _ = mimetypes.guess_type(path.name)
        return {"source_path": source_path, "file_name": path.name, "file_extension": path.suffix.lower(), "mime_type": mime_type or "application/octet-stream", "file_size": path.stat().st_size, "content_hash": content_hash}

    def _chunk_sections(self, sections: list[SourceSection]) -> list[SourceSection]:
        chunks: list[SourceSection] = []
        for section in sorted(sections, key=lambda item: item.sequence):
            text = self._normalize(section.text)
            if not text:
                continue
            if section.metadata.get("atomic") == "true":
                chunks.append(SourceSection(section.sequence, text, section.source_locator))
                continue
            start = 0
            while start < len(text):
                end = min(len(text), start + self._chunk_size)
                if end < len(text):
                    natural_break = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
                    if natural_break > start:
                        end = natural_break
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(SourceSection(section.sequence, chunk, section.source_locator))
                if end >= len(text):
                    break
                start = max(end - self._chunk_overlap, start + 1)
        return chunks

    @staticmethod
    def _normalize(text: str) -> str:
        return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip()).strip()

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, DocumentExtractionError):
            return str(error)
        return "Unable to index this document."

    def _require_document(self, document_id: UUID) -> Document:
        document = self._repository.get(str(document_id))
        if document is None:
            raise KnowledgeDocumentNotFoundError("The requested document was not found.")
        return document

    @staticmethod
    def _summary(document: Document) -> DocumentSummaryResponse:
        return DocumentSummaryResponse(id=UUID(document.id), source_path=document.source_path, file_name=document.file_name, file_extension=document.file_extension, mime_type=document.mime_type, file_size=document.file_size, status=document.status, error_message=document.error_message, created_at=document.created_at, updated_at=document.updated_at, indexed_at=document.indexed_at)
