"""D180 controlled explicit /action live Chat routing projection."""

from __future__ import annotations

from uuid import UUID

from app.contracts.command import CommandRequest
from app.contracts.execution_approval import ExecutionApprovalProposalOutcome
from app.contracts.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffOutcome,
)
from app.contracts.explicit_action_live_chat_routing import (
    ExplicitActionLiveChatProjectionOutcome,
)
from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.contracts.governed_action import GovernedActionPreparation
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffIntegration,
)


_ROUTE_MODES = frozenset({"legacy", "cognitive"})
_STATUS_MAP = {
    "cognitive_outcome_unavailable": "unavailable",
    "not_applicable": "rejected",
    "invalid": "rejected",
    "lineage_unavailable": "unavailable",
    "needs_clarification": "rejected",
    "unsupported": "rejected",
    "intent_rejected": "rejected",
    "prepared_for_owner_review": "pending_approval",
    "approval_unavailable": "unavailable",
}


class ExplicitActionLiveChatRoutingService:
    """Route metadata plus D179 projection; owns no AI or execution authority."""

    def __init__(
        self,
        *,
        route_mode: str,
        handoff: ExplicitActionCognitiveHandoffIntegration,
    ) -> None:
        if route_mode not in _ROUTE_MODES:
            raise ValueError("explicit_action_live_chat_route_mode_invalid")
        if not isinstance(handoff, ExplicitActionCognitiveHandoffIntegration):
            raise TypeError(
                "handoff must be an ExplicitActionCognitiveHandoffIntegration."
            )
        self._route_mode = route_mode
        self._handoff = handoff

    @property
    def route_mode(self) -> str:
        return self._route_mode

    def project_cognitive(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        command: CommandRequest,
        orchestration_outcome: CommandOrchestrationOutcome,
    ) -> ExplicitActionLiveChatProjectionOutcome:
        if self._route_mode != "cognitive":
            raise RuntimeError(
                "explicit_action_live_chat_cognitive_route_not_selected"
            )
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(
            orchestration_outcome,
            CommandOrchestrationOutcome,
        ):
            raise TypeError(
                "orchestration_outcome must be a CommandOrchestrationOutcome."
            )

        handoff = self._handoff.process(
            message,
            project_id=project_id,
            command=command,
            orchestration_outcome=orchestration_outcome,
        )
        if not isinstance(handoff, ExplicitActionCognitiveHandoffOutcome):
            raise RuntimeError(
                "explicit_action_live_chat_handoff_invalid"
            )
        projected = _STATUS_MAP.get(handoff.status)
        if projected is None:
            raise RuntimeError(
                "explicit_action_live_chat_handoff_status_invalid"
            )

        approval = (
            self._owner_review_approval(handoff)
            if handoff.status == "prepared_for_owner_review"
            else None
        )
        return ExplicitActionLiveChatProjectionOutcome(
            status=projected,
            reason_code=handoff.reason_code,
            approval=approval,
            handoff=handoff,
        )

    @staticmethod
    def _owner_review_approval(
        handoff: ExplicitActionCognitiveHandoffOutcome,
    ) -> ExecutionApprovalProposalOutcome:
        d177 = handoff.runtime
        if (
            not isinstance(d177, ExplicitActionSemanticRuntimeOutcome)
            or d177.status != "prepared_for_owner_review"
            or d177.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_d177_invalid"
            )

        d175 = d177.runtime
        if (
            not isinstance(d175, StructuredActionSemanticRuntimeOutcome)
            or d175.status != "prepared_for_owner_review"
            or d175.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_d175_invalid"
            )

        d173 = d175.runtime
        if (
            not isinstance(d173, StructuredActionCandidateRuntimeOutcome)
            or d173.status != "prepared_for_owner_review"
            or d173.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_d173_invalid"
            )

        d170 = d173.runtime
        if (
            not isinstance(d170, StructuredActionProposalRuntimeOutcome)
            or d170.status != "prepared_for_owner_review"
            or d170.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_d170_invalid"
            )

        d167 = d170.runtime
        if (
            not isinstance(d167, GovernedActionRuntimeOutcome)
            or d167.status != "prepared_for_owner_review"
            or d167.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_d167_invalid"
            )

        preparation = d167.preparation
        if (
            not isinstance(preparation, GovernedActionPreparation)
            or preparation.status != "pending_approval"
            or preparation.reason_code != handoff.reason_code
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_preparation_invalid"
            )

        approval = preparation.approval
        if (
            not isinstance(approval, ExecutionApprovalProposalOutcome)
            or approval.status != "pending"
            or approval.proposal is None
        ):
            raise RuntimeError(
                "explicit_action_live_chat_owner_review_approval_invalid"
            )
        return approval


__all__ = ["ExplicitActionLiveChatRoutingService"]
