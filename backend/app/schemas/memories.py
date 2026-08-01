from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


MemoryState = Literal["PENDING", "CONFIRMED", "ARCHIVED"]
MemoryValueType = Literal["STRING", "INTEGER", "BOOLEAN", "DATE", "JSON"]
MemoryKey = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class CreateMemoryRequest(BaseModel):
    key: MemoryKey
    value: Any
    value_type: MemoryValueType
    state: MemoryState = "PENDING"


class UpdateMemoryRequest(BaseModel):
    value: Any | None = None
    value_type: MemoryValueType | None = None
    state: MemoryState | None = None


class MemoryResponse(BaseModel):
    id: UUID
    key: str
    value: Any
    value_type: MemoryValueType
    state: MemoryState
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    page: int
    page_size: int
    total: int


class DeleteMemoryResponse(BaseModel):
    memory_id: UUID
