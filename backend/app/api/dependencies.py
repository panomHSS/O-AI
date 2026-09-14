from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.adapters.chatgpt import ChatGPTAdapter
from app.adapters.local_ai import LocalAIAdapter
from app.adapters.ollama_runtime import OllamaRuntimeClient
from app.adapters.standard_tool import StandardToolAdapter
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
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_router import AIRouter
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.telemetry.system_metrics import SystemMetricsProvider
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.tool_module_router import ToolModuleRouter
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
from app.services.ai_adapter_registry import AIAdapterRegistry
from app.services.command_orchestrator import CommandOrchestrator
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
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
def get_chatgpt_adapter() -> ChatGPTAdapter:
    """Compose the configured ChatGPT adapter around the legacy provider."""
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

    return ChatGPTAdapter(provider)


@lru_cache
def get_chat_service() -> ChatService:
    """Compose the legacy chat service behind its ChatGPT compatibility adapter."""
    return ChatService(provider=get_chatgpt_adapter())


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


def get_command_decision_engine() -> CommandDecisionEngine:
    """Compose the pure D23 command decision engine."""
    return CommandDecisionEngine()


def get_ai_router() -> AIRouter:
    """Expose Local AI to D24 only when deployment enables it."""
    settings = get_settings()
    available = [CHATGPT_DEFAULT_ADAPTER_ID]
    if settings.oai_local_ai_enabled:
        available.append(LOCAL_AI_ADAPTER_ID)
    return AIRouter(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        available_adapter_ids=available,
    )


def get_local_ai_adapter() -> LocalAIAdapter:
    """Compose D26 Local AI without changing D24 route execution behavior."""
    settings = get_settings()
    runtime_client = OllamaRuntimeClient(base_url=settings.oai_local_ai_base_url)
    return LocalAIAdapter(
        runtime_client=runtime_client,
        enabled=settings.oai_local_ai_enabled,
        model=settings.oai_local_ai_model,
        timeout_seconds=settings.oai_local_ai_timeout_seconds,
        context_length=settings.oai_local_ai_context_length,
        telemetry_provider=SystemMetricsProvider(
            runtime_client=runtime_client,
            model=settings.oai_local_ai_model,
        ),
    )


def get_standard_tool_adapter() -> StandardToolAdapter:
    """Compose the D27 deterministic, read-only standard tool adapter."""
    return StandardToolAdapter()


def get_adapter_registry(
    conversation_service: ConversationService = Depends(get_conversation_service),
    chat_service: ChatService = Depends(get_chat_service),
    local_ai_adapter: LocalAIAdapter = Depends(get_local_ai_adapter),
    standard_tool_adapter: StandardToolAdapter = Depends(get_standard_tool_adapter),
) -> AdapterRegistry:
    """Compose D31 while preserving the D29 default AI adapter seam."""
    default_adapter_factory = getattr(
        conversation_service,
        "default_ai_adapter",
        chat_service.default_ai_adapter,
    )
    return AdapterRegistry(
        (
            default_adapter_factory(),
            local_ai_adapter,
            standard_tool_adapter,
        )
    )

def get_tool_module_router(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
) -> ToolModuleRouter:
    """Expose the shared D31 registry through the D27 selection boundary."""
    return ToolModuleRouter(registry=adapter_registry)


def get_orchestration_error_normalizer() -> OrchestrationErrorNormalizer:
    """Compose the pure D28 safe-error classification boundary."""
    return OrchestrationErrorNormalizer()


def get_response_composer(
    normalizer: OrchestrationErrorNormalizer = Depends(
        get_orchestration_error_normalizer
    ),
) -> ResponseComposer:
    """Compose D28 presentation without wiring orchestration into chat."""
    return ResponseComposer(normalizer)


def get_ai_adapter_registry(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
) -> AIAdapterRegistry:
    """Preserve the D29 AI registry surface over the shared D31 registry."""
    return AIAdapterRegistry(registry=adapter_registry)


def get_command_orchestrator(
    conversation_service: ConversationService = Depends(get_conversation_service),
    decision_engine: CommandDecisionEngine = Depends(get_command_decision_engine),
    ai_router: AIRouter = Depends(get_ai_router),
    ai_adapters: AIAdapterRegistry = Depends(get_ai_adapter_registry),
    error_normalizer: OrchestrationErrorNormalizer = Depends(
        get_orchestration_error_normalizer
    ),
    response_composer: ResponseComposer = Depends(get_response_composer),
    tool_module_router: ToolModuleRouter = Depends(get_tool_module_router),
) -> CommandOrchestrator:
    """Compose D29 only at the existing chat input boundary."""
    return CommandOrchestrator(
        conversation_service=conversation_service,
        decision_engine=decision_engine,
        ai_router=ai_router,
        ai_adapters=ai_adapters,
        error_normalizer=error_normalizer,
        response_composer=response_composer,
        tool_module_router=tool_module_router,
    )


def get_command_input_pipeline(
    conversation_service: ConversationService = Depends(
        get_conversation_service
    ),
    decision_engine: CommandDecisionEngine = Depends(
        get_command_decision_engine
    ),
    ai_router: AIRouter = Depends(get_ai_router),
) -> CommandInputPipeline:
    """Compose the narrow D22 chat input boundary."""
    return CommandInputPipeline(
        conversation_service,
        decision_engine,
        ai_router,
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
