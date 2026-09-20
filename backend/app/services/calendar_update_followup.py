"""D101 exact update proposal orchestration over D101 follow-up and D73 approval."""

from __future__ import annotations

from uuid import UUID

from app.contracts.google_calendar_write import (
    GoogleCalendarEventPatch,
    GoogleCalendarUpdateEventRequest,
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


class CalendarUpdateFollowupProposalError(RuntimeError):
    """Base D101 exact update proposal orchestration error."""


class CalendarUpdateFollowupProposalBindingError(
    CalendarUpdateFollowupProposalError
):
    """Server-bound follow-up consumption failed after proposal creation."""


class CalendarUpdateFollowupProposalService:
    """Create an exact D73 update proposal from one server-bound follow-up."""

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

    def propose_exact_update(
        self,
        *,
        followup_id: str,
        changes: GoogleCalendarEventPatch,
        workspace_id: WorkspaceId,
        conversation_id: UUID,
    ):
        if not isinstance(changes, GoogleCalendarEventPatch):
            raise ValueError("calendar_update_patch_invalid")

        binding = self._followup_store.resolve(
            followup_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        request = GoogleCalendarUpdateEventRequest(
            target=binding.target,
            changes=changes,
        )
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
            raise CalendarUpdateFollowupProposalBindingError(
                "Calendar update follow-up consumption failed closed."
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
    "CalendarUpdateFollowupProposalBindingError",
    "CalendarUpdateFollowupProposalError",
    "CalendarUpdateFollowupProposalService",
]
