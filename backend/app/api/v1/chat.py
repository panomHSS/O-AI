from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_chat_service
from app.schemas.api import ApiSuccess
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ApiSuccess[ChatResponse], status_code=status.HTTP_200_OK)
def send_chat_message(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ApiSuccess[ChatResponse]:
    """Handle a single chat turn through the configured chat service."""
    return ApiSuccess(data=ChatResponse(reply=chat_service.send_message(payload.message)))
