from fastapi import APIRouter

from app.api.v1.automations import router as automations_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.local_ai_visibility import router as local_ai_visibility_router
from app.api.v1.local_ai_control import router as local_ai_control_router
from app.api.v1.health import router as health_router
from app.api.v1.execution_approvals import router as execution_approvals_router
from app.api.v1.calendar_write_approvals import router as calendar_write_approvals_router
from app.api.v1.gmail_send_approvals import router as gmail_send_approvals_router
from app.api.v1.gmail_send_executions import router as gmail_send_executions_router
from app.api.v1.calendar_write_chat import router as calendar_write_chat_router
from app.api.v1.calendar_write_executions import router as calendar_write_executions_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.knowledge_answer import router as knowledge_answer_router
from app.api.v1.memories import router as memories_router
from app.api.v1.oauth import router as oauth_router
from app.api.v1.gmail_oauth import router as gmail_oauth_router
from app.api.v1.gmail_send_oauth import router as gmail_send_oauth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.project_update_proposals import router as project_update_proposals_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(automations_router)
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(diagnostics_router)
api_router.include_router(local_ai_visibility_router)
api_router.include_router(local_ai_control_router)
api_router.include_router(health_router)
api_router.include_router(execution_approvals_router)
api_router.include_router(calendar_write_approvals_router)
api_router.include_router(gmail_send_approvals_router)
api_router.include_router(gmail_send_executions_router)
api_router.include_router(calendar_write_chat_router)
api_router.include_router(calendar_write_executions_router)
api_router.include_router(knowledge_router)
api_router.include_router(knowledge_answer_router)
api_router.include_router(memories_router)
api_router.include_router(oauth_router)
api_router.include_router(gmail_oauth_router)
api_router.include_router(gmail_send_oauth_router)
api_router.include_router(projects_router)
api_router.include_router(project_update_proposals_router)
