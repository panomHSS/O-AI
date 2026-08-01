import json
from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.memory import Memory
from app.repositories.memories import MemoryRepository
from app.models.memory_version import MemoryVersion
from app.schemas.memories import ArchiveMemoryRequest, CreateMemoryRequest, DecisionRequest, MemoryDiffResponse, MemoryHistoryResponse, MemoryListResponse, MemoryResponse, MemoryVersionResponse, UpdateMemoryRequest


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
            memory = self._repository.create(payload.key, serialized, payload.value_type, "PENDING")
            self._repository.create_initial_version(memory, payload.change_reason, self._json_optional(payload.evidence_snapshot))
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
        if memory.pending_version_id:
            raise MemoryConflictError("A pending proposal already exists for this memory.")
        active = self._repository.version_by_id(memory.active_version_id)
        base_value, base_type = (active.value, active.value_type) if active else (memory.value, memory.value_type)
        value_type = payload.value_type or base_type
        if "value" in payload.model_fields_set:
            value = self._serialize(payload.value, value_type)
        else:
            value = base_value
            if payload.value_type is not None:
                self._deserialize(value, value_type)
        if value == base_value and value_type == base_type and "evidence_snapshot" not in payload.model_fields_set:
            return self._response(memory)
        try:
            updated = self._repository.create_version(memory, state="PENDING", value=value, value_type=value_type, change_reason=payload.change_reason, decision_comment=None, evidence_snapshot=self._json_optional(payload.evidence_snapshot) if "evidence_snapshot" in payload.model_fields_set else self._latest_evidence(memory))
            memory.pending_version_id = updated.id
            self._repository.commit()
            return self._response(memory)
        except Exception:
            self._repository.rollback()
            raise

    def approve(self, memory_id: UUID, version: int, payload: DecisionRequest) -> MemoryResponse:
        return self._decide(memory_id, version, "CONFIRMED", payload.decision_comment)

    def reject(self, memory_id: UUID, version: int, payload: DecisionRequest) -> MemoryResponse:
        return self._decide(memory_id, version, "REJECTED", payload.decision_comment)

    def archive(self, memory_id: UUID, payload: ArchiveMemoryRequest) -> MemoryResponse:
        memory = self._require(memory_id)
        if memory.pending_version_id:
            raise MemoryConflictError("A memory with a pending proposal cannot be archived.")
        active = self._repository.version_by_id(memory.active_version_id)
        if active is None:
            raise MemoryValidationError("Only a confirmed memory can be archived.")
        try:
            self._repository.create_version(memory, state="ARCHIVED", value=active.value, value_type=active.value_type, change_reason=payload.change_reason, decision_comment=None, evidence_snapshot=active.evidence_snapshot)
            memory.state = "ARCHIVED"
            self._repository.commit()
            return self._response(memory)
        except Exception:
            self._repository.rollback()
            raise

    def history(self, memory_id: UUID) -> MemoryHistoryResponse:
        memory = self._require(memory_id)
        return MemoryHistoryResponse(items=[self._version_response(item) for item in self._repository.versions(memory.id)])

    def diff(self, memory_id: UUID, from_version: int, to_version: int) -> MemoryDiffResponse:
        memory = self._require(memory_id)
        left = self._repository.version(memory.id, from_version)
        right = self._repository.version(memory.id, to_version)
        if left is None or right is None:
            raise MemoryNotFoundError("The requested memory version was not found.")
        fields = ("value", "value_type", "state", "change_reason", "decision_comment", "evidence_snapshot")
        changes = {field: {"from": self._decoded_field(left, field), "to": self._decoded_field(right, field)} for field in fields if getattr(left, field) != getattr(right, field)}
        return MemoryDiffResponse(memory_id=memory_id, from_version=from_version, to_version=to_version, changes=changes)

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

    def _decide(self, memory_id: UUID, version: int, state: str, comment: str) -> MemoryResponse:
        memory = self._require(memory_id)
        proposal = self._repository.version(memory.id, version)
        if proposal is None or proposal.id != memory.pending_version_id or proposal.state != "PENDING":
            raise MemoryValidationError("Only pending memories can be approved or rejected.")
        try:
            self._repository.decide(proposal, state, comment)
            memory.pending_version_id = None
            if state == "CONFIRMED":
                memory.active_version_id = proposal.id
                memory.value, memory.value_type, memory.state = proposal.value, proposal.value_type, "CONFIRMED"
            elif memory.active_version_id is None:
                memory.state = "REJECTED"
            self._repository.commit()
            return self._response(memory)
        except Exception:
            self._repository.rollback()
            raise

    def _latest_evidence(self, memory: Memory) -> str | None:
        latest = self._repository.version(memory.id, memory.current_version)
        return latest.evidence_snapshot if latest else None

    @staticmethod
    def _json_optional(value: object | None) -> str | None:
        return None if value is None else json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _decoded_field(version: MemoryVersion, field: str) -> object:
        value = getattr(version, field)
        return json.loads(value) if field in {"value", "evidence_snapshot"} and value is not None else value

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

    def _response(self, memory: Memory) -> MemoryResponse:
        active = self._repository.version_by_id(memory.active_version_id)
        pending = self._repository.version_by_id(memory.pending_version_id)
        return MemoryResponse(id=UUID(memory.id), key=memory.key, value=self._deserialize(active.value, active.value_type) if active else None, value_type=active.value_type if active else None, state=memory.state, created_at=memory.created_at, updated_at=memory.updated_at, current_version=memory.current_version, active_version=self._version_response(active) if active else None, pending_version=self._version_response(pending) if pending else None)

    @staticmethod
    def _version_response(version: MemoryVersion) -> MemoryVersionResponse:
        return MemoryVersionResponse(id=UUID(version.id), version=version.version, key=version.key, value=MemoryService._deserialize(version.value, version.value_type), value_type=version.value_type, state=version.state, change_reason=version.change_reason, decision_comment=version.decision_comment, evidence_snapshot=json.loads(version.evidence_snapshot) if version.evidence_snapshot else None, created_by=version.created_by, proposed_by=version.proposed_by, proposed_at=version.proposed_at, decided_by=version.decided_by, decided_at=version.decided_at, created_at=version.created_at)
