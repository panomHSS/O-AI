"""D113 owner-bound Engineering Investigation workflow.

This layer binds one D113 investigation to the exact server-selected workspace
and existing conversation. It grants no D107 proposal, approval, D108 apply,
provider/model/credential, Tool/Module, connector, shell/process, Git, network,
or Skill execution authority.
"""

from __future__ import annotations

from app.contracts.engineering_investigation import (
    EngineeringInvestigationRequest,
    EngineeringInvestigationResult,
)
from app.contracts.workspace import WorkspaceScope
from app.services.engineering_investigation import (
    EngineeringInvestigationError,
    EngineeringInvestigationService,
)


class EngineeringInvestigationConversationNotFoundError(
    EngineeringInvestigationError
):
    def __init__(self) -> None:
        super().__init__("engineering_investigation_conversation_not_found")


class EngineeringInvestigationWorkflowService:
    """Verify exact conversation/workspace binding before investigation."""

    def __init__(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_repository,
        investigation_service: EngineeringInvestigationService,
    ) -> None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_investigation_request_invalid")
        if not callable(getattr(conversation_repository, "get", None)):
            raise TypeError("conversation_repository must support get().")
        if not isinstance(
            investigation_service,
            EngineeringInvestigationService,
        ):
            raise TypeError(
                "investigation_service must be EngineeringInvestigationService."
            )

        self._workspace_scope = workspace_scope
        self._conversations = conversation_repository
        self._investigation_service = investigation_service

    @property
    def workspace_scope(self) -> WorkspaceScope:
        return self._workspace_scope

    def investigate(
        self,
        request: EngineeringInvestigationRequest,
    ) -> EngineeringInvestigationResult:
        if not isinstance(request, EngineeringInvestigationRequest):
            raise EngineeringInvestigationError(
                "engineering_investigation_request_invalid"
            )

        conversation = self._conversations.get(
            str(request.conversation_id)
        )
        if conversation is None:
            raise EngineeringInvestigationConversationNotFoundError()

        return self._investigation_service.investigate(
            workspace_scope=self._workspace_scope,
            request=request,
        )


__all__ = [
    "EngineeringInvestigationConversationNotFoundError",
    "EngineeringInvestigationWorkflowService",
]