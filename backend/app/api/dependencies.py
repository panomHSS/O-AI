from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.openai_provider import OpenAIChatProvider
from app.repositories.conversations import ConversationRepository
from app.services.chat import ChatService
from app.services.conversations import ConversationService


@lru_cache
def get_chat_service() -> ChatService:
    """Compose the configured provider behind the provider-neutral service."""
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    provider = OpenAIChatProvider(api_key=api_key, model=settings.openai_model)
    return ChatService(provider=provider)


def get_conversation_service(
    database_session: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationService:
    settings = get_settings()
    return ConversationService(
        repository=ConversationRepository(database_session),
        chat_service=chat_service,
        context_message_limit=settings.oai_chat_context_message_limit,
    )
