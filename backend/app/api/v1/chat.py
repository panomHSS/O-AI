from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_conversation_service
from app.schemas.api import ApiSuccess
from app.schemas.chat import ChatRequest, ChatResponse, MemoryUsageResponse
from app.services.conversations import ConversationService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ApiSuccess[ChatResponse], status_code=status.HTTP_200_OK)
def send_chat_message(
    payload: ChatRequest,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ApiSuccess[ChatResponse]:
    """Handle a single chat turn through the configured chat service."""
    result = conversation_service.send_message(payload.message, payload.conversation_id)
    return ApiSuccess(data=ChatResponse(reply=result.reply, conversation_id=result.conversation_id, memories_used=[MemoryUsageResponse(memory_id=item.memory_id, version=item.version, key=item.key) for item in result.memories_used]))
