from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversations import ConversationRepository
from app.schemas.conversations import ConversationDetailResponse, ConversationSummaryResponse, StoredMessageResponse
from app.services.chat import ChatContextMessage, ChatService

TITLE_MAX_LENGTH = 80


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist."""


@dataclass(frozen=True)
class ChatTurnResult:
    reply: str
    conversation_id: UUID


class ConversationService:
    """Coordinates local conversation persistence with provider-neutral chat."""

    def __init__(self, repository: ConversationRepository, chat_service: ChatService, context_message_limit: int) -> None:
        self._repository = repository
        self._chat_service = chat_service
        self._context_message_limit = context_message_limit

    def send_message(self, message: str, conversation_id: UUID | None = None) -> ChatTurnResult:
        conversation, recent_messages = self.begin_turn(message, conversation_id)

        context = [ChatContextMessage(role=item.role, content=item.content) for item in recent_messages]
        reply = self._chat_service.send_message(message, context)

        self.complete_turn(conversation.id, reply)

        return ChatTurnResult(reply=reply, conversation_id=UUID(conversation.id))

    def begin_turn(self, message: str, conversation_id: UUID | None = None) -> tuple[Conversation, list[ChatContextMessage]]:
        """Persist a final user turn and return bounded history for another orchestrator."""
        conversation = self._get_or_create_conversation(message, conversation_id)
        recent = self._repository.recent_messages(conversation.id, self._context_message_limit)
        try:
            self._repository.add_message(conversation, "user", message)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise
        return conversation, [ChatContextMessage(role=item.role, content=item.content) for item in recent]

    def complete_turn(self, conversation_id: str, reply: str) -> None:
        conversation = self._require_conversation(UUID(conversation_id))
        try:
            self._repository.add_message(conversation, "assistant", reply)
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

    def _get_or_create_conversation(self, message: str, conversation_id: UUID | None) -> Conversation:
        if conversation_id is not None:
            return self._require_conversation(conversation_id)

        try:
            conversation = self._repository.create(self._create_title(message))
            self._repository.commit()
            return conversation
        except Exception:
            self._repository.rollback()
            raise

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
        )

    @staticmethod
    def _to_message(message: Message) -> StoredMessageResponse:
        return StoredMessageResponse(
            id=UUID(message.id),
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
