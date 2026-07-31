from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Validated input for a chat turn."""

    message: str = Field(min_length=1, max_length=4_000)


class ChatResponse(BaseModel):
    """Stable response contract for a chat turn."""

    reply: str
