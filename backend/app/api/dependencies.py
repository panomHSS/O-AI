from functools import lru_cache

from app.core.config import get_settings
from app.providers.openai_provider import OpenAIChatProvider
from app.services.chat import ChatService


@lru_cache
def get_chat_service() -> ChatService:
    """Compose the configured provider behind the provider-neutral service."""
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    provider = OpenAIChatProvider(api_key=api_key, model=settings.openai_model)
    return ChatService(provider=provider)
