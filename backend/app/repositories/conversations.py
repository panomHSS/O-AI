from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.db.base import utc_now
from app.models.conversation import Conversation
from app.models.message import Message


class ConversationRepository:
    """Database operations isolated from application services."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, title: str) -> Conversation:
        conversation = Conversation(title=title)
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        statement: Select[tuple[Conversation]] = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages).selectinload(Message.citations))
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(statement)

    def list(self) -> Sequence[Conversation]:
        statement: Select[tuple[Conversation]] = select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        return self._session.scalars(statement).all()

    def add_message(self, conversation: Conversation, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation.id, role=role, content=content)
        conversation.updated_at = utc_now()
        self._session.add(message)
        self._session.flush()
        return message

    def recent_messages(self, conversation_id: str, limit: int) -> Sequence[Message]:
        latest_message_ids = (
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .subquery()
        )
        statement: Select[tuple[Message]] = (
            select(Message)
            .where(Message.id.in_(select(latest_message_ids.c.id)))
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return self._session.scalars(statement).all()

    def delete(self, conversation: Conversation) -> None:
        self._session.delete(conversation)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
