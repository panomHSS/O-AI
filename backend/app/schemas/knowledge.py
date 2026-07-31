from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


DocumentStatus = Literal["indexed", "failed", "missing"]


class ScanKnowledgeResponse(BaseModel):
    discovered: int
    indexed: int
    unchanged: int
    unsupported: int
    failed: int


class DocumentSummaryResponse(BaseModel):
    id: UUID
    source_path: str
    file_name: str
    file_extension: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None


class DocumentListResponse(BaseModel):
    items: list[DocumentSummaryResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class DocumentChunkSummary(BaseModel):
    chunk_index: int
    source_locator: str


class DocumentDetailResponse(DocumentSummaryResponse):
    chunk_count: int
    chunks: list[DocumentChunkSummary]


class DeleteDocumentResponse(BaseModel):
    document_id: UUID


class KnowledgeSearchResult(BaseModel):
    document_id: UUID
    file_name: str
    source_path: str
    source_locator: str
    excerpt: str
    relevance_score: float | None = None


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeSearchResult]
    query: str
