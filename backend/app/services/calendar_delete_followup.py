"""D101 exact delete proposal orchestration over D101 follow-up and D73 approval."""

from __future__ import annotations

from uuid import UUID

from app.contracts.google_calendar_write import (
    GoogleCalendarDeleteEventRequest,
)
from app.contracts.workspace import WorkspaceId
from app.services.calendar_write_approval import (
    CalendarWriteApprovalError,
    CalendarWriteApprovalService,
)
from app.services.calendar_write_followup import (
    CalendarWriteFollowupError,
    CalendarWriteFollowupStore,
)


class CalendarDeleteFollowupProposalError(RuntimeError):
    """Base D101 exact delete proposal orchestration error."""


class CalendarDeleteFollowupProposalBindingError(
    CalendarDeleteFollowupProposalError
):
    """Server-bound follow-up consumption failed after proposal creation."""


class CalendarDeleteFollowupProposalService:
    """Create an exact D73 delete proposal from one server-bound follow-up."""

    def __init__(
        self,
        *,
        approval_service: CalendarWriteApprovalService,
        followup_store: CalendarWriteFollowupStore,
    ) -> None:
        if not isinstance(approval_service, CalendarWriteApprovalService):
            raise TypeError(
                "approval_service must be CalendarWriteApprovalService."
            )
        if not isinstance(followup_store, CalendarWriteFollowupStore):
            raise TypeError(
                "followup_store must be CalendarWriteFollowupStore."
            )
        self._approval_service = approval_service
        self._followup_store = followup_store

    def propose_exact_delete(
        self,
        *,
        followup_id: str,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ):
        binding = self._followup_store.resolve(
            followup_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        request = GoogleCalendarDeleteEventRequest(target=binding.target)
        proposal_outcome = self._approval_service.propose(request)
        proposal = proposal_outcome.proposal
        try:
            self._followup_store.consume(
                followup_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
            )
        except CalendarWriteFollowupError:
            self._neutralize_orphan(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise
        except Exception as error:
            self._neutralize_orphan(
                proposal.approval_id,
                proposal.write_digest,
            )
            raise CalendarDeleteFollowupProposalBindingError(
                "Calendar delete follow-up consumption failed closed."
            ) from error
        return proposal_outcome

    def _neutralize_orphan(
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
    "CalendarDeleteFollowupProposalBindingError",
    "CalendarDeleteFollowupProposalError",
    "CalendarDeleteFollowupProposalService",
]
