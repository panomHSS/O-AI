from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_conversation_service
from app.schemas.api import ApiSuccess
from app.schemas.conversations import ConversationDetailResponse, ConversationSummaryResponse, DeleteConversationResponse
from app.services.conversations import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ApiSuccess[list[ConversationSummaryResponse]], status_code=status.HTTP_200_OK)
def list_conversations(
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ApiSuccess[list[ConversationSummaryResponse]]:
    return ApiSuccess(data=conversation_service.list_conversations())


@router.get("/{conversation_id}", response_model=ApiSuccess[ConversationDetailResponse], status_code=status.HTTP_200_OK)
def get_conversation(
    conversation_id: UUID,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ApiSuccess[ConversationDetailResponse]:
    return ApiSuccess(data=conversation_service.get_conversation(conversation_id))


@router.delete("/{conversation_id}", response_model=ApiSuccess[DeleteConversationResponse], status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: UUID,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ApiSuccess[DeleteConversationResponse]:
    conversation_service.delete_conversation(conversation_id)
    return ApiSuccess(data=DeleteConversationResponse(conversation_id=conversation_id))
