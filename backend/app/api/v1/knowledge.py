from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.dependencies import get_knowledge_service
from app.schemas.api import ApiSuccess
from app.schemas.knowledge import (
    DeleteDocumentResponse, DocumentDetailResponse, DocumentListResponse, DocumentStatus,
    KnowledgeSearchResponse, ScanKnowledgeResponse,
)
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

LOCAL_REQUEST_HEADER_VALUE = "1"


def require_local_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit browser request intent for the scan side effect."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.post("/scan", response_model=ApiSuccess[ScanKnowledgeResponse], status_code=status.HTTP_200_OK)
def scan_documents(
    _: Annotated[None, Depends(require_local_request_marker)],
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> ApiSuccess[ScanKnowledgeResponse]:
    return ApiSuccess(data=ScanKnowledgeResponse(**knowledge_service.scan().__dict__))


@router.get("/documents", response_model=ApiSuccess[DocumentListResponse], status_code=status.HTTP_200_OK)
def list_documents(
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
) -> ApiSuccess[DocumentListResponse]:
    return ApiSuccess(data=knowledge_service.list_documents(page, page_size, status_filter))


@router.get("/documents/{document_id}", response_model=ApiSuccess[DocumentDetailResponse], status_code=status.HTTP_200_OK)
def get_document(document_id: UUID, knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)]) -> ApiSuccess[DocumentDetailResponse]:
    return ApiSuccess(data=knowledge_service.get_document(document_id))


@router.delete("/documents/{document_id}", response_model=ApiSuccess[DeleteDocumentResponse], status_code=status.HTTP_200_OK)
def delete_document(document_id: UUID, knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)]) -> ApiSuccess[DeleteDocumentResponse]:
    knowledge_service.delete_document(document_id)
    return ApiSuccess(data=DeleteDocumentResponse(document_id=document_id))


@router.get("/search", response_model=ApiSuccess[KnowledgeSearchResponse], status_code=status.HTTP_200_OK)
def search_documents(
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiSuccess[KnowledgeSearchResponse]:
    return ApiSuccess(data=knowledge_service.search(q, limit))
