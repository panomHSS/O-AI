from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.memory import Memory


class MemoryRepository:
    """Persistence boundary for explicitly owner-managed memories."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, key: str, value: str, value_type: str, state: str) -> Memory:
        memory = Memory(key=key, value=value, value_type=value_type, state=state)
        self._session.add(memory)
        self._session.flush()
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._session.get(Memory, memory_id)

    def list(self, state: str | None, page: int, page_size: int) -> tuple[Sequence[Memory], int]:
        filters = [Memory.state == state] if state else []
        statement: Select[tuple[Memory]] = select(Memory).where(*filters).order_by(Memory.updated_at.desc(), Memory.id.desc()).offset((page - 1) * page_size).limit(page_size)
        total = self._session.scalar(select(func.count(Memory.id)).where(*filters)) or 0
        return self._session.scalars(statement).all(), total

    def update(self, memory: Memory, **changes: str) -> Memory:
        for field, value in changes.items():
            setattr(memory, field, value)
        self._session.flush()
        return memory

    def delete(self, memory: Memory) -> None:
        self._session.delete(memory)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
