from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project


class ConversationRepository:
    """Workspace-scoped database operations for Conversation roots."""

    def __init__(
        self,
        session: Session,
        workspace_scope: WorkspaceScope,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def create(
        self,
        title: str,
        project_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            title=title,
            project_id=project_id,
            workspace_id=self._workspace_id,
        )
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        statement: Select[tuple[Conversation]] = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == self._workspace_id,
            )
            .options(
                selectinload(Conversation.messages).selectinload(
                    Message.citations
                )
            )
            .execution_options(populate_existing=True)
        )
        return self._session.scalar(statement)

    def list(self) -> Sequence[Conversation]:
        statement: Select[tuple[Conversation]] = (
            select(Conversation)
            .where(Conversation.workspace_id == self._workspace_id)
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.id.desc(),
            )
        )
        return self._session.scalars(statement).all()

    def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
    ) -> Message:
        self._require_owned(conversation)
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
        )
        conversation.updated_at = utc_now()
        self._session.add(message)
        self._session.flush()
        return message

    def recent_messages(
        self,
        conversation_id: str,
        limit: int,
    ) -> Sequence[Message]:
        latest_message_ids = (
            select(Message.id)
            .join(
                Conversation,
                Conversation.id == Message.conversation_id,
            )
            .where(
                Message.conversation_id == conversation_id,
                Conversation.workspace_id == self._workspace_id,
            )
            .order_by(
                Message.created_at.desc(),
                Message.id.desc(),
            )
            .limit(limit)
            .subquery()
        )
        statement: Select[tuple[Message]] = (
            select(Message)
            .where(Message.id.in_(select(latest_message_ids.c.id)))
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
        )
        return self._session.scalars(statement).all()

    def delete(self, conversation: Conversation) -> None:
        self._require_owned(conversation)
        self._session.delete(conversation)

    def project_exists(self, project_id: str) -> bool:
        return (
            self._session.scalar(
                select(Project.id)
                .where(
                    Project.id == project_id,
                    Project.workspace_id == self._workspace_id,
                )
                .limit(1)
            )
            is not None
        )

    def _require_owned(self, conversation: Conversation) -> None:
        if conversation.workspace_id != self._workspace_id:
            raise ValueError("workspace_mismatch")

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
