from typing import Any

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryReference


class ConversationContext(BaseModel):
    """Conversation data for a single intelligence execution."""

    history: list[Any] = Field(default_factory=list)

    memories: list[MemoryReference] = Field(
        default_factory=list,
    )

    project_context: Any | None = None