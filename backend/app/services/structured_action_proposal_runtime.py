"""D170 production-composable D168 -> D169 -> D167 runtime seam."""

from __future__ import annotations

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentProposal,
)
from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)
from app.services.governed_action_runtime import GovernedActionRuntimeIntegration


_D167_TERMINAL_STATUSES = frozenset(
    {
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


class StructuredActionProposalRuntimeIntegration:
    """Compose D169 conversion with D167 lineage/governance preparation."""

    def __init__(
        self,
        *,
        conversion_service: GovernedActionIntentConversionService,
        runtime_integration: GovernedActionRuntimeIntegration,
    ) -> None:
        if not isinstance(
            conversion_service,
            GovernedActionIntentConversionService,
        ):
            raise TypeError(
                "conversion_service must be a "
                "GovernedActionIntentConversionService."
            )
        if not isinstance(
            runtime_integration,
            GovernedActionRuntimeIntegration,
        ):
            raise TypeError(
                "runtime_integration must be a "
                "GovernedActionRuntimeIntegration."
            )
        self._conversion_service = conversion_service
        self._runtime_integration = runtime_integration

    def process(
        self,
        proposal: StructuredActionIntentProposal | None,
        *,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> StructuredActionProposalRuntimeOutcome:
        if proposal is not None and not isinstance(
            proposal,
            StructuredActionIntentProposal,
        ):
            raise TypeError(
                "proposal must be a StructuredActionIntentProposal or None."
            )
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise TypeError(
                "cognitive_outcome must be a CognitiveExecutiveOutcome."
            )

        if proposal is None:
            return StructuredActionProposalRuntimeOutcome(
                status="no_action_proposal",
                reason_code="no_structured_action_proposal",
            )

        conversion = self._conversion_service.convert(proposal)
        if conversion.status == "not_convertible":
            return StructuredActionProposalRuntimeOutcome(
                status="proposal_not_convertible",
                reason_code=conversion.reason_code,
                conversion=conversion,
            )

        intent = conversion.action_intent
        if intent is None:
            raise RuntimeError(
                "structured_action_runtime_converted_intent_missing"
            )

        runtime = self._runtime_integration.prepare(
            intent,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )

        if runtime.status == "no_action_intent":
            raise RuntimeError(
                "structured_action_runtime_unexpected_no_action_intent"
            )
        if runtime.status not in _D167_TERMINAL_STATUSES:
            raise RuntimeError(
                "structured_action_runtime_downstream_status_invalid"
            )

        return StructuredActionProposalRuntimeOutcome(
            status=runtime.status,
            reason_code=runtime.reason_code,
            conversion=conversion,
            runtime=runtime,
        )


__all__ = ["StructuredActionProposalRuntimeIntegration"]