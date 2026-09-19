"""D96 verify-before-freeze Context snapshot capture."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.contracts.context import ContextBundle, ContextLayer
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotClock,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.services.context_provenance_sources import (
    ContextProvenanceSourceError,
    ContextSourceObservation,
    ConversationProvenanceSourcePort,
    KnowledgeProvenanceSourcePort,
    MemoryProvenanceSourcePort,
    ProjectProvenanceSourcePort,
)


class ContextSnapshotError(Exception):
    """Bounded D96 snapshot capture failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ContextSnapshotService:
    """Verify authoritative source truth and freeze one immutable snapshot."""

    def __init__(
        self,
        *,
        conversation_source: ConversationProvenanceSourcePort,
        project_source: ProjectProvenanceSourcePort,
        memory_source: MemoryProvenanceSourcePort,
        knowledge_source: KnowledgeProvenanceSourcePort,
        clock: ContextSnapshotClock,
    ) -> None:
        self._conversation_source = conversation_source
        self._project_source = project_source
        self._memory_source = memory_source
        self._knowledge_source = knowledge_source
        self._clock = clock

    def capture(self, bundle: ContextBundle) -> ContextSnapshot:
        if not isinstance(bundle, ContextBundle):
            raise ContextSnapshotError("context_snapshot_invalid")

        frozen: list[ContextSnapshotItem] = []

        for item in bundle.items:
            source = self._source_for(item.source.layer)
            try:
                observation = source.observe(item)
            except ContextProvenanceSourceError as error:
                raise ContextSnapshotError(error.code) from None
            except Exception:
                raise ContextSnapshotError(
                    "context_snapshot_source_unavailable"
                ) from None

            self._verify_observation(
                bundle=bundle,
                item=item,
                observation=observation,
            )

            try:
                provenance = ContextSourceProvenance(
                    source=item.source,
                    content_sha256=context_text_sha256(item.text),
                    parent_source_id=observation.parent_source_id,
                    version_ref=observation.version_ref,
                    source_locator=observation.source_locator,
                    source_timestamp=observation.source_timestamp,
                )
                frozen.append(
                    ContextSnapshotItem(
                        item=item,
                        provenance=provenance,
                    )
                )
            except ValueError as error:
                if "timestamp" in str(error):
                    raise ContextSnapshotError(
                        "context_snapshot_timestamp_invalid"
                    ) from None
                raise ContextSnapshotError(
                    "context_snapshot_invalid"
                ) from None

        captured_at = self._capture_time()
        items = tuple(frozen)

        try:
            digest = compute_context_snapshot_digest(
                workspace_scope=bundle.workspace_scope,
                captured_at=captured_at,
                items=items,
            )
            return ContextSnapshot(
                workspace_scope=bundle.workspace_scope,
                captured_at=captured_at,
                items=items,
                snapshot_digest=digest,
            )
        except ValueError:
            raise ContextSnapshotError("context_snapshot_invalid") from None

    def _source_for(self, layer: ContextLayer) -> object:
        if layer is ContextLayer.CONVERSATION:
            return self._conversation_source
        if layer is ContextLayer.PROJECT:
            return self._project_source
        if layer is ContextLayer.MEMORY:
            return self._memory_source
        if layer is ContextLayer.KNOWLEDGE:
            return self._knowledge_source
        raise ContextSnapshotError("context_snapshot_source_mismatch")

    @staticmethod
    def _verify_observation(
        *,
        bundle: ContextBundle,
        item: object,
        observation: object,
    ) -> None:
        from app.contracts.context import ContextItem

        if not isinstance(item, ContextItem):
            raise ContextSnapshotError("context_snapshot_invalid")
        if not isinstance(observation, ContextSourceObservation):
            raise ContextSnapshotError("context_snapshot_source_mismatch")
        if observation.source != item.source:
            raise ContextSnapshotError("context_snapshot_source_mismatch")
        if (
            observation.source.workspace_id
            is not bundle.workspace_scope.workspace_id
        ):
            raise ContextSnapshotError("context_snapshot_source_mismatch")
        if (
            observation.text != item.text
            or observation.label != item.label
        ):
            raise ContextSnapshotError("context_snapshot_source_changed")

    def _capture_time(self) -> datetime:
        try:
            value = self._clock.now_utc()
        except Exception:
            raise ContextSnapshotError(
                "context_snapshot_timestamp_invalid"
            ) from None

        if not isinstance(value, datetime):
            raise ContextSnapshotError(
                "context_snapshot_timestamp_invalid"
            )
        offset = value.utcoffset()
        if offset is None or offset != timedelta(0):
            raise ContextSnapshotError(
                "context_snapshot_timestamp_invalid"
            )
        return value


__all__ = [
    "ContextSnapshotError",
    "ContextSnapshotService",
]
