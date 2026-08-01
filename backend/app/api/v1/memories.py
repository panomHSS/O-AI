from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_memory_service
from app.schemas.api import ApiSuccess
from app.schemas.memories import ArchiveMemoryRequest, CreateMemoryRequest, DecisionRequest, DeleteMemoryResponse, MemoryDiffResponse, MemoryHistoryResponse, MemoryListResponse, MemoryResponse, MemoryState, UpdateMemoryRequest
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


@router.post("/{memory_id}/versions/{version}/approve", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_200_OK)
def approve_memory(memory_id: UUID, version: int, payload: DecisionRequest, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.approve(memory_id, version, payload))


@router.post("/{memory_id}/versions/{version}/reject", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_200_OK)
def reject_memory(memory_id: UUID, version: int, payload: DecisionRequest, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.reject(memory_id, version, payload))


@router.post("/{memory_id}/archive", response_model=ApiSuccess[MemoryResponse], status_code=status.HTTP_200_OK)
def archive_memory(memory_id: UUID, payload: ArchiveMemoryRequest, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryResponse]:
    return ApiSuccess(data=service.archive(memory_id, payload))


@router.get("/{memory_id}/history", response_model=ApiSuccess[MemoryHistoryResponse], status_code=status.HTTP_200_OK)
def memory_history(memory_id: UUID, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[MemoryHistoryResponse]:
    return ApiSuccess(data=service.history(memory_id))


@router.get("/{memory_id}/diff", response_model=ApiSuccess[MemoryDiffResponse], status_code=status.HTTP_200_OK)
def memory_diff(memory_id: UUID, service: Annotated[MemoryService, Depends(get_memory_service)], from_version: Annotated[int, Query(ge=1)] = 1, to_version: Annotated[int, Query(ge=1)] = 1) -> ApiSuccess[MemoryDiffResponse]:
    return ApiSuccess(data=service.diff(memory_id, from_version, to_version))


@router.delete("/{memory_id}", response_model=ApiSuccess[DeleteMemoryResponse], status_code=status.HTTP_200_OK)
def delete_memory(memory_id: UUID, service: Annotated[MemoryService, Depends(get_memory_service)]) -> ApiSuccess[DeleteMemoryResponse]:
    service.delete(memory_id)
    return ApiSuccess(data=DeleteMemoryResponse(memory_id=memory_id))
