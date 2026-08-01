import json
from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.memory import Memory
from app.repositories.memories import MemoryRepository
from app.schemas.memories import CreateMemoryRequest, MemoryListResponse, MemoryResponse, UpdateMemoryRequest


class MemoryNotFoundError(Exception):
    pass


class MemoryValidationError(Exception):
    pass


class MemoryConflictError(Exception):
    pass


class MemoryService:
    """Owner-controlled CRUD service; it never derives or learns memories automatically."""

    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def create(self, payload: CreateMemoryRequest) -> MemoryResponse:
        serialized = self._serialize(payload.value, payload.value_type)
        try:
            memory = self._repository.create(payload.key, serialized, payload.value_type, payload.state)
            self._repository.commit()
            return self._response(memory)
        except IntegrityError as error:
            self._repository.rollback()
            raise MemoryConflictError("A memory with this key already exists.") from error
        except Exception:
            self._repository.rollback()
            raise

    def list(self, state: str | None, page: int, page_size: int) -> MemoryListResponse:
        memories, total = self._repository.list(state, page, page_size)
        return MemoryListResponse(items=[self._response(memory) for memory in memories], page=page, page_size=page_size, total=total)

    def get(self, memory_id: UUID) -> MemoryResponse:
        return self._response(self._require(memory_id))

    def update(self, memory_id: UUID, payload: UpdateMemoryRequest) -> MemoryResponse:
        memory = self._require(memory_id)
        changes: dict[str, str] = {}
        value_type = payload.value_type or memory.value_type
        if "value" in payload.model_fields_set:
            changes["value"] = self._serialize(payload.value, value_type)
        elif payload.value_type is not None:
            self._deserialize(memory.value, value_type)
            changes["value_type"] = value_type
        if payload.value_type is not None:
            changes["value_type"] = value_type
        if payload.state is not None:
            changes["state"] = payload.state
        if not changes:
            return self._response(memory)
        try:
            updated = self._repository.update(memory, **changes)
            self._repository.commit()
            return self._response(updated)
        except Exception:
            self._repository.rollback()
            raise

    def delete(self, memory_id: UUID) -> None:
        memory = self._require(memory_id)
        try:
            self._repository.delete(memory)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _require(self, memory_id: UUID) -> Memory:
        memory = self._repository.get(str(memory_id))
        if memory is None:
            raise MemoryNotFoundError("The requested memory was not found.")
        return memory

    @staticmethod
    def _serialize(value: object, value_type: str) -> str:
        if value_type == "STRING" and not isinstance(value, str):
            raise MemoryValidationError("STRING memories require a string value.")
        if value_type == "INTEGER" and (not isinstance(value, int) or isinstance(value, bool)):
            raise MemoryValidationError("INTEGER memories require an integer value.")
        if value_type == "BOOLEAN" and not isinstance(value, bool):
            raise MemoryValidationError("BOOLEAN memories require a boolean value.")
        if value_type == "DATE":
            if not isinstance(value, str):
                raise MemoryValidationError("DATE memories require an ISO-8601 date string.")
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise MemoryValidationError("DATE memories require an ISO-8601 date string.") from error
        if value_type == "JSON":
            try:
                return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError) as error:
                raise MemoryValidationError("JSON memories require a JSON-serializable value.") from error
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _deserialize(value: str, value_type: str) -> object:
        decoded = json.loads(value)
        MemoryService._serialize(decoded, value_type)
        return decoded

    @staticmethod
    def _response(memory: Memory) -> MemoryResponse:
        return MemoryResponse(id=UUID(memory.id), key=memory.key, value=MemoryService._deserialize(memory.value, memory.value_type), value_type=memory.value_type, state=memory.state, created_at=memory.created_at, updated_at=memory.updated_at)
