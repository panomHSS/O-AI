from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceScope
from app.models.memory import Memory
from app.models.memory_version import MemoryVersion


class MemoryRepository:
    """Workspace-scoped persistence boundary for owner-managed Memories."""

    def __init__(
        self,
        session: Session,
        workspace_scope: WorkspaceScope,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    def create(
        self,
        key: str,
        value: str,
        value_type: str,
        state: str,
    ) -> Memory:
        memory = Memory(
            key=key,
            value=value,
            value_type=value_type,
            state=state,
            workspace_id=self._workspace_id,
        )
        self._session.add(memory)
        self._session.flush()
        return memory

    def create_version(
        self,
        memory: Memory,
        *,
        state: str,
        value: str,
        value_type: str,
        change_reason: str,
        decision_comment: str | None,
        evidence_snapshot: str | None,
    ) -> MemoryVersion:
        self._require_owned(memory)
        version = memory.current_version + 1
        item = MemoryVersion(
            memory_id=memory.id,
            version=version,
            key=memory.key,
            value=value,
            value_type=value_type,
            state=state,
            change_reason=change_reason,
            decision_comment=decision_comment,
            evidence_snapshot=evidence_snapshot,
        )
        self._session.add(item)
        memory.current_version = version
        self._session.flush()
        return item

    def create_initial_version(
        self,
        memory: Memory,
        change_reason: str,
        evidence_snapshot: str | None,
    ) -> MemoryVersion:
        self._require_owned(memory)
        item = MemoryVersion(
            memory_id=memory.id,
            version=1,
            key=memory.key,
            value=memory.value,
            value_type=memory.value_type,
            state=memory.state,
            change_reason=change_reason,
            decision_comment=None,
            evidence_snapshot=evidence_snapshot,
        )
        self._session.add(item)
        self._session.flush()
        memory.pending_version_id = item.id if item.state == "PENDING" else None
        memory.active_version_id = item.id if item.state == "CONFIRMED" else None
        return item

    def decide(
        self,
        version: MemoryVersion,
        state: str,
        comment: str,
    ) -> None:
        if self.version_by_id(version.id) is None:
            raise ValueError("workspace_mismatch")
        if version.state != "PENDING" or state not in {"CONFIRMED", "REJECTED"}:
            raise ValueError(
                "Only a pending version can receive one approval decision."
            )
        version.state = state
        version.decision_comment = comment
        from app.db.base import utc_now

        version.decided_by = "owner"
        version.decided_at = utc_now()
        self._session.flush()

    def versions(self, memory_id: str) -> Sequence[MemoryVersion]:
        return self._session.scalars(
            select(MemoryVersion)
            .join(Memory, Memory.id == MemoryVersion.memory_id)
            .where(
                MemoryVersion.memory_id == memory_id,
                Memory.workspace_id == self._workspace_id,
            )
            .order_by(MemoryVersion.version.desc())
        ).all()

    def version(
        self,
        memory_id: str,
        version: int,
    ) -> MemoryVersion | None:
        return self._session.scalar(
            select(MemoryVersion)
            .join(Memory, Memory.id == MemoryVersion.memory_id)
            .where(
                MemoryVersion.memory_id == memory_id,
                MemoryVersion.version == version,
                Memory.workspace_id == self._workspace_id,
            )
        )

    def version_by_id(
        self,
        version_id: str | None,
    ) -> MemoryVersion | None:
        if not version_id:
            return None
        return self._session.scalar(
            select(MemoryVersion)
            .join(Memory, Memory.id == MemoryVersion.memory_id)
            .where(
                MemoryVersion.id == version_id,
                Memory.workspace_id == self._workspace_id,
            )
        )

    def get(self, memory_id: str) -> Memory | None:
        return self._session.scalar(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.workspace_id == self._workspace_id,
            )
        )

    def list(
        self,
        state: str | None,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Memory], int]:
        filters = [Memory.workspace_id == self._workspace_id]
        if state:
            filters.append(Memory.state == state)

        statement: Select[tuple[Memory]] = (
            select(Memory)
            .where(*filters)
            .order_by(
                Memory.updated_at.desc(),
                Memory.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (
            self._session.scalar(
                select(func.count(Memory.id)).where(*filters)
            )
            or 0
        )
        return self._session.scalars(statement).all(), total

    def confirmed_versions_for_context(self) -> Sequence[MemoryVersion]:
        """Return only active confirmed Memories from the exact workspace."""
        statement: Select[tuple[MemoryVersion]] = (
            select(MemoryVersion)
            .join(
                Memory,
                (Memory.active_version_id == MemoryVersion.id)
                & (Memory.id == MemoryVersion.memory_id),
            )
            .where(
                Memory.workspace_id == self._workspace_id,
                Memory.state == "CONFIRMED",
                MemoryVersion.state == "CONFIRMED",
            )
            .order_by(
                MemoryVersion.key,
                MemoryVersion.id,
            )
        )
        return self._session.scalars(statement).all()

    def delete(self, memory: Memory) -> None:
        self._require_owned(memory)
        self._session.delete(memory)

    def _require_owned(self, memory: Memory) -> None:
        if memory.workspace_id != self._workspace_id:
            raise ValueError("workspace_mismatch")

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
