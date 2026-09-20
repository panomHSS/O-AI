"""D101 exact Calendar Update owner decision orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.contracts.workspace import WorkspaceId
from app.services.calendar_update_decision import CalendarUpdateDecisionStore
from app.services.calendar_update_delete_execution import (
    CalendarUpdateDeleteExecutionService,
)
from app.services.calendar_write_approval import CalendarWriteApprovalService
from app.services.conversations import ConversationService


UpdateOwnerDecision = Literal["approved", "denied"]
UpdateOwnerTerminalStatus = Literal[
    "denied",
    "succeeded",
    "failed",
    "indeterminate",
]


@dataclass(frozen=True, slots=True)
class CalendarUpdateOwnerDecisionOutcome:
    approval_id: str
    decision: UpdateOwnerDecision
    status: UpdateOwnerTerminalStatus
    reason_code: str


class CalendarUpdateOwnerDecisionError(RuntimeError):
    """Base D101 owner Update decision orchestration error."""


class CalendarUpdateOwnerDecisionService:
    """Enforce workspace/conversation correlation before D73/D75 mutation."""

    def __init__(
        self,
        *,
        decision_store: CalendarUpdateDecisionStore,
        approval_service: CalendarWriteApprovalService,
        execution_service: CalendarUpdateDeleteExecutionService,
        conversation_service: ConversationService,
    ) -> None:
        self._decision_store = decision_store
        self._approval_service = approval_service
        self._execution_service = execution_service
        self._conversation_service = conversation_service

    def deny(
        self,
        *,
        approval_id: str,
        write_digest: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarUpdateOwnerDecisionOutcome:
        self._require_owner_scope(
            approval_id=approval_id,
            write_digest=write_digest,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        self._decision_store.consume(
            approval_id,
            write_digest,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        self._approval_service.deny(approval_id, write_digest)

        return CalendarUpdateOwnerDecisionOutcome(
            approval_id=approval_id,
            decision="denied",
            status="denied",
            reason_code="owner_denied",
        )

    def approve(
        self,
        *,
        approval_id: str,
        write_digest: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> CalendarUpdateOwnerDecisionOutcome:
        self._require_owner_scope(
            approval_id=approval_id,
            write_digest=write_digest,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        self._decision_store.consume(
            approval_id,
            write_digest,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        self._approval_service.approve(approval_id, write_digest)

        try:
            execution = self._execution_service.execute_update(
                approval_id,
                write_digest,
            )
        except Exception as error:
            raise CalendarUpdateOwnerDecisionError(
                "calendar_update_execution_rejected"
            ) from error

        status = getattr(execution, "status", None)
        reason_code = getattr(execution, "reason_code", None)
        if status not in {"succeeded", "failed", "indeterminate"}:
            raise CalendarUpdateOwnerDecisionError(
                "calendar_update_execution_status_invalid"
            )
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or reason_code != reason_code.strip()
        ):
            raise CalendarUpdateOwnerDecisionError(
                "calendar_update_execution_reason_invalid"
            )

        return CalendarUpdateOwnerDecisionOutcome(
            approval_id=approval_id,
            decision="approved",
            status=status,
            reason_code=reason_code,
        )

    def _require_owner_scope(
        self,
        *,
        approval_id: str,
        write_digest: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> None:
        self._decision_store.resolve(
            approval_id,
            write_digest,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        self._conversation_service.get_conversation(str(conversation_id))


__all__ = [
    "CalendarUpdateOwnerDecisionError",
    "CalendarUpdateOwnerDecisionOutcome",
    "CalendarUpdateOwnerDecisionService",
]
