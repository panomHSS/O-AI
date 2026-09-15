from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from app.contracts.execution_audit import AuditSink
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.adapters.chatgpt import ChatGPTAdapter
from app.adapters.local_ai import LocalAIAdapter
from app.adapters.plugin_echo_module import EchoPluginModuleAdapter
from app.adapters.project_snapshot_module import ProjectSnapshotModuleAdapter
from app.adapters.workspace_overview_module import WorkspaceOverviewModuleAdapter
from app.adapters.standard_tool import StandardToolAdapter
from app.adapters.filesystem_tools import (
    FilesystemListToolAdapter,
    FilesystemReadTextToolAdapter,
    FilesystemStatToolAdapter,
)
from app.adapters.filesystem_write_tools import (
    FilesystemCreateTextToolAdapter,
    FilesystemReplaceTextToolAdapter,
)
from app.adapters.system_health_tool import SystemHealthToolAdapter
from app.adapters.system_info_tool import SystemInfoToolAdapter
from app.services.tool_filesystem_boundary import ToolFilesystemBoundary
from app.db.session import get_db
from app.providers.openai_provider import OpenAIChatProvider
from app.plugins.default_plugin_discovery import DefaultPluginDiscovery
from app.plugins.explicit_plugin_factory_loader import ExplicitPluginFactoryLoader
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
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.plugin_projection_catalog import (
    PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS,
    PluginProjectionCatalog,
)
from app.services.plugin_candidate_discovery import PluginCandidateDiscovery
from app.services.plugin_governance import (
    PluginGovernanceDecisionStore,
    PluginGovernanceService,
)
from app.services.plugin_loading import (
    LoadedPluginStore,
    PluginLoadingService,
)
from app.services.plugin_module_exposure import (
    PluginModuleExposureService,
    PluginModuleExposureStore,
)
from app.services.plugin_permission_binding import (
    PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES,
    PluginPermissionBindingService,
    PluginPermissionBindingStore,
    PluginPermissionProfileCatalog,
)
from app.services.plugin_registration_activation import (
    PluginRegistrationActivationService,
    PluginRegistrationActivationStore,
    PluginRuntimeActivationSnapshot,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID
from app.telemetry.system_metrics import SystemMetricsProvider
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.chat_action_bridge import ChatActionBridge
from app.services.chat_plugin_action import (
    ChatPluginActionBindingStore,
    ChatPluginActionCompletionService,
    FirstPartyPluginEnablementService,
)
from app.services.tool_module_router import ToolModuleRouter
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
from app.services.ai_adapter_registry import AIAdapterRegistry
from app.services.command_orchestrator import CommandOrchestrator
from app.services.command_execution_coordinator import (
    CommandExecutionCoordinator,
)
from app.services.execution_approval_service import (
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_planner import ExecutionPlanner
from app.services.execution_guard import ExecutionGuard
from app.services.execution_audit import ExecutionAuditTrail, LoggingAuditSink
from app.services.execution_audit_persistence import (
    CompositeAuditSink,
    DatabaseAuditSink,
)
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime
from app.services.ai_runtime import AIRuntime
from app.services.ai_capability_model_discovery import AICapabilityModelDiscovery
from app.services.ai_discovery_sources import (
    ChatGPTConfiguredModelDiscoverySource,
    LocalAIModelDiscoverySource,
)
from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_runtime_factory import LocalAIRuntimeFactory
from app.contracts.ai_route import LOCAL_AI_ADAPTER_ID
from app.contracts.local_ai_runtime import LocalAIRuntimeClient
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


def get_ai_provider_routing_policy() -> AIProviderRoutingPolicy:
    """Translate deployment settings into immutable D32 route enablement."""
    settings = get_settings()
    enabled = {CHATGPT_DEFAULT_ADAPTER_ID}
    if settings.oai_local_ai_enabled:
        enabled.add(LOCAL_AI_ADAPTER_ID)
    return AIProviderRoutingPolicy(
        default_adapter_id=CHATGPT_DEFAULT_ADAPTER_ID,
        enabled_adapter_ids=frozenset(enabled),
    )


def get_local_ai_config() -> LocalAIAdapterConfig:
    """Translate deployment settings into immutable D33 Local AI configuration."""
    settings = get_settings()
    return LocalAIAdapterConfig(
        enabled=settings.oai_local_ai_enabled,
        backend_id=settings.oai_local_ai_backend,
        model=settings.oai_local_ai_model,
        base_url=settings.oai_local_ai_base_url,
        timeout_seconds=settings.oai_local_ai_timeout_seconds,
        context_length=settings.oai_local_ai_context_length,
    )


def get_local_ai_runtime_factory() -> LocalAIRuntimeFactory:
    """Expose explicit, fail-closed D33 Local AI runtime construction."""
    return LocalAIRuntimeFactory()


def get_local_ai_runtime_client(
    config: LocalAIAdapterConfig = Depends(get_local_ai_config),
    factory: LocalAIRuntimeFactory = Depends(get_local_ai_runtime_factory),
) -> LocalAIRuntimeClient:
    """Resolve the configured Local AI backend without probing or fallback."""
    return factory.create(
        backend_id=config.backend_id,
        base_url=config.base_url,
    )


def get_local_ai_telemetry_provider(
    config: LocalAIAdapterConfig = Depends(get_local_ai_config),
    runtime_client: LocalAIRuntimeClient = Depends(get_local_ai_runtime_client),
) -> SystemMetricsProvider:
    """Share the provider-neutral D33 runtime with best-effort D26 telemetry."""
    return SystemMetricsProvider(
        runtime_client=runtime_client,
        model=config.model,
    )


def get_local_ai_adapter(
    config: LocalAIAdapterConfig = Depends(get_local_ai_config),
    runtime_client: LocalAIRuntimeClient = Depends(get_local_ai_runtime_client),
    telemetry_provider: SystemMetricsProvider = Depends(
        get_local_ai_telemetry_provider
    ),
) -> LocalAIAdapter:
    """Compose LocalAIAdapter without coupling it to a runtime implementation."""
    return LocalAIAdapter(
        runtime_client=runtime_client,
        enabled=config.enabled,
        model=config.model,
        timeout_seconds=config.timeout_seconds,
        context_length=config.context_length,
        telemetry_provider=telemetry_provider,
    )


def get_standard_tool_adapter() -> StandardToolAdapter:
    """Compose the D27 deterministic, read-only standard tool adapter."""
    return StandardToolAdapter()


@lru_cache
def get_tool_catalog_adapters() -> tuple[object, ...]:
    """Compose the bounded D42 read-only Tool Catalog."""
    workspace_root = Path(__file__).resolve().parents[3]
    boundary = ToolFilesystemBoundary(workspace_root)
    return (
        SystemInfoToolAdapter(),
        SystemHealthToolAdapter(workspace_root),
        FilesystemListToolAdapter(boundary),
        FilesystemStatToolAdapter(boundary),
        FilesystemReadTextToolAdapter(boundary),
    )


@lru_cache
def get_safe_write_tool_adapters() -> tuple[object, ...]:
    """Compose the approval-gated D48 safe-write Tool Catalog."""
    workspace_root = Path(__file__).resolve().parents[3]
    boundary = ToolFilesystemBoundary(workspace_root)
    return (
        FilesystemCreateTextToolAdapter(boundary),
        FilesystemReplaceTextToolAdapter(boundary),
    )


def get_module_catalog_adapters(
    database_session: Session = Depends(get_db),
) -> tuple[object, ...]:
    """Compose D43 modules plus the explicit D51 Plugin bridge."""
    workspace_root = Path(__file__).resolve().parents[3]
    project_resolver = ProjectContextResolver(
        ProjectContextReader(database_session)
    )
    return (
        WorkspaceOverviewModuleAdapter(workspace_root),
        ProjectSnapshotModuleAdapter(project_resolver),
        EchoPluginModuleAdapter(),
    )


@lru_cache
def get_plugin_projection_catalog() -> PluginProjectionCatalog:
    """Compose the immutable, metadata-only D52 Plugin projection snapshot."""
    return PluginProjectionCatalog(
        PRODUCTION_PLUGIN_CAPABILITY_PROJECTIONS
    )


@lru_cache
def get_plugin_discovery() -> DefaultPluginDiscovery:
    """Compose the legacy metadata-only Plugin discovery source for D53."""
    return DefaultPluginDiscovery()


@lru_cache
def get_plugin_candidate_discovery() -> PluginCandidateDiscovery:
    """Compose D53 reconciliation without Plugin loading or execution."""
    return PluginCandidateDiscovery(
        discovery=get_plugin_discovery(),
        projection_catalog=get_plugin_projection_catalog(),
    )


@lru_cache
def get_plugin_governance_store() -> PluginGovernanceDecisionStore:
    """Compose the bounded process-local D54 governance decision store."""
    return PluginGovernanceDecisionStore()


@lru_cache
def get_plugin_governance_service() -> PluginGovernanceService:
    """Compose D54 admission governance without loading or execution authority."""
    return PluginGovernanceService(
        candidate_discovery=get_plugin_candidate_discovery(),
        store=get_plugin_governance_store(),
    )


@lru_cache
def get_controlled_plugin_loader() -> ExplicitPluginFactoryLoader:
    """Compose the exact static D55 Plugin factory allowlist."""
    return ExplicitPluginFactoryLoader()


@lru_cache
def get_loaded_plugin_store() -> LoadedPluginStore:
    """Compose the bounded process-local D55 loaded Plugin store."""
    return LoadedPluginStore()


@lru_cache
def get_plugin_loading_service() -> PluginLoadingService:
    """Compose D55 loading without registration, exposure, or execution."""
    return PluginLoadingService(
        candidate_discovery=get_plugin_candidate_discovery(),
        governance=get_plugin_governance_service(),
        loader=get_controlled_plugin_loader(),
        store=get_loaded_plugin_store(),
    )


@lru_cache
def get_plugin_module_exposure_store() -> PluginModuleExposureStore:
    """Compose the bounded process-local D56 Module exposure store."""
    return PluginModuleExposureStore()


@lru_cache
def get_plugin_module_exposure_service() -> PluginModuleExposureService:
    """Compose D56 exposure without AdapterRegistry or permission authority."""
    return PluginModuleExposureService(
        projection_catalog=get_plugin_projection_catalog(),
        candidate_discovery=get_plugin_candidate_discovery(),
        governance=get_plugin_governance_service(),
        loading=get_plugin_loading_service(),
        loaded_store=get_loaded_plugin_store(),
        exposure_store=get_plugin_module_exposure_store(),
    )


@lru_cache
def get_plugin_permission_profile_catalog() -> PluginPermissionProfileCatalog:
    """Compose the immutable default-deny D57 Plugin permission profiles."""
    return PluginPermissionProfileCatalog(PRODUCTION_PLUGIN_CAPABILITY_PERMISSION_PROFILES)


@lru_cache
def get_plugin_permission_binding_store() -> PluginPermissionBindingStore:
    """Compose the bounded process-local D57 permission binding store."""
    return PluginPermissionBindingStore()


@lru_cache
def get_plugin_permission_binding_service() -> PluginPermissionBindingService:
    """Compose D57 permission intent without registration or D44 activation."""
    return PluginPermissionBindingService(
        exposure_service=get_plugin_module_exposure_service(),
        profile_catalog=get_plugin_permission_profile_catalog(),
        store=get_plugin_permission_binding_store(),
        reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
    )


@lru_cache
def get_plugin_registration_activation_store() -> PluginRegistrationActivationStore:
    """Compose the bounded process-local D58 activation authority store."""
    return PluginRegistrationActivationStore()


@lru_cache
def get_plugin_registration_activation_service() -> PluginRegistrationActivationService:
    """Compose D58 activation without approval, authorization, or execution."""
    reserved_adapter_ids = frozenset(
        {
            CHATGPT_DEFAULT_ADAPTER_ID,
            LOCAL_AI_ADAPTER_ID,
            *(
                permission.adapter_id
                for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            ),
        }
    )
    return PluginRegistrationActivationService(
        binding_service=get_plugin_permission_binding_service(),
        exposure_service=get_plugin_module_exposure_service(),
        store=get_plugin_registration_activation_store(),
        reserved_adapter_ids=reserved_adapter_ids,
        reserved_permissions=PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
    )


@lru_cache
def get_first_party_plugin_enablement_service() -> FirstPartyPluginEnablementService:
    """Compose D61 owner-configured first-party Plugin lifecycle materialization."""
    return FirstPartyPluginEnablementService(
        governance=get_plugin_governance_service(),
        loading=get_plugin_loading_service(),
        exposure=get_plugin_module_exposure_service(),
        binding=get_plugin_permission_binding_service(),
        activation=get_plugin_registration_activation_service(),
    )


def get_plugin_runtime_activation_snapshot() -> PluginRuntimeActivationSnapshot:
    """Materialize configured first-party Plugins, then capture one D58 snapshot."""
    settings = get_settings()
    get_first_party_plugin_enablement_service().ensure_github_public_repository_enabled(
        settings.oai_github_public_repo_connector_enabled
    )
    return get_plugin_registration_activation_service().runtime_snapshot()


def get_adapter_registry(
    conversation_service: ConversationService = Depends(get_conversation_service),
    chat_service: ChatService = Depends(get_chat_service),
    local_ai_adapter: LocalAIAdapter = Depends(get_local_ai_adapter),
    standard_tool_adapter: StandardToolAdapter = Depends(get_standard_tool_adapter),
    tool_catalog_adapters: tuple[object, ...] = Depends(get_tool_catalog_adapters),
    safe_write_tool_adapters: tuple[object, ...] = Depends(
        get_safe_write_tool_adapters
    ),
    module_catalog_adapters: tuple[object, ...] = Depends(get_module_catalog_adapters),
    plugin_activation_snapshot: PluginRuntimeActivationSnapshot = Depends(
        get_plugin_runtime_activation_snapshot
    ),
) -> AdapterRegistry:
    """Compose D31 plus one coherent D58 immutable activation snapshot."""
    if not isinstance(plugin_activation_snapshot, PluginRuntimeActivationSnapshot):
        plugin_activation_snapshot = PluginRuntimeActivationSnapshot()
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
            *tool_catalog_adapters,
            *safe_write_tool_adapters,
            *module_catalog_adapters,
            *plugin_activation_snapshot.adapters,
        )
    )

def get_ai_router(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    policy: AIProviderRoutingPolicy = Depends(get_ai_provider_routing_policy),
) -> AIRouter:
    """Compose D32 routing from the shared registry and immutable policy."""
    return AIRouter(
        registry=adapter_registry,
        policy=policy,
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


_D49_PROVIDER_MANAGED_MODEL_ID = "provider-managed"


def get_chatgpt_model_discovery_source(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatGPTConfiguredModelDiscoverySource:
    """Describe the active ChatGPT-compatible model binding without probing.

    Production OpenAI continues to require its explicit OPENAI_MODEL setting.
    Legacy/injected conversation-provider seams that do not expose model
    discovery receive an opaque provider-managed binding used only as D49
    authorization metadata; it is never forwarded as a provider model override.
    """
    settings = get_settings()
    configured_model_id = settings.openai_model

    if configured_model_id is None:
        adapter_factory = getattr(
            conversation_service,
            "default_ai_adapter",
            None,
        )
        if not callable(adapter_factory):
            configured_model_id = _D49_PROVIDER_MANAGED_MODEL_ID
        else:
            selected_adapter = adapter_factory()
            if selected_adapter is not get_chatgpt_adapter():
                configured_model_id = _D49_PROVIDER_MANAGED_MODEL_ID

    return ChatGPTConfiguredModelDiscoverySource(
        configured_model_id=configured_model_id,
    )


def get_local_ai_model_discovery_source(
    config: LocalAIAdapterConfig = Depends(get_local_ai_config),
    runtime_client: LocalAIRuntimeClient = Depends(get_local_ai_runtime_client),
) -> LocalAIModelDiscoverySource:
    """Compose read-only Local AI discovery over the D33 runtime seam."""
    return LocalAIModelDiscoverySource(
        enabled=config.enabled,
        configured_model_id=config.model,
        runtime_client=runtime_client,
    )


def get_ai_capability_model_discovery(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    chatgpt_source: ChatGPTConfiguredModelDiscoverySource = Depends(
        get_chatgpt_model_discovery_source
    ),
    local_ai_source: LocalAIModelDiscoverySource = Depends(
        get_local_ai_model_discovery_source
    ),
) -> AICapabilityModelDiscovery:
    """Compose D34 metadata discovery without routing or execution."""
    return AICapabilityModelDiscovery(
        registry=adapter_registry,
        sources=(chatgpt_source, local_ai_source),
    )

def get_ai_adapter_registry(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
) -> AIAdapterRegistry:
    """Preserve the D29 AI registry surface over the shared D31 registry."""
    return AIAdapterRegistry(registry=adapter_registry)


def get_audit_sink(
    database_session: Session = Depends(get_db),
) -> AuditSink:
    """Compose D47 durable audit plus D39 structured logging."""
    bind = database_session.get_bind()
    audit_bind = getattr(bind, "engine", bind)
    audit_session_factory = sessionmaker(
        bind=audit_bind,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return CompositeAuditSink(
        (
            LoggingAuditSink(),
            DatabaseAuditSink(
                audit_session_factory
            ),
        )
    )


def get_execution_audit_trail(
    audit_sink: AuditSink = Depends(get_audit_sink),
) -> ExecutionAuditTrail:
    """Compose non-authoritative D39 execution observation."""
    return ExecutionAuditTrail(sink=audit_sink)


def get_tool_runtime(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    audit: ExecutionAuditTrail = Depends(get_execution_audit_trail),
) -> ToolRuntime:
    """Compose D38 Tool runtime with D39 observation."""
    return ToolRuntime(registry=adapter_registry, audit=audit)


def get_module_runtime(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    audit: ExecutionAuditTrail = Depends(get_execution_audit_trail),
) -> ModuleRuntime:
    """Compose D37 Module runtime with D39 observation."""
    return ModuleRuntime(registry=adapter_registry, audit=audit)


def get_ai_runtime(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    audit: ExecutionAuditTrail = Depends(get_execution_audit_trail),
) -> AIRuntime:
    """Compose D49 AI runtime over the shared registry and D47 audit."""
    return AIRuntime(
        registry=adapter_registry,
        audit=audit,
    )


def get_capability_permission_policy(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    plugin_activation_snapshot: PluginRuntimeActivationSnapshot = Depends(
        get_plugin_runtime_activation_snapshot
    ),
) -> CapabilityPermissionPolicy:
    """Compose D44 from static permissions plus the same D58 snapshot."""
    if not isinstance(plugin_activation_snapshot, PluginRuntimeActivationSnapshot):
        plugin_activation_snapshot = PluginRuntimeActivationSnapshot()
    return CapabilityPermissionPolicy(
        registry=adapter_registry,
        permissions=(
            *PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
            *plugin_activation_snapshot.permissions,
        ),
    )


def get_execution_guard(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    permission_policy: CapabilityPermissionPolicy = Depends(
        get_capability_permission_policy
    ),
    audit: ExecutionAuditTrail = Depends(get_execution_audit_trail),
) -> ExecutionGuard:
    """Compose D36 authorization with D44 policy and D39 observation."""
    return ExecutionGuard(
        registry=adapter_registry,
        permission_policy=permission_policy,
        audit=audit,
    )


def get_execution_planner(
    adapter_registry: AdapterRegistry = Depends(get_adapter_registry),
    decision_engine: CommandDecisionEngine = Depends(get_command_decision_engine),
    ai_router: AIRouter = Depends(get_ai_router),
    ai_discovery: AICapabilityModelDiscovery = Depends(
        get_ai_capability_model_discovery
    ),
    permission_policy: CapabilityPermissionPolicy = Depends(
        get_capability_permission_policy
    ),
    audit: ExecutionAuditTrail = Depends(get_execution_audit_trail),
) -> ExecutionPlanner:
    """Compose D35 planning with D44 policy and D39 observation."""
    return ExecutionPlanner(
        registry=adapter_registry,
        decision_engine=decision_engine,
        ai_router=ai_router,
        ai_discovery=ai_discovery,
        permission_policy=permission_policy,
        audit=audit,
    )

@lru_cache
def get_pending_execution_approval_store() -> PendingExecutionApprovalStore:
    """Compose the process-local bounded D45 one-time approval store."""
    return PendingExecutionApprovalStore()


def get_command_execution_coordinator(
    planner: ExecutionPlanner = Depends(get_execution_planner),
    guard: ExecutionGuard = Depends(get_execution_guard),
    tool_runtime: ToolRuntime = Depends(get_tool_runtime),
    module_runtime: ModuleRuntime = Depends(get_module_runtime),
) -> CommandExecutionCoordinator:
    """Compose the frozen D40 Tool/Module integration boundary."""
    return CommandExecutionCoordinator(
        planner=planner,
        guard=guard,
        tool_runtime=tool_runtime,
        module_runtime=module_runtime,
    )


def get_execution_approval_service(
    planner: ExecutionPlanner = Depends(get_execution_planner),
    permission_policy: CapabilityPermissionPolicy = Depends(
        get_capability_permission_policy
    ),
    coordinator: CommandExecutionCoordinator = Depends(
        get_command_execution_coordinator
    ),
    store: PendingExecutionApprovalStore = Depends(
        get_pending_execution_approval_store
    ),
) -> ExecutionApprovalService:
    """Compose D45 review/decision without moving execution authority."""
    return ExecutionApprovalService(
        planner=planner,
        permission_policy=permission_policy,
        coordinator=coordinator,
        store=store,
    )


@lru_cache
def get_chat_plugin_action_binding_store() -> ChatPluginActionBindingStore:
    """Compose bounded process-local D61 Chat/approval correlation metadata."""
    return ChatPluginActionBindingStore()


def get_chat_action_bridge(
    conversation_service: ConversationService = Depends(
        get_conversation_service
    ),
    approval_service: ExecutionApprovalService = Depends(
        get_execution_approval_service
    ),
    plugin_binding_store: ChatPluginActionBindingStore = Depends(
        get_chat_plugin_action_binding_store
    ),
) -> ChatActionBridge:
    """Compose D46/D61 Chat action routing over existing D45 authority."""
    settings = get_settings()
    return ChatActionBridge(
        conversation_service=conversation_service,
        approval_service=approval_service,
        plugin_binding_store=plugin_binding_store,
        github_public_repo_connector_enabled=(
            settings.oai_github_public_repo_connector_enabled
        ),
    )


def get_chat_plugin_action_completion_service(
    conversation_service: ConversationService = Depends(
        get_conversation_service
    ),
    binding_store: ChatPluginActionBindingStore = Depends(
        get_chat_plugin_action_binding_store
    ),
) -> ChatPluginActionCompletionService:
    """Compose non-authoritative D61 Plugin-result Chat finalization."""
    return ChatPluginActionCompletionService(
        conversation_service=conversation_service,
        binding_store=binding_store,
    )


def get_command_orchestrator(
    conversation_service: ConversationService = Depends(get_conversation_service),
    planner: ExecutionPlanner = Depends(get_execution_planner),
    guard: ExecutionGuard = Depends(get_execution_guard),
    ai_runtime: AIRuntime = Depends(get_ai_runtime),
    error_normalizer: OrchestrationErrorNormalizer = Depends(
        get_orchestration_error_normalizer
    ),
    response_composer: ResponseComposer = Depends(get_response_composer),
    tool_runtime: ToolRuntime = Depends(get_tool_runtime),
) -> CommandOrchestrator:
    """Compose D49 normal chat through Planner, Guard and AIRuntime."""
    return CommandOrchestrator(
        conversation_service=conversation_service,
        planner=planner,
        guard=guard,
        ai_runtime=ai_runtime,
        error_normalizer=error_normalizer,
        response_composer=response_composer,
        tool_runtime=tool_runtime,
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
    execution_planner: ExecutionPlanner = Depends(
        get_execution_planner
    ),
    execution_guard: ExecutionGuard = Depends(
        get_execution_guard
    ),
    ai_runtime: AIRuntime = Depends(
        get_ai_runtime
    ),
    error_normalizer: OrchestrationErrorNormalizer = Depends(
        get_orchestration_error_normalizer
    ),
    response_composer: ResponseComposer = Depends(
        get_response_composer
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
        execution_planner=execution_planner,
        execution_guard=execution_guard,
        ai_runtime=ai_runtime,
        error_normalizer=error_normalizer,
        response_composer=response_composer,
    )
