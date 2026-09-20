"""D101 exact Calendar Delete owner decision orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.contracts.workspace import WorkspaceId
from app.services.calendar_delete_decision import CalendarDeleteDecisionStore
from app.services.calendar_update_delete_execution import (
    CalendarUpdateDeleteExecutionService,
)
from app.services.calendar_write_approval import CalendarWriteApprovalService
from app.services.conversations import ConversationService


DeleteOwnerDecision = Literal["approved", "denied"]
DeleteOwnerTerminalStatus = Literal[
    "denied",
    "succeeded",
    "failed",
    "indeterminate",
]


@dataclass(frozen=True, slots=True)
class CalendarDeleteOwnerDecisionOutcome:
    approval_id: str
    decision: DeleteOwnerDecision
    status: DeleteOwnerTerminalStatus
    reason_code: str


class CalendarDeleteOwnerDecisionError(RuntimeError):
    """Base D101 owner Delete decision orchestration error."""


class CalendarDeleteOwnerDecisionService:
    """Enforce workspace/conversation correlation before D73/D75 mutation."""

    def __init__(
        self,
        *,
        decision_store: CalendarDeleteDecisionStore,
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
    ) -> CalendarDeleteOwnerDecisionOutcome:
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

        return CalendarDeleteOwnerDecisionOutcome(
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
    ) -> CalendarDeleteOwnerDecisionOutcome:
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
            execution = self._execution_service.execute_delete(
                approval_id,
                write_digest,
            )
        except Exception as error:
            raise CalendarDeleteOwnerDecisionError(
                "calendar_delete_execution_rejected"
            ) from error

        status = getattr(execution, "status", None)
        reason_code = getattr(execution, "reason_code", None)
        if status not in {"succeeded", "failed", "indeterminate"}:
            raise CalendarDeleteOwnerDecisionError(
                "calendar_delete_execution_status_invalid"
            )
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or reason_code != reason_code.strip()
        ):
            raise CalendarDeleteOwnerDecisionError(
                "calendar_delete_execution_reason_invalid"
            )

        return CalendarDeleteOwnerDecisionOutcome(
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
    "CalendarDeleteOwnerDecisionError",
    "CalendarDeleteOwnerDecisionOutcome",
    "CalendarDeleteOwnerDecisionService",
]
