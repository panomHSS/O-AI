from typing import Any

from pydantic import BaseModel, Field


class ConversationContext(BaseModel):
    """Conversation data for a single intelligence execution."""

    history: list[Any] = Field(default_factory=list)
    project_context: Any | None = None