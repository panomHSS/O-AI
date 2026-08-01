from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_memory_service
from app.schemas.api import ApiSuccess
from app.schemas.memories import CreateMemoryRequest, DeleteMemoryResponse, MemoryListResponse, MemoryResponse, MemoryState, UpdateMemoryRequest
from app.services.memories import MemoryService


router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_201_CREATED)
def create_memory(payload: CreateMemoryRequest, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.create(payload))


@router.get("", response_model=ApiSuccess[MemoryListResponse], status_code=status.HTTP_200_OK)
def list_memories(
    service: Annotated[MemoryService, Depends(get_memory_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    state: MemoryState | None = None,
) -> ApiSuccess[MemoryListResponse]:
    return ApiSuccess(data=service.list(state, page, page_size))


@router.get("/{memory_id}", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_200_OK)
def get_memory(memory_id: UUID, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.get(memory_id))


@router.patch("/{memory_id}", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_200_OK)
def update_memory(memory_id: UUID, payload: UpdateMemoryRequest, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.update(memory_id, payload))


@router.delete("/{memory_id}", response_model=ApiSuccess[DeleteMemoryResponse], status_code=status.HTTP_200_OK)
def delete_memory(memory_id: UUID, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[DeleteMemoryResponse]:
    service.delete(memory_id)
    return ApiSuccess(data=DeleteMemoryResponse(memory_id=memory_id))
