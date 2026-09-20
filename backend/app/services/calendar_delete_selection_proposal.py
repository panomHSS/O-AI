"""D101 selection-to-exact-delete proposal handoff."""

from __future__ import annotations

from uuid import UUID

from app.contracts.workspace import WorkspaceId
from app.services.calendar_delete_decision import (
    CalendarDeleteDecisionBindingService,
    CalendarDeleteDecisionError,
)
from app.services.calendar_delete_followup import (
    CalendarDeleteFollowupProposalService,
)
from app.services.calendar_read_selection import (
    CalendarReadSelectionError,
    CalendarReadSelectionStore,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalError,
    CalendarWriteApprovalService,
)
from app.services.calendar_write_followup import (
    CalendarWriteFollowupError,
    CalendarWriteFollowupService,
    CalendarWriteFollowupStore,
)


class CalendarDeleteSelectionProposalError(RuntimeError):
    """Base D101 exact-delete selection handoff error."""


class CalendarDeleteSelectionProposalService:
    """Turn one opaque read selection into one exact D73 Delete proposal."""

    def __init__(
        self,
        *,
        selection_store: CalendarReadSelectionStore,
        write_followup_service: CalendarWriteFollowupService,
        write_followup_store: CalendarWriteFollowupStore,
        delete_proposal_service: CalendarDeleteFollowupProposalService,
        approval_service: CalendarWriteApprovalService,
        decision_binding_service: CalendarDeleteDecisionBindingService,
    ) -> None:
        if not isinstance(selection_store, CalendarReadSelectionStore):
            raise TypeError("selection_store must be CalendarReadSelectionStore.")
        if not isinstance(write_followup_service, CalendarWriteFollowupService):
            raise TypeError(
                "write_followup_service must be CalendarWriteFollowupService."
            )
        if not isinstance(write_followup_store, CalendarWriteFollowupStore):
            raise TypeError(
                "write_followup_store must be CalendarWriteFollowupStore."
            )
        if not isinstance(
            delete_proposal_service,
            CalendarDeleteFollowupProposalService,
        ):
            raise TypeError(
                "delete_proposal_service must be "
                "CalendarDeleteFollowupProposalService."
            )
        if not isinstance(approval_service, CalendarWriteApprovalService):
            raise TypeError(
                "approval_service must be CalendarWriteApprovalService."
            )

        if not isinstance(
            decision_binding_service,
            CalendarDeleteDecisionBindingService,
        ):
            raise TypeError(
                "decision_binding_service must be "
                "CalendarDeleteDecisionBindingService."
            )

        self._selection_store = selection_store
        self._write_followup_service = write_followup_service
        self._write_followup_store = write_followup_store
        self._delete_proposal_service = delete_proposal_service
        self._approval_service = approval_service
        self._decision_binding_service = decision_binding_service

    def propose_from_selection(
        self,
        *,
        selection_id: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ):
        selection = self._selection_store.resolve(
            selection_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )

        followup = self._write_followup_service.bind_exact_target(
            target=selection.target,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )

        try:
            outcome = self._delete_proposal_service.propose_exact_delete(
                followup_id=followup.followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
        except Exception:
            self._neutralize_followup(
                followup.followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
            raise

        proposal = outcome.proposal
        try:
            consumed = self._selection_store.consume(
                selection_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
        except CalendarReadSelectionError:
            self._neutralize_proposal(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise
        except Exception as error:
            self._neutralize_proposal(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise CalendarDeleteSelectionProposalError(
                "Calendar Delete selection handoff failed closed."
            ) from error

        if consumed != selection:
            self._neutralize_proposal(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise CalendarDeleteSelectionProposalError(
                "Calendar Delete selection handoff integrity failed."
            )

        try:
            self._decision_binding_service.bind_proposal(
                approval_id=proposal.approval_id,
                write_digest=proposal.write_digest,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                expires_at=proposal.expires_at,
            )
        except CalendarDeleteDecisionError:
            self._neutralize_proposal(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise

        return outcome

    def _neutralize_followup(
        self,
        followup_id: str,
        *,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ) -> None:
        try:
            self._write_followup_store.consume(
                followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
        except CalendarWriteFollowupError:
            return

    def _neutralize_proposal(
        self,
        approval_id: str,
        write_digest: str,
    ) -> None:
        try:
            self._approval_service.deny(
                approval_id,
                write_digest,
            )
        except CalendarWriteApprovalError:
            return


__all__ = [
    "CalendarDeleteSelectionProposalError",
    "CalendarDeleteSelectionProposalService",
]
