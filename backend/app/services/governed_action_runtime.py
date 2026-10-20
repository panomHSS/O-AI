"""D167 governed Brain -> Hands runtime lineage integration."""

from app.contracts.cognitive_brain import CognitiveOrganStatus, CognitiveTurnState
from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.governed_action import ActionIntent
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.workspace import WorkspaceScope
from app.services.governed_action import (
    GovernedActionBoundary,
    governed_action_intent_digest,
)


class GovernedActionRuntimeIntegration:
    """Validate current Brain lineage, then delegate only to D166 prepare."""

    def __init__(
        self,
        *,
        boundary: GovernedActionBoundary,
        workspace_scope: WorkspaceScope,
    ) -> None:
        if not isinstance(boundary, GovernedActionBoundary):
            raise TypeError("boundary must be a GovernedActionBoundary.")
        if not isinstance(workspace_scope, WorkspaceScope):
            raise TypeError("workspace_scope must be a WorkspaceScope.")
        self._boundary = boundary
        self._workspace_id = workspace_scope.workspace_id

    def prepare(
        self,
        intent: ActionIntent | None,
        *,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> GovernedActionRuntimeOutcome:
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise TypeError("cognitive_outcome must be a CognitiveExecutiveOutcome.")

        if intent is None:
            return GovernedActionRuntimeOutcome(
                status="no_action_intent",
                reason_code="no_action_intent",
            )
        if not isinstance(intent, ActionIntent):
            raise TypeError("intent must be an ActionIntent or None.")

        digest = governed_action_intent_digest(intent)

        if command.command != "chat.message":
            return self._reject(digest, "source_command_not_cognitive_chat")
        if intent.source_turn_id != command.request_id:
            return self._reject(digest, "source_turn_request_mismatch")
        if cognitive_outcome.envelope.turn_id != command.request_id:
            return self._reject(digest, "cognitive_turn_request_mismatch")
        if cognitive_outcome.envelope.workspace_id != self._workspace_id:
            return self._reject(digest, "cognitive_workspace_mismatch")
        if (
            cognitive_outcome.terminal_state is not CognitiveTurnState.COMPLETED
            or cognitive_outcome.publication_disposition != "eligible"
        ):
            return self._reject(digest, "cognitive_outcome_not_action_eligible")

        events = tuple(
            event for event in cognitive_outcome.trace
            if event.stage == "publication_accepted"
        )
        if len(events) != 1:
            return self._reject(digest, "source_artifact_unavailable")
        event = events[0]
        if (
            event.state is not CognitiveTurnState.FINALIZING
            or event.status is not CognitiveOrganStatus.READY
            or event.artifact_digest is None
        ):
            return self._reject(digest, "source_artifact_unavailable")
        if intent.source_artifact_digest != event.artifact_digest:
            return self._reject(digest, "source_artifact_mismatch")

        prepared = self._boundary.prepare(intent)
        if prepared.status == "pending_approval":
            status = "prepared_for_owner_review"
        elif prepared.status == "unavailable":
            status = "approval_unavailable"
        else:
            status = "intent_rejected"
        return GovernedActionRuntimeOutcome(
            status=status,
            reason_code=prepared.reason_code,
            intent_digest=digest,
            preparation=prepared,
        )

    @staticmethod
    def _reject(
        digest: str,
        reason: str,
    ) -> GovernedActionRuntimeOutcome:
        return GovernedActionRuntimeOutcome(
            status="intent_rejected",
            reason_code=reason,
            intent_digest=digest,
        )
