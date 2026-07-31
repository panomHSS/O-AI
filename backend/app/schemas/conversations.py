from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StoredMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationSummaryResponse):
    messages: list[StoredMessageResponse]


class DeleteConversationResponse(BaseModel):
    conversation_id: UUID
