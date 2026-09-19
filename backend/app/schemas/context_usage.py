from datetime import datetime

from pydantic import BaseModel

from app.contracts.context_usage import ContextUsage


class ContextUsageResponse(BaseModel):
    """D99 additive read-only Context transparency response."""

    captured_at: datetime
    total_items: int
    conversation_items: int
    project_items: int
    memory_items: int
    knowledge_items: int

    @classmethod
    def from_usage(cls, usage: ContextUsage) -> "ContextUsageResponse":
        if not isinstance(usage, ContextUsage):
            raise ValueError("context_usage_invalid")
        return cls(
            captured_at=usage.captured_at,
            total_items=usage.total_items,
            conversation_items=usage.conversation_items,
            project_items=usage.project_items,
            memory_items=usage.memory_items,
            knowledge_items=usage.knowledge_items,
        )


__all__ = ["ContextUsageResponse"]
