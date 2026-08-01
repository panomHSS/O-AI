from typing import Annotated
from fastapi import APIRouter, Depends
from app.api.dependencies import get_knowledge_answer_service
from app.schemas.api import ApiSuccess
from app.schemas.knowledge_answer import KnowledgeAnswerRequest, KnowledgeAnswerResponse
from app.services.knowledge_answer import KnowledgeAnswerService
router = APIRouter(prefix="/knowledge", tags=["knowledge"])
@router.post("/answer", response_model=ApiSuccess[KnowledgeAnswerResponse])
def answer(payload: KnowledgeAnswerRequest, service: Annotated[KnowledgeAnswerService, Depends(get_knowledge_answer_service)]) -> ApiSuccess[KnowledgeAnswerResponse]: return ApiSuccess(data=service.answer(payload.question, payload.conversation_id, payload.project_id))
