from uuid import UUID

from pydantic import BaseModel


class RequestContext(BaseModel):
    """Request metadata for a single intelligence execution."""

    request_id: str
    question: str
    conversation_id: UUID | None = None
    project_id: UUID | None = None