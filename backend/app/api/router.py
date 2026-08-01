from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.knowledge_answer import router as knowledge_answer_router
from app.api.v1.memories import router as memories_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(health_router)
api_router.include_router(knowledge_router)
api_router.include_router(knowledge_answer_router)
api_router.include_router(memories_router)
