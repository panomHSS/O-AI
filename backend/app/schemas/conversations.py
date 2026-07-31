from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StoredCitationResponse(BaseModel):
    id: UUID
    citation_id: str
    order: int
    document_id: UUID
    file_name: str
    source_path: str
    source_locator: str
    excerpt: str
    excerpt_hash: str
    confidence: float
    evidence_type: str


class StoredMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    citations: list[StoredCitationResponse] = Field(default_factory=list)


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: list[StoredMessageResponse]


class DeleteConversationResponse(BaseModel):
    conversation_id: UUID
