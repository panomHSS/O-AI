"""D96 exact-workspace read-only provenance source observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.workspace import WorkspaceScope
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.memory import Memory
from app.models.memory_version import MemoryVersion
from app.models.message import Message
from app.models.project import Project
from app.services.context_sources import (
    conversation_context_projection,
    knowledge_context_projection,
    memory_context_projection,
    project_context_projection,
)
from app.services.memory_resolver import (
    decode_memory_context_value,
    memory_context_key_is_valid,
)
from app.services.project_context import (
    ProjectContextRecord,
    ProjectContextResolver,
    ProjectContextUnavailableError,
)


class ContextProvenanceSourceError(Exception):
    """Bounded D96 source observation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ContextSourceObservation:
    """Ephemeral current-source projection used only for D96 verification."""

    source: ContextSourceRef
    text: str
    label: str | None
    parent_source_id: str | None
    version_ref: str | None
    source_locator: str | None
    source_timestamp: datetime | None

    def __post_init__(self) -> None:
        ContextItem(
            source=self.source,
            text=self.text,
            label=self.label,
        )


class ConversationProvenanceSourcePort(Protocol):
    def observe(self, item: ContextItem) -> ContextSourceObservation: ...


class ProjectProvenanceSourcePort(Protocol):
    def observe(self, item: ContextItem) -> ContextSourceObservation: ...


class MemoryProvenanceSourcePort(Protocol):
    def observe(self, item: ContextItem) -> ContextSourceObservation: ...


class KnowledgeProvenanceSourcePort(Protocol):
    def observe(self, item: ContextItem) -> ContextSourceObservation: ...


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("source_timestamp_invalid")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class _BaseProvenanceSource:
    def __init__(
        self,
        session: Session,
        workspace_scope: WorkspaceScope,
    ) -> None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value
        self._workspace_enum = workspace_scope.workspace_id

    def _require_item(
        self,
        item: ContextItem,
        layer: ContextLayer,
    ) -> None:
        if not isinstance(item, ContextItem):
            raise ContextProvenanceSourceError(
                "context_snapshot_source_mismatch"
            )
        if (
            item.source.workspace_id is not self._workspace_enum
            or item.source.layer is not layer
        ):
            raise ContextProvenanceSourceError(
                "context_snapshot_source_mismatch"
            )


class ConversationProvenanceSource(_BaseProvenanceSource):
    """Re-observe one persisted Message through its exact-workspace root."""

    def observe(self, item: ContextItem) -> ContextSourceObservation:
        self._require_item(item, ContextLayer.CONVERSATION)
        try:
            row = self._session.execute(
                select(
                    Message.id,
                    Message.conversation_id,
                    Message.role,
                    Message.content,
                    Message.created_at,
                )
                .join(
                    Conversation,
                    Conversation.id == Message.conversation_id,
                )
                .where(
                    Message.id == item.source.source_id,
                    Conversation.workspace_id == self._workspace_id,
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        if row is None:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            )
        try:
            text, label = conversation_context_projection(
                row["role"],
                row["content"],
            )
            timestamp = _utc(row["created_at"])
        except (TypeError, UnicodeError, ValueError) as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        return ContextSourceObservation(
            source=item.source,
            text=text,
            label=label,
            parent_source_id=row["conversation_id"],
            version_ref=None,
            source_locator=None,
            source_timestamp=timestamp,
        )


class _StaticProjectReader:
    def __init__(
        self,
        project_id: str,
        record: ProjectContextRecord,
    ) -> None:
        self._project_id = project_id
        self._record = record

    def get_current(
        self,
        project_id: str,
    ) -> ProjectContextRecord | None:
        if project_id != self._project_id:
            return None
        return self._record


class ProjectProvenanceSource(_BaseProvenanceSource):
    """Re-observe one current Project under the exact workspace."""

    def observe(self, item: ContextItem) -> ContextSourceObservation:
        self._require_item(item, ContextLayer.PROJECT)
        try:
            row = self._session.execute(
                select(
                    Project.id,
                    Project.title,
                    Project.objective,
                    Project.status,
                    Project.current_summary,
                    Project.next_action,
                    Project.current_revision,
                    Project.updated_at,
                ).where(
                    Project.id == item.source.source_id,
                    Project.workspace_id == self._workspace_id,
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        if row is None:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            )

        record = ProjectContextRecord(
            title=row["title"],
            objective=row["objective"],
            status=row["status"],
            current_summary=row["current_summary"],
            next_action=row["next_action"],
            current_revision=row["current_revision"],
        )
        try:
            context = ProjectContextResolver(
                _StaticProjectReader(item.source.source_id, record)
            ).resolve(item.source.source_id)
            if context is None:
                raise ValueError("project_context_missing")
            text = project_context_projection(context)
            timestamp = _utc(row["updated_at"])
        except (
            ProjectContextUnavailableError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        return ContextSourceObservation(
            source=item.source,
            text=text,
            label="project_current",
            parent_source_id=None,
            version_ref=str(context.current_revision),
            source_locator=None,
            source_timestamp=timestamp,
        )


class MemoryProvenanceSource(_BaseProvenanceSource):
    """Re-observe one still-active confirmed MemoryVersion."""

    def observe(self, item: ContextItem) -> ContextSourceObservation:
        self._require_item(item, ContextLayer.MEMORY)
        try:
            row = self._session.execute(
                select(
                    MemoryVersion.id,
                    MemoryVersion.memory_id,
                    MemoryVersion.version,
                    MemoryVersion.key,
                    MemoryVersion.value,
                    MemoryVersion.value_type,
                    MemoryVersion.created_at,
                )
                .join(
                    Memory,
                    (Memory.id == MemoryVersion.memory_id)
                    & (Memory.active_version_id == MemoryVersion.id),
                )
                .where(
                    MemoryVersion.id == item.source.source_id,
                    Memory.workspace_id == self._workspace_id,
                    Memory.state == "CONFIRMED",
                    MemoryVersion.state == "CONFIRMED",
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        if row is None:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            )

        try:
            if not memory_context_key_is_valid(row["key"]):
                raise ValueError("memory_key_invalid")
            value = decode_memory_context_value(row["value"])
            if value is None:
                raise ValueError("memory_value_invalid")
            text = memory_context_projection(
                key=row["key"],
                value=value,
                value_type=row["value_type"],
            )
            timestamp = _utc(row["created_at"])
        except (TypeError, UnicodeError, ValueError) as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        return ContextSourceObservation(
            source=item.source,
            text=text,
            label="memory",
            parent_source_id=row["memory_id"],
            version_ref=str(row["version"]),
            source_locator=None,
            source_timestamp=timestamp,
        )


class KnowledgeProvenanceSource(_BaseProvenanceSource):
    """Re-observe one indexed Knowledge chunk under exact workspace."""

    def observe(self, item: ContextItem) -> ContextSourceObservation:
        self._require_item(item, ContextLayer.KNOWLEDGE)
        try:
            row = self._session.execute(
                select(
                    DocumentChunk.id,
                    DocumentChunk.document_id,
                    DocumentChunk.content,
                    DocumentChunk.source_locator,
                    Document.content_hash,
                    Document.indexed_at,
                )
                .join(
                    Document,
                    Document.id == DocumentChunk.document_id,
                )
                .where(
                    DocumentChunk.id == item.source.source_id,
                    Document.workspace_id == self._workspace_id,
                    Document.status == "indexed",
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        if row is None:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            )

        try:
            text, label = knowledge_context_projection(row["content"])
            timestamp = _utc(row["indexed_at"])
        except (TypeError, UnicodeError, ValueError) as error:
            raise ContextProvenanceSourceError(
                "context_snapshot_source_unavailable"
            ) from error

        return ContextSourceObservation(
            source=item.source,
            text=text,
            label=label,
            parent_source_id=row["document_id"],
            version_ref=row["content_hash"],
            source_locator=row["source_locator"],
            source_timestamp=timestamp,
        )


__all__ = [
    "ContextProvenanceSourceError",
    "ContextSourceObservation",
    "ConversationProvenanceSource",
    "ConversationProvenanceSourcePort",
    "KnowledgeProvenanceSource",
    "KnowledgeProvenanceSourcePort",
    "MemoryProvenanceSource",
    "MemoryProvenanceSourcePort",
    "ProjectProvenanceSource",
    "ProjectProvenanceSourcePort",
]
