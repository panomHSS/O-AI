"""D97 exact-workspace durable Context snapshot repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
)
from app.contracts.workspace import WorkspaceScope
from app.models.context_snapshot import (
    ContextSnapshotItemRecord,
    ContextSnapshotRecord,
)
from app.models.conversation import Conversation
from app.models.message import Message


class ContextSnapshotPersistenceError(Exception):
    """Bounded durable Context snapshot persistence failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ContextSnapshotRepository:
    """Persist and reconstruct D96 snapshots under one exact workspace."""

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

    def add_snapshot(
        self,
        message: Message,
        snapshot: ContextSnapshot,
    ) -> ContextSnapshotRecord:
        if not isinstance(message, Message):
            raise ContextSnapshotPersistenceError(
                "context_snapshot_message_invalid"
            )
        if not isinstance(snapshot, ContextSnapshot):
            raise ContextSnapshotPersistenceError(
                "context_snapshot_invalid"
            )
        if snapshot.workspace_scope.workspace_id is not self._workspace_enum:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_workspace_mismatch"
            )

        try:
            self._session.flush()
            ownership = self._session.execute(
                select(
                    Message.role,
                    Conversation.workspace_id,
                )
                .join(
                    Conversation,
                    Conversation.id == Message.conversation_id,
                )
                .where(Message.id == message.id)
            ).mappings().one_or_none()
        except SQLAlchemyError as error:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_message_unavailable"
            ) from error

        if ownership is None:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_message_unavailable"
            )
        if ownership["workspace_id"] != self._workspace_id:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_workspace_mismatch"
            )
        if ownership["role"] != "assistant":
            raise ContextSnapshotPersistenceError(
                "context_snapshot_assistant_required"
            )

        try:
            existing = self._session.scalar(
                select(ContextSnapshotRecord.id).where(
                    ContextSnapshotRecord.message_id == message.id
                )
            )
            if existing is not None:
                raise ContextSnapshotPersistenceError(
                    "context_snapshot_already_exists"
                )

            record = ContextSnapshotRecord(
                message_id=message.id,
                contract_version=snapshot.contract_version,
                captured_at=snapshot.captured_at,
                snapshot_digest=snapshot.snapshot_digest,
            )
            self._session.add(record)
            self._session.flush()

            rows = [
                ContextSnapshotItemRecord(
                    snapshot_id=record.id,
                    item_order=index,
                    layer=snapshot_item.item.source.layer.value,
                    source_id=snapshot_item.item.source.source_id,
                    text=snapshot_item.item.text,
                    label=snapshot_item.item.label,
                    content_sha256=(
                        snapshot_item.provenance.content_sha256
                    ),
                    parent_source_id=(
                        snapshot_item.provenance.parent_source_id
                    ),
                    version_ref=snapshot_item.provenance.version_ref,
                    source_locator=(
                        snapshot_item.provenance.source_locator
                    ),
                    source_timestamp=(
                        snapshot_item.provenance.source_timestamp
                    ),
                )
                for index, snapshot_item in enumerate(
                    snapshot.items,
                    start=1,
                )
            ]
            self._session.add_all(rows)
            self._session.flush()
            return record
        except ContextSnapshotPersistenceError:
            raise
        except SQLAlchemyError as error:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_persistence_failed"
            ) from error

    def get_for_message(
        self,
        message_id: str,
    ) -> ContextSnapshot | None:
        if type(message_id) is not str or not message_id:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_message_invalid"
            )

        try:
            statement = (
                select(ContextSnapshotRecord)
                .join(
                    Message,
                    Message.id == ContextSnapshotRecord.message_id,
                )
                .join(
                    Conversation,
                    Conversation.id == Message.conversation_id,
                )
                .where(
                    ContextSnapshotRecord.message_id == message_id,
                    Conversation.workspace_id == self._workspace_id,
                )
                .options(
                    selectinload(ContextSnapshotRecord.items)
                )
            )
            record = self._session.scalar(statement)
        except SQLAlchemyError as error:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_read_failed"
            ) from error

        if record is None:
            return None

        try:
            items = tuple(
                self._reconstruct_item(row)
                for row in sorted(
                    record.items,
                    key=lambda item: item.item_order,
                )
            )
            return ContextSnapshot(
                workspace_scope=WorkspaceScope(self._workspace_enum),
                captured_at=_as_utc(record.captured_at),
                items=items,
                snapshot_digest=record.snapshot_digest,
                contract_version=record.contract_version,
            )
        except (
            TypeError,
            UnicodeError,
            ValueError,
        ) as error:
            raise ContextSnapshotPersistenceError(
                "context_snapshot_invalid"
            ) from error

    def _reconstruct_item(
        self,
        row: ContextSnapshotItemRecord,
    ) -> ContextSnapshotItem:
        source = ContextSourceRef(
            workspace_id=self._workspace_enum,
            layer=ContextLayer(row.layer),
            source_id=row.source_id,
        )
        item = ContextItem(
            source=source,
            text=row.text,
            label=row.label,
        )
        provenance = ContextSourceProvenance(
            source=source,
            content_sha256=row.content_sha256,
            parent_source_id=row.parent_source_id,
            version_ref=row.version_ref,
            source_locator=row.source_locator,
            source_timestamp=(
                _as_utc(row.source_timestamp)
                if row.source_timestamp is not None
                else None
            ),
        )
        return ContextSnapshotItem(
            item=item,
            provenance=provenance,
        )


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("context_snapshot_timestamp_invalid")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "ContextSnapshotPersistenceError",
    "ContextSnapshotRepository",
]
