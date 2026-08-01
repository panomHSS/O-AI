from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversations import ConversationRepository
from app.repositories.message_citations import CitationSnapshot, MessageCitationRepository
from app.schemas.conversations import ConversationDetailResponse, ConversationSummaryResponse, StoredCitationResponse, StoredMessageResponse
from app.services.chat import ChatContextMessage, ChatService
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
from app.services.project_context import ProjectContext, ProjectContextResolver

TITLE_MAX_LENGTH = 80


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist."""


class ConversationAssociationError(Exception):
    """Raised when an immutable conversation-project timing rule is violated."""


@dataclass(frozen=True)
class ChatTurnResult:
    reply: str
    conversation_id: UUID
    memories_used: tuple[ResolvedMemory, ...] = ()
    reasoning_plan: ReasoningPlan | None = None
    planning_plan: PlanningPlan | None = None
    decision_analysis: DecisionAnalysis | None = None
    goal_analysis: GoalAnalysis | None = None


class ConversationService:
    """Coordinates local conversation persistence with provider-neutral chat."""

    def __init__(self, repository: ConversationRepository, chat_service: ChatService, context_message_limit: int, citation_repository: MessageCitationRepository | None = None, memory_resolver: MemoryResolver | None = None, reasoning_service: ReasoningService | None = None, planning_service: PlanningService | None = None, decision_service: DecisionService | None = None, goal_service: GoalService | None = None, project_context_resolver: ProjectContextResolver | None = None) -> None:
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

    def send_message(self, message: str, conversation_id: UUID | None = None, project_id: UUID | None = None) -> ChatTurnResult:
        conversation, recent_messages = self.begin_turn(message, conversation_id, project_id)
        project_context = self.resolve_project_context(conversation)

        context = [ChatContextMessage(role=item.role, content=item.content) for item in recent_messages]
        memories = self._memory_resolver.resolve(message) if self._memory_resolver else ()
        reasoning_plan = self._reasoning_service.plan(message, memories)
        planning_plan = self._planning_service.plan(reasoning_plan)
        decision_analysis = self._decision_service.analyze(reasoning_plan, planning_plan)
        goal_analysis = self._goal_service.analyze(reasoning_plan, planning_plan, decision_analysis)
        reply = self._chat_service.send_message(message, context, memories, reasoning_plan, planning_plan, decision_analysis, goal_analysis, project_context)

        self.complete_turn(conversation.id, reply)

        return ChatTurnResult(reply=reply, conversation_id=UUID(conversation.id), memories_used=memories, reasoning_plan=reasoning_plan, planning_plan=planning_plan, decision_analysis=decision_analysis, goal_analysis=goal_analysis)

    def begin_turn(self, message: str, conversation_id: UUID | None = None, project_id: UUID | None = None) -> tuple[Conversation, list[ChatContextMessage]]:
        """Persist a final user turn and return bounded history for another orchestrator."""
        try:
            conversation = self._get_or_create_conversation(message, conversation_id, project_id)
            recent = self._repository.recent_messages(conversation.id, self._context_message_limit)
            self._repository.add_message(conversation, "user", message)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return conversation, [ChatContextMessage(role=item.role, content=item.content) for item in recent]

    def complete_turn(self, conversation_id: str, reply: str, citations: list[CitationSnapshot] | None = None) -> None:
        conversation = self._require_conversation(UUID(conversation_id))
        try:
            assistant_message = self._repository.add_message(conversation, "assistant", reply)
            if citations:
                if self._citation_repository is None:
                    raise RuntimeError("Citation persistence is not configured.")
                self._citation_repository.add_snapshots(assistant_message, citations)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def list_conversations(self) -> list[ConversationSummaryResponse]:
        return [self._to_summary(conversation) for conversation in self._repository.list()]

    def get_conversation(self, conversation_id: UUID) -> ConversationDetailResponse:
        conversation = self._require_conversation(conversation_id)
        messages = sorted(conversation.messages, key=lambda message: (message.created_at, message.id))
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

    def resolve_project_context(self, conversation: Conversation) -> ProjectContext | None:
        """Resolve only current approved Project fields for one provider request."""
        return self._project_context_resolver.resolve(conversation.project_id) if self._project_context_resolver else None

    def _get_or_create_conversation(self, message: str, conversation_id: UUID | None, project_id: UUID | None) -> Conversation:
        if conversation_id is not None:
            if project_id is not None:
                raise ConversationAssociationError("A project can only be selected when creating a conversation.")
            return self._require_conversation(conversation_id)
        if project_id is not None and not self._repository.project_exists(str(project_id)):
            raise ProjectNotFoundError("The requested project was not found.")
        return self._repository.create(self._create_title(message), str(project_id) if project_id else None)

    def _require_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = self._repository.get(str(conversation_id))
        if conversation is None:
            raise ConversationNotFoundError("The requested conversation was not found.")
        return conversation

    @staticmethod
    def _create_title(message: str) -> str:
        normalized = " ".join(message.split())
        return (normalized[:TITLE_MAX_LENGTH] or "New conversation")

    @staticmethod
    def _to_summary(conversation: Conversation) -> ConversationSummaryResponse:
        return ConversationSummaryResponse(
            id=UUID(conversation.id),
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            project_id=UUID(conversation.project_id) if conversation.project_id else None,
        )

    @staticmethod
    def _to_message(message: Message) -> StoredMessageResponse:
        return StoredMessageResponse(
            id=UUID(message.id),
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            citations=[
                StoredCitationResponse(
                    id=UUID(citation.id), citation_id=citation.citation_id, order=citation.citation_order,
                    document_id=UUID(citation.document_id), file_name=citation.file_name, source_path=citation.source_path,
                    source_locator=citation.source_locator, excerpt=citation.excerpt, excerpt_hash=citation.excerpt_hash,
                    confidence=citation.confidence, evidence_type=citation.evidence_type,
                )
                for citation in sorted(message.citations, key=lambda item: item.citation_order)
            ],
        )
