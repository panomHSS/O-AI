from dataclasses import dataclass
from uuid import UUID

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.context_snapshots import ContextSnapshotRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.message_citations import CitationSnapshot, MessageCitationRepository
from app.schemas.conversations import ConversationDetailResponse, ConversationSummaryResponse, StoredCitationResponse, StoredMessageResponse
from app.schemas.context_usage import ContextUsageResponse
from app.services.chat import ChatContextMessage, ChatService
from app.contracts.ai import AIAdapter
from app.contracts.context_provenance import ContextSnapshot
from app.contracts.context_resolution import ContextResolveRequest
from app.contracts.context_usage import ContextUsage
from app.contracts.workspace import WorkspaceScope, parse_workspace_id
from app.services.context_chat import (
    ContextMemoryUsage,
    memory_usage_from_snapshot,
    project_context_from_snapshot,
    reasoning_evidence_from_snapshot,
)
from app.services.context_resolver import ContextResolutionError, ContextResolver
from app.services.context_usage import (
    context_usage_for_message,
    context_usage_from_snapshot,
)
from app.services.context_snapshot import ContextSnapshotService
from app.services.memory_resolver import MemoryResolver, ResolvedMemory
from app.schemas.reasoning import ReasoningPlan
from app.services.reasoning import ReasoningService
from app.schemas.planning import PlanningPlan
from app.services.planning import PlanningService
from app.schemas.decision import DecisionAnalysis
from app.services.decision import DecisionService
from app.schemas.goals import GoalAnalysis
from app.services.goals import GoalService
from app.services.projects import ProjectNotFoundError
from app.services.project_context import (
    ProjectContext,
    ProjectContextResolver,
    ProjectContextUnavailableError,
)
from app.schemas.project_actions import ProjectActionAnalysis
from app.services.project_actions import ProjectActionService
from app.schemas.project_action_planning import ProjectActionPlan
from app.services.project_action_planning import ProjectActionPlanningService
from app.schemas.project_action_execution import ProjectActionExecutionProposal
from app.services.project_action_execution import (
    ProjectActionExecutionProposalService,
)
from app.services.project_action_execution_persistence import (
    ProjectActionExecutionPersistenceService,
)


TITLE_MAX_LENGTH = 80


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist."""


class ConversationAssociationError(Exception):
    """Raised when an immutable conversation-project timing rule is violated."""


@dataclass(frozen=True)
class ChatTurnResult:
    reply: str
    conversation_id: UUID
    project_id: UUID | None = None
    memories_used: tuple[ResolvedMemory | ContextMemoryUsage, ...] = ()
    reasoning_plan: ReasoningPlan | None = None
    planning_plan: PlanningPlan | None = None
    decision_analysis: DecisionAnalysis | None = None
    goal_analysis: GoalAnalysis | None = None
    project_context: ProjectContext | None = None
    project_action_analysis: ProjectActionAnalysis | None = None
    project_action_plan: ProjectActionPlan | None = None
    project_action_execution_proposal: ProjectActionExecutionProposal | None = None
    context_usage: ContextUsage | None = None


class ConversationService:
    """Coordinates local conversation persistence with provider-neutral chat."""

    def __init__(
        self,
        repository: ConversationRepository,
        chat_service: ChatService,
        context_message_limit: int,
        citation_repository: MessageCitationRepository | None = None,
        memory_resolver: MemoryResolver | None = None,
        reasoning_service: ReasoningService | None = None,
        planning_service: PlanningService | None = None,
        decision_service: DecisionService | None = None,
        goal_service: GoalService | None = None,
        project_context_resolver: ProjectContextResolver | None = None,
        project_action_service: ProjectActionService | None = None,
        project_action_planning_service: ProjectActionPlanningService | None = None,
        project_action_execution_proposal_service: (
            ProjectActionExecutionProposalService | None
        ) = None,
        project_action_execution_persistence_service: (
            ProjectActionExecutionPersistenceService | None
        ) = None,
        context_resolver: ContextResolver | None = None,
        context_snapshot_service: ContextSnapshotService | None = None,
        context_snapshot_repository: ContextSnapshotRepository | None = None,
    ) -> None:
        self._repository = repository
        self._chat_service = chat_service
        self._context_message_limit = context_message_limit
        self._citation_repository = citation_repository
        self._memory_resolver = memory_resolver
        self._reasoning_service = reasoning_service or ReasoningService()
        self._planning_service = planning_service or PlanningService()
        self._decision_service = decision_service or DecisionService()
        self._goal_service = goal_service or GoalService()
        self._project_context_resolver = project_context_resolver
        self._project_action_service = project_action_service or ProjectActionService()
        self._project_action_planning_service = (
            project_action_planning_service or ProjectActionPlanningService()
        )
        self._project_action_execution_proposal_service = (
            project_action_execution_proposal_service
            or ProjectActionExecutionProposalService()
        )
        self._project_action_execution_persistence_service = (
            project_action_execution_persistence_service
        )
        self._context_resolver = context_resolver
        self._context_snapshot_service = context_snapshot_service
        self._context_snapshot_repository = context_snapshot_repository

    @property
    def workspace_id(self) -> str:
        return self._repository.workspace_id

    def default_ai_adapter(self) -> AIAdapter:
        return self._chat_service.default_ai_adapter()

    def send_context_message(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        *,
        ai_adapter: AIAdapter,
    ) -> ChatTurnResult:
        """Run the D97 normal-AI lane over one verified D95/D96 Context truth."""

        if (
            self._context_resolver is None
            or self._context_snapshot_service is None
            or self._context_snapshot_repository is None
        ):
            raise RuntimeError("context_chat_not_configured")
        if ai_adapter is None:
            raise ValueError("context_chat_ai_adapter_required")

        try:
            conversation = self._get_or_create_conversation(
                message,
                conversation_id,
                project_id,
            )
            workspace_scope = WorkspaceScope(
                parse_workspace_id(self._repository.workspace_id)
            )
            request = ContextResolveRequest(
                workspace_scope=workspace_scope,
                query=message,
                conversation_id=conversation.id,
                project_id=conversation.project_id,
            )
            try:
                bundle = self._context_resolver.resolve(request)
            except ContextResolutionError as error:
                if error.code == "context_project_unavailable":
                    raise ProjectContextUnavailableError(
                        "Project context is unavailable."
                    ) from None
                raise
            snapshot = self._context_snapshot_service.capture(bundle)
            context_usage = context_usage_from_snapshot(snapshot)

            project_context = project_context_from_snapshot(snapshot)
            memories = memory_usage_from_snapshot(snapshot)
            evidence_map = reasoning_evidence_from_snapshot(snapshot)
            reasoning_plan = self._reasoning_service.plan_from_evidence_map(
                message,
                evidence_map,
            )
            planning_plan = self._planning_service.plan(reasoning_plan)
            decision_analysis = self._decision_service.analyze(
                reasoning_plan,
                planning_plan,
            )
            goal_analysis = self._goal_service.analyze(
                reasoning_plan,
                planning_plan,
                decision_analysis,
            )

            project_action_analysis = (
                self._project_action_service.analyze(project_context)
                if project_context is not None
                else None
            )
            project_action_plan = (
                self._project_action_planning_service.plan(project_action_analysis)
                if project_action_analysis is not None
                else None
            )
            project_action_execution_proposal = (
                self._project_action_execution_proposal_service.propose(
                    project_action_plan
                )
                if project_action_plan is not None
                else None
            )

            self._repository.add_message(conversation, "user", message)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        if (
            project_action_execution_proposal is not None
            and self._project_action_execution_persistence_service is not None
        ):
            self._project_action_execution_persistence_service.persist(
                project_action_execution_proposal,
                project_id=conversation.project_id,
                conversation_id=conversation.id,
            )

        reply = self._chat_service.send_context_message(
            message=message,
            snapshot=snapshot,
            reasoning_plan=reasoning_plan,
            planning_plan=planning_plan,
            decision_analysis=decision_analysis,
            goal_analysis=goal_analysis,
            ai_adapter=ai_adapter,
        )

        self.complete_context_turn(conversation.id, reply, snapshot)

        return ChatTurnResult(
            reply=reply,
            conversation_id=UUID(conversation.id),
            project_id=UUID(conversation.project_id) if conversation.project_id else None,
            memories_used=memories,
            reasoning_plan=reasoning_plan,
            planning_plan=planning_plan,
            decision_analysis=decision_analysis,
            goal_analysis=goal_analysis,
            project_context=project_context,
            project_action_analysis=project_action_analysis,
            project_action_plan=project_action_plan,
            project_action_execution_proposal=project_action_execution_proposal,
            context_usage=context_usage,
        )

    def send_message(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
        ai_adapter: AIAdapter | None = None,
    ) -> ChatTurnResult:
        conversation, recent_messages = self.begin_turn(
            message,
            conversation_id,
            project_id,
        )
        project_context = self.resolve_project_context(conversation)
        project_action_analysis = (
            self._project_action_service.analyze(project_context)
            if project_context is not None
            else None
        )
        project_action_plan = (
            self._project_action_planning_service.plan(project_action_analysis)
            if project_action_analysis is not None
            else None
        )
        project_action_execution_proposal = (
            self._project_action_execution_proposal_service.propose(
                project_action_plan
            )
            if project_action_plan is not None
            else None
        )
        if (
            project_action_execution_proposal is not None
            and self._project_action_execution_persistence_service is not None
        ):
            self._project_action_execution_persistence_service.persist(
                project_action_execution_proposal,
                project_id=conversation.project_id,
                conversation_id=conversation.id,
            )

        context = [
            ChatContextMessage(role=item.role, content=item.content)
            for item in recent_messages
        ]
        memories = (
            self._memory_resolver.resolve(message)
            if self._memory_resolver
            else ()
        )
        reasoning_plan = self._reasoning_service.plan(message, memories)
        planning_plan = self._planning_service.plan(reasoning_plan)
        decision_analysis = self._decision_service.analyze(
            reasoning_plan,
            planning_plan,
        )
        goal_analysis = self._goal_service.analyze(
            reasoning_plan,
            planning_plan,
            decision_analysis,
        )
        reply = self._chat_service.send_message(
            message,
            context,
            memories,
            reasoning_plan,
            planning_plan,
            decision_analysis,
            goal_analysis,
            project_context,
            ai_adapter,
        )
        self.complete_turn(conversation.id, reply)
        return ChatTurnResult(
            reply=reply,
            conversation_id=UUID(conversation.id),
            project_id=UUID(conversation.project_id) if conversation.project_id else None,
            memories_used=memories,
            reasoning_plan=reasoning_plan,
            planning_plan=planning_plan,
            decision_analysis=decision_analysis,
            goal_analysis=goal_analysis,
            project_context=project_context,
            project_action_analysis=project_action_analysis,
            project_action_plan=project_action_plan,
            project_action_execution_proposal=project_action_execution_proposal,
        )

    def begin_turn(
        self,
        message: str,
        conversation_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> tuple[Conversation, list[ChatContextMessage]]:
        try:
            conversation = self._get_or_create_conversation(
                message,
                conversation_id,
                project_id,
            )
            recent = self._repository.recent_messages(
                conversation.id,
                self._context_message_limit,
            )
            self._repository.add_message(conversation, "user", message)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return conversation, [
            ChatContextMessage(role=item.role, content=item.content)
            for item in recent
        ]

    def complete_context_turn(
        self,
        conversation_id: str,
        reply: str,
        snapshot: ContextSnapshot,
    ) -> None:
        if self._context_snapshot_repository is None:
            raise RuntimeError("context_snapshot_persistence_not_configured")
        conversation = self._require_conversation(UUID(conversation_id))
        try:
            assistant_message = self._repository.add_message(
                conversation,
                "assistant",
                reply,
            )
            self._context_snapshot_repository.add_snapshot(
                assistant_message,
                snapshot,
            )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def complete_turn(
        self,
        conversation_id: str,
        reply: str,
        citations: list[CitationSnapshot] | None = None,
    ) -> None:
        conversation = self._require_conversation(UUID(conversation_id))
        try:
            assistant_message = self._repository.add_message(
                conversation,
                "assistant",
                reply,
            )
            if citations:
                if self._citation_repository is None:
                    raise RuntimeError("Citation persistence is not configured.")
                self._citation_repository.add_snapshots(
                    assistant_message,
                    citations,
                )
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def list_conversations(self) -> list[ConversationSummaryResponse]:
        return [self._to_summary(item) for item in self._repository.list()]

    def get_conversation(self, conversation_id: UUID) -> ConversationDetailResponse:
        conversation = self._require_conversation(conversation_id)
        messages = sorted(
            conversation.messages,
            key=lambda message: (message.created_at, message.id),
        )
        return ConversationDetailResponse(
            **self._to_summary(conversation).model_dump(),
            messages=[self._to_message(message) for message in messages],
        )

    def delete_conversation(self, conversation_id: UUID) -> None:
        conversation = self._require_conversation(conversation_id)
        try:
            self._repository.delete(conversation)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def resolve_project_context(
        self,
        conversation: Conversation,
    ) -> ProjectContext | None:
        return (
            self._project_context_resolver.resolve(conversation.project_id)
            if self._project_context_resolver
            else None
        )

    def _get_or_create_conversation(
        self,
        message: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
    ) -> Conversation:
        if conversation_id is not None:
            if project_id is not None:
                raise ConversationAssociationError(
                    "A project can only be selected when creating a conversation."
                )
            return self._require_conversation(conversation_id)
        if (
            project_id is not None
            and not self._repository.project_exists(str(project_id))
        ):
            raise ProjectNotFoundError("The requested project was not found.")
        return self._repository.create(
            self._create_title(message),
            str(project_id) if project_id else None,
        )

    def _require_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = self._repository.get(str(conversation_id))
        if conversation is None:
            raise ConversationNotFoundError(
                "The requested conversation was not found."
            )
        return conversation

    @staticmethod
    def _create_title(message: str) -> str:
        normalized = " ".join(message.split())
        return normalized[:TITLE_MAX_LENGTH] or "New conversation"

    @staticmethod
    def _to_summary(conversation: Conversation) -> ConversationSummaryResponse:
        return ConversationSummaryResponse(
            id=UUID(conversation.id),
            workspace_id=conversation.workspace_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            project_id=UUID(conversation.project_id) if conversation.project_id else None,
        )

    def _to_message(self, message: Message) -> StoredMessageResponse:
        usage = (
            context_usage_for_message(
                self._context_snapshot_repository,
                message.id,
            )
            if (
                message.role == "assistant"
                and self._context_snapshot_repository is not None
            )
            else None
        )
        return StoredMessageResponse(
            id=UUID(message.id),
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            context_usage=(
                ContextUsageResponse.from_usage(usage)
                if usage is not None
                else None
            ),
            citations=[
                StoredCitationResponse(
                    id=UUID(citation.id),
                    citation_id=citation.citation_id,
                    order=citation.citation_order,
                    document_id=UUID(citation.document_id),
                    file_name=citation.file_name,
                    source_path=citation.source_path,
                    source_locator=citation.source_locator,
                    excerpt=citation.excerpt,
                    excerpt_hash=citation.excerpt_hash,
                    confidence=citation.confidence,
                    evidence_type=citation.evidence_type,
                )
                for citation in sorted(
                    message.citations,
                    key=lambda item: item.citation_order,
                )
            ],
        )
