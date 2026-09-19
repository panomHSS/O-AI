"""D99 read-only Context usage projection."""

from __future__ import annotations

from app.contracts.context import ContextLayer
from app.contracts.context_provenance import ContextSnapshot
from app.contracts.context_usage import ContextUsage
from app.repositories.context_snapshots import ContextSnapshotRepository


def context_usage_from_snapshot(snapshot: ContextSnapshot) -> ContextUsage:
    """Project an already verified D96 snapshot into fixed layer counts."""

    if not isinstance(snapshot, ContextSnapshot):
        raise ValueError("context_snapshot_invalid")

    counts = {layer: 0 for layer in ContextLayer}
    for snapshot_item in snapshot.items:
        counts[snapshot_item.item.source.layer] += 1

    return ContextUsage(
        captured_at=snapshot.captured_at,
        total_items=len(snapshot.items),
        conversation_items=counts[ContextLayer.CONVERSATION],
        project_items=counts[ContextLayer.PROJECT],
        memory_items=counts[ContextLayer.MEMORY],
        knowledge_items=counts[ContextLayer.KNOWLEDGE],
    )


def context_usage_for_message(
    repository: ContextSnapshotRepository,
    message_id: str,
) -> ContextUsage | None:
    """Read one exact-workspace summary without materializing Context text."""

    return repository.get_usage_for_message(message_id)


__all__ = [
    "context_usage_for_message",
    "context_usage_from_snapshot",
]
