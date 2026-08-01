from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


MemoryState = Literal["PENDING", "CONFIRMED", "REJECTED", "ARCHIVED"]
MemoryValueType = Literal["STRING", "INTEGER", "BOOLEAN", "DATE", "JSON"]
MemoryKey = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class CreateMemoryRequest(BaseModel):
    key: MemoryKey
    value: Any
    value_type: MemoryValueType
    state: MemoryState = "PENDING"
    change_reason: str = Field(default="Owner created memory.", min_length=1, max_length=512)
    evidence_snapshot: Any | None = None


class UpdateMemoryRequest(BaseModel):
    value: Any | None = None
    value_type: MemoryValueType | None = None
    change_reason: str = Field(min_length=1, max_length=512)
    evidence_snapshot: Any | None = None


class DecisionRequest(BaseModel):
    decision_comment: str = Field(min_length=1, max_length=2000)


class ArchiveMemoryRequest(BaseModel):
    change_reason: str = Field(min_length=1, max_length=512)


class MemoryVersionResponse(BaseModel):
    id: UUID
    version: int
    key: str
    value: Any
    value_type: MemoryValueType
    state: MemoryState
    change_reason: str
    decision_comment: str | None
    evidence_snapshot: Any | None
    created_by: str
    proposed_by: str
    proposed_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    created_at: datetime


class MemoryResponse(BaseModel):
    id: UUID
    key: str
    value: Any | None
    value_type: MemoryValueType | None
    state: MemoryState
    created_at: datetime
    updated_at: datetime
    current_version: int
    active_version: MemoryVersionResponse | None
    pending_version: MemoryVersionResponse | None


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    page: int
    page_size: int
    total: int


class DeleteMemoryResponse(BaseModel):
    memory_id: UUID


class MemoryHistoryResponse(BaseModel):
    items: list[MemoryVersionResponse]


class MemoryDiffResponse(BaseModel):
    memory_id: UUID
    from_version: int
    to_version: int
    changes: dict[str, dict[str, Any]]
