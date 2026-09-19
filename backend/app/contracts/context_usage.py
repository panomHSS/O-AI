"""D99 read-only Context usage contract.

Context usage is transparency metadata only. It grants no command, approval,
authorization, credential, connector, AI-provider, cloud-egress, or execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ContextUsage:
    """Read-only layer counts for one exact persisted D97 snapshot."""

    captured_at: datetime
    total_items: int
    conversation_items: int
    project_items: int
    memory_items: int
    knowledge_items: int

    def __post_init__(self) -> None:
        offset = (
            self.captured_at.utcoffset()
            if isinstance(self.captured_at, datetime)
            else None
        )
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("context_usage_captured_at_invalid")

        values = (
            self.total_items,
            self.conversation_items,
            self.project_items,
            self.memory_items,
            self.knowledge_items,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in values
        ):
            raise ValueError("context_usage_count_invalid")

        if self.total_items != sum(values[1:]):
            raise ValueError("context_usage_total_mismatch")


__all__ = ["ContextUsage"]
