from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.openai_provider import OpenAIChatProvider
from app.readers import create_document_reader_registry
from app.repositories.conversations import ConversationRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.memories import MemoryRepository
from app.repositories.message_citations import MessageCitationRepository
from app.repositories.project_action_execution_proposals import (
    ProjectActionExecutionProposalRepository,
)
from app.repositories.project_update_proposals import (
    ProjectUpdateProposalRepository,
)
from app.repositories.projects import ProjectRepository
from app.search.factory import create_knowledge_search
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.decision import DecisionService
from app.services.knowledge import KnowledgeService
from app.services.knowledge_answer import KnowledgeAnswerService
from app.services.knowledge_intelligence import (
    CitationEngine,
    ConfidenceEvaluator,
    ConflictDetector,
    ContextBuilder,
    EvidenceRanker,
    GroundedPromptBuilder,
    IntentAnalyzer,
    RetrievalPlanner,
)
from app.services.memories import MemoryService
from app.services.memory_resolver import MemoryResolver
from app.services.planning import PlanningService
from app.services.project_action_execution_persistence import (
    ProjectActionExecutionPersistenceService,
)
from app.services.project_context import (
    ProjectContextReader,
    ProjectContextResolver,
)
from app.services.project_update_generation import (
    ProjectUpdateProposalGenerator,
)
from app.services.project_update_orchestrator import (
    ProjectUpdateTurnOrchestrator,
)
from app.services.project_update_proposals import (
    ProjectUpdateProposalService,
)
from app.services.projects import ProjectService
from app.services.reasoning import ReasoningService
from app.embeddings.base import EmbeddingPort
from app.embeddings.openai import OpenAIEmbeddingAdapter
from app.intelligence.pipeline.pipeline import Pipeline
from app.intelligence.orchestrator.knowledge_orchestrator import (
    KnowledgeOrchestrator,
)
from app.intelligence.steps import (
    RetrievalStep,
    EvidenceStep,
    ReasoningStep,
    PlanningStep,
    DecisionStep,
    GoalStep,
)
from backend.app.services.goals import GoalService
from app.pipeline.retrieval import RetrievalPipeline
from app.pipeline.components import RetrievalComponents

@lru_cache
def get_chat_service() -> ChatService:
    """Compose the configured provider behind the provider-neutral service."""
    settings = get_settings()

    api_key = (
        settings.openai_api_key.get_secret_value()
        if settings.openai_api_key
        else None
    )

    provider = OpenAIChatProvider(
        api_key=api_key,
        model=settings.openai_model,
    )

    return ChatService(
        provider=provider,
    )


def get_conversation_service(
    database_session: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationService:
    settings = get_settings()

    execution_proposal_repository = (
        ProjectActionExecutionProposalRepository(
            database_session
        )
    )

    execution_persistence_service = (
        ProjectActionExecutionPersistenceService(
            execution_proposal_repository
        )
    )

    return ConversationService(
        repository=ConversationRepository(
            database_session
        ),
        chat_service=chat_service,
        context_message_limit=(
            settings.oai_chat_context_message_limit
        ),
        citation_repository=MessageCitationRepository(
            database_session
        ),
        memory_resolver=MemoryResolver(
            reader=MemoryRepository(
                database_session
            ),
            item_limit=(
                settings.oai_memory_context_max_items
            ),
            char_budget=(
                settings.oai_memory_context_max_chars
            ),
            item_char_limit=(
                settings.oai_memory_context_max_item_chars
            ),
        ),
        project_context_resolver=ProjectContextResolver(
            ProjectContextReader(
                database_session
            )
        ),
        project_action_execution_persistence_service=(
            execution_persistence_service
        ),
        
    )


@lru_cache
def get_document_reader_registry():
    return create_document_reader_registry()

def get_embedding_provider() -> EmbeddingPort:
    """Compose the configured embedding provider."""
    settings = get_settings()

    api_key = (
        settings.openai_api_key.get_secret_value()
        if settings.openai_api_key
        else None
    )

    return OpenAIEmbeddingAdapter(
        api_key=api_key,
        model=settings.oai_embedding_model,
        dimensions=settings.oai_embedding_dimensions,
    )

def get_knowledge_repository(
    database_session: Session,
) -> KnowledgeRepository:
    """Compose authoritative knowledge storage with derived search."""

    dialect_name = (
        database_session.get_bind().dialect.name
    )

    embeddings = None

    if dialect_name == "postgresql":
        embeddings = get_embedding_provider()

    search = create_knowledge_search(
        database_session,
        embeddings=embeddings,
    )

    return KnowledgeRepository(
        session=database_session,
        search=search,
    )

def get_knowledge_service(
    database_session: Session = Depends(get_db),
) -> KnowledgeService:
    settings = get_settings()

    return KnowledgeService(
        repository=get_knowledge_repository(
            database_session
        ),
        readers=get_document_reader_registry(),
        root=settings.oai_knowledge_root,
        max_file_size_mb=(
            settings.oai_document_max_file_size_mb
        ),
        chunk_size=settings.oai_chunk_size_chars,
        chunk_overlap=(
            settings.oai_chunk_overlap_chars
        ),
    )


def get_memory_service(
    database_session: Session = Depends(get_db),
) -> MemoryService:
    return MemoryService(
        MemoryRepository(
            database_session
        )
    )


def get_project_service(
    database_session: Session = Depends(get_db),
) -> ProjectService:
    return ProjectService(
        ProjectRepository(
            database_session
        )
    )


def get_project_update_proposal_service(
    database_session: Session = Depends(get_db),
) -> ProjectUpdateProposalService:
    project_service = ProjectService(
        ProjectRepository(
            database_session
        )
    )

    return ProjectUpdateProposalService(
        repository=ProjectUpdateProposalRepository(
            database_session
        ),
        conversation_repository=ConversationRepository(
            database_session
        ),
        project_service=project_service,
    )


def get_project_update_turn_orchestrator(
    proposal_service: ProjectUpdateProposalService = Depends(
        get_project_update_proposal_service
    ),
) -> ProjectUpdateTurnOrchestrator:
    return ProjectUpdateTurnOrchestrator(
        generator=ProjectUpdateProposalGenerator(),
        proposal_service=proposal_service,
    )


def get_knowledge_answer_service(
    database_session: Session = Depends(get_db),
    chat_service: ChatService = Depends(
        get_chat_service
    ),
) -> KnowledgeAnswerService:
    settings = get_settings()

    conversation_service = ConversationService(
        ConversationRepository(
            database_session
        ),
        chat_service,
        settings.oai_chat_context_message_limit,
        MessageCitationRepository(
            database_session
        ),
        project_context_resolver=ProjectContextResolver(
            ProjectContextReader(
                database_session
            )
        ),
    )

    knowledge_repository = get_knowledge_repository(
        database_session
    )

    memory_resolver = MemoryResolver(
        MemoryRepository(
            database_session
        ),
        settings.oai_memory_context_max_items,
        settings.oai_memory_context_max_chars,
        settings.oai_memory_context_max_item_chars,
    )

    retrieval_step = RetrievalStep(
        knowledge_repository,
        IntentAnalyzer(),
        RetrievalPlanner(
            settings.oai_knowledge_answer_max_retrieval_queries,
        ),
        settings.oai_knowledge_answer_candidates_per_query,
    )

    evidence_step = EvidenceStep(
        EvidenceRanker(
            settings.oai_knowledge_answer_max_evidence_per_document,
            minimum_score=(
                settings.oai_knowledge_answer_minimum_evidence_score
            ),
        ),
        ConflictDetector(),
        ContextBuilder(
            settings.oai_knowledge_answer_context_char_budget,
        ),
        settings.oai_knowledge_answer_selected_evidence_count,
    )
    reasoning_step = ReasoningStep(
        ReasoningService(),
        memory_resolver,
    )

    planning_step = PlanningStep(
        PlanningService(),
    )

    decision_step = DecisionStep(
        DecisionService(),
    )

    goal_step = GoalStep(
        GoalService(),
    )

    pipeline = Pipeline(
        (
            retrieval_step,
            evidence_step,
            reasoning_step,
            planning_step,
            decision_step,
            goal_step,
        )
    )

    orchestrator = KnowledgeOrchestrator(
        pipeline,
    )

    analyzer = IntentAnalyzer()

    planner = RetrievalPlanner(
        settings.oai_knowledge_answer_max_retrieval_queries,
    )

    ranker = EvidenceRanker(
        settings.oai_knowledge_answer_max_evidence_per_document,
        minimum_score=(
            settings.oai_knowledge_answer_minimum_evidence_score
        ),
    )

    conflict_detector = ConflictDetector()

    context_builder = ContextBuilder(
        settings.oai_knowledge_answer_context_char_budget,
    )

    retrieval_components = RetrievalComponents(
        analyzer=analyzer,
        planner=planner,
        ranker=ranker,
        conflict_detector=conflict_detector,
        context_builder=context_builder,
    )

    retrieval_pipeline = RetrievalPipeline(
        components=retrieval_components,
        repository=knowledge_repository,
        candidates_per_query=settings.oai_knowledge_answer_candidates_per_query,
        selected_limit=settings.oai_knowledge_answer_selected_evidence_count,
    )

    return KnowledgeAnswerService(
        knowledge_repository,
        conversation_service,
        chat_service,
        analyzer,
        planner,
        ranker,
        conflict_detector,
        context_builder,
        GroundedPromptBuilder(),
        CitationEngine(),
        ConfidenceEvaluator(),
        settings.oai_knowledge_answer_candidates_per_query,
        settings.oai_knowledge_answer_selected_evidence_count,
        memory_resolver,
        ReasoningService(),
        PlanningService(),
        DecisionService(),
        GoalService(),
        orchestrator,
        retrieval_pipeline,
    )