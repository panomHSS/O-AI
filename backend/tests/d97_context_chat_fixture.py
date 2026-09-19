"""D97 test composition helper for normal Context-aware Chat fixtures."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.contracts.context_provenance import SystemContextSnapshotClock
from app.contracts.context_resolution import Utf8ByteBudgetCounter
from app.contracts.workspace import WorkspaceScope
from app.repositories.context_snapshots import ContextSnapshotRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.memories import MemoryRepository
from app.repositories.message_citations import MessageCitationRepository
from app.search.factory import create_knowledge_search
from app.services.chat import ChatService
from app.services.context_chat import build_context_chat_budget_policy
from app.services.context_provenance_sources import (
    ConversationProvenanceSource,
    KnowledgeProvenanceSource,
    MemoryProvenanceSource,
    ProjectProvenanceSource,
)
from app.services.context_resolver import ContextResolver
from app.services.context_snapshot import ContextSnapshotService
from app.services.context_sources import (
    ConversationContextSource,
    KnowledgeContextSource,
    MemoryContextSource,
    ProjectContextSource,
)
from app.services.conversations import ConversationService
from app.services.memory_resolver import MemoryResolver
from app.services.project_action_execution_persistence import (
    ProjectActionExecutionPersistenceService,
)
from app.services.project_context import (
    ProjectContextReader,
    ProjectContextResolver,
)


def build_context_aware_conversation_service(
    *,
    session: Session,
    workspace_scope: WorkspaceScope,
    chat_service: ChatService,
    context_message_limit: int,
    memory_max_items: int = 8,
    citation_repository: MessageCitationRepository | None = None,
    memory_resolver: MemoryResolver | None = None,
    project_context_resolver: ProjectContextResolver | None = None,
    project_action_execution_persistence_service: (
        ProjectActionExecutionPersistenceService | None
    ) = None,
) -> ConversationService:
    """Compose the production-shaped D95/D96/D97 normal Chat path for tests."""

    project_resolver = (
        project_context_resolver
        or ProjectContextResolver(
            ProjectContextReader(
                session,
                workspace_scope,
            )
        )
    )
    conversation_repository = ConversationRepository(
        session,
        workspace_scope,
    )
    context_resolver = ContextResolver(
        conversation_source=ConversationContextSource(
            conversation_repository
        ),
        project_source=ProjectContextSource(
            project_resolver
        ),
        memory_source=MemoryContextSource(
            MemoryRepository(
                session,
                workspace_scope,
            )
        ),
        knowledge_source=KnowledgeContextSource(
            create_knowledge_search(session)
        ),
        policy=build_context_chat_budget_policy(
            conversation_message_limit=context_message_limit,
            memory_max_items=memory_max_items,
        ),
        counter=Utf8ByteBudgetCounter(),
    )
    snapshot_service = ContextSnapshotService(
        conversation_source=ConversationProvenanceSource(
            session,
            workspace_scope,
        ),
        project_source=ProjectProvenanceSource(
            session,
            workspace_scope,
        ),
        memory_source=MemoryProvenanceSource(
            session,
            workspace_scope,
        ),
        knowledge_source=KnowledgeProvenanceSource(
            session,
            workspace_scope,
        ),
        clock=SystemContextSnapshotClock(),
    )
    return ConversationService(
        repository=conversation_repository,
        chat_service=chat_service,
        context_message_limit=context_message_limit,
        citation_repository=citation_repository,
        memory_resolver=memory_resolver,
        project_context_resolver=project_resolver,
        project_action_execution_persistence_service=(
            project_action_execution_persistence_service
        ),
        context_resolver=context_resolver,
        context_snapshot_service=snapshot_service,
        context_snapshot_repository=ContextSnapshotRepository(
            session,
            workspace_scope,
        ),
    )
