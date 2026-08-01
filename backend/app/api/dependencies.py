from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.openai_provider import OpenAIChatProvider
from app.repositories.conversations import ConversationRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.message_citations import MessageCitationRepository
from app.repositories.memories import MemoryRepository
from app.readers import create_document_reader_registry
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.knowledge import KnowledgeService
from app.services.knowledge_answer import KnowledgeAnswerService
from app.services.memories import MemoryService
from app.services.memory_resolver import MemoryResolver
from app.services.reasoning import ReasoningService
from app.services.planning import PlanningService
from app.services.knowledge_intelligence import CitationEngine, ConfidenceEvaluator, ConflictDetector, ContextBuilder, EvidenceRanker, GroundedPromptBuilder, IntentAnalyzer, RetrievalPlanner


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
        citation_repository=MessageCitationRepository(database_session),
        memory_resolver=MemoryResolver(MemoryRepository(database_session), settings.oai_memory_context_max_items, settings.oai_memory_context_max_chars, settings.oai_memory_context_max_item_chars),
        reasoning_service=ReasoningService(),
        planning_service=PlanningService(),
    )


@lru_cache
def get_document_reader_registry():
    return create_document_reader_registry()


def get_knowledge_service(database_session: Session = Depends(get_db)) -> KnowledgeService:
    settings = get_settings()
    return KnowledgeService(
        repository=KnowledgeRepository(database_session),
        readers=get_document_reader_registry(),
        root=settings.oai_knowledge_root,
        max_file_size_mb=settings.oai_document_max_file_size_mb,
        chunk_size=settings.oai_chunk_size_chars,
        chunk_overlap=settings.oai_chunk_overlap_chars,
    )


def get_memory_service(database_session: Session = Depends(get_db)) -> MemoryService:
    return MemoryService(MemoryRepository(database_session))


def get_knowledge_answer_service(database_session: Session = Depends(get_db), chat_service: ChatService = Depends(get_chat_service)) -> KnowledgeAnswerService:
    settings = get_settings()
    conversation_service = ConversationService(ConversationRepository(database_session), chat_service, settings.oai_chat_context_message_limit, MessageCitationRepository(database_session))
    return KnowledgeAnswerService(KnowledgeRepository(database_session), conversation_service, chat_service, IntentAnalyzer(), RetrievalPlanner(settings.oai_knowledge_answer_max_retrieval_queries), EvidenceRanker(settings.oai_knowledge_answer_max_evidence_per_document), ConflictDetector(), ContextBuilder(settings.oai_knowledge_answer_context_char_budget), GroundedPromptBuilder(), CitationEngine(), ConfidenceEvaluator(), settings.oai_knowledge_answer_candidates_per_query, settings.oai_knowledge_answer_selected_evidence_count, MemoryResolver(MemoryRepository(database_session), settings.oai_memory_context_max_items, settings.oai_memory_context_max_chars, settings.oai_memory_context_max_item_chars), ReasoningService(), PlanningService())
