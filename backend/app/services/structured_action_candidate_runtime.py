"""D173 production-composable D172 -> D168 -> D170 orchestration seam."""

from __future__ import annotations

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_intent_proposal import StructuredActionIntentProposal
from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)
from app.services.structured_action_candidate_producer import StructuredActionCandidateProducer
from app.services.structured_action_intent_proposal import StructuredActionIntentProposalService
from app.services.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeIntegration,
)

_DOWNSTREAM = frozenset({
    "intent_rejected", "prepared_for_owner_review", "approval_unavailable",
})


class StructuredActionCandidateRuntimeIntegration:
    """Compose D172, D168, and D170 without adding authority."""

    def __init__(
        self,
        *,
        candidate_producer: StructuredActionCandidateProducer,
        proposal_service: StructuredActionIntentProposalService,
        proposal_runtime: StructuredActionProposalRuntimeIntegration,
    ) -> None:
        if not isinstance(candidate_producer, StructuredActionCandidateProducer):
            raise TypeError("candidate_producer must be a StructuredActionCandidateProducer.")
        if not isinstance(proposal_service, StructuredActionIntentProposalService):
            raise TypeError("proposal_service must be a StructuredActionIntentProposalService.")
        if not isinstance(proposal_runtime, StructuredActionProposalRuntimeIntegration):
            raise TypeError("proposal_runtime must be a StructuredActionProposalRuntimeIntegration.")
        self._candidate_producer = candidate_producer
        self._proposal_service = proposal_service
        self._proposal_runtime = proposal_runtime

    def process(
        self,
        semantic: StructuredActionSemanticInput | None,
        *,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> StructuredActionCandidateRuntimeOutcome:
        if semantic is not None and not isinstance(semantic, StructuredActionSemanticInput):
            raise TypeError("semantic must be a StructuredActionSemanticInput or None.")
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise TypeError("cognitive_outcome must be a CognitiveExecutiveOutcome.")

        production = self._candidate_producer.produce(semantic)
        if not isinstance(production, StructuredActionCandidateProductionOutcome):
            raise RuntimeError("structured_action_candidate_runtime_production_invalid")

        if production.status == "not_applicable":
            return StructuredActionCandidateRuntimeOutcome(
                status="no_action_semantics",
                reason_code=production.reason_code,
                production=production,
            )
        if production.status == "unsupported":
            return StructuredActionCandidateRuntimeOutcome(
                status="unsupported",
                reason_code=production.reason_code,
                production=production,
            )

        candidate = production.candidate
        if candidate is None:
            raise RuntimeError("structured_action_candidate_runtime_candidate_missing")
        proposal = self._proposal_service.propose(candidate)
        if not isinstance(proposal, StructuredActionIntentProposal):
            raise RuntimeError("structured_action_candidate_runtime_proposal_invalid")

        if production.status == "needs_clarification":
            if (
                proposal.status != "needs_clarification"
                or proposal.reason_code != "structured_action_information_missing"
            ):
                raise RuntimeError("structured_action_candidate_runtime_clarification_mismatch")
            return StructuredActionCandidateRuntimeOutcome(
                status="needs_clarification",
                reason_code=proposal.reason_code,
                production=production,
                proposal=proposal,
            )

        if production.status != "candidate_ready":
            raise RuntimeError("structured_action_candidate_runtime_production_status_invalid")
        if (
            proposal.status != "proposal_ready"
            or proposal.reason_code != "structured_action_proposal_ready"
        ):
            raise RuntimeError("structured_action_candidate_runtime_proposal_not_ready")

        runtime = self._proposal_runtime.process(
            proposal,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )
        if not isinstance(runtime, StructuredActionProposalRuntimeOutcome):
            raise RuntimeError("structured_action_candidate_runtime_downstream_invalid")
        if runtime.status in {"no_action_proposal", "proposal_not_convertible"}:
            raise RuntimeError("structured_action_candidate_runtime_downstream_invariant")
        if runtime.status not in _DOWNSTREAM:
            raise RuntimeError("structured_action_candidate_runtime_downstream_status_invalid")
        return StructuredActionCandidateRuntimeOutcome(
            status=runtime.status,
            reason_code=runtime.reason_code,
            production=production,
            proposal=proposal,
            runtime=runtime,
        )


__all__ = ["StructuredActionCandidateRuntimeIntegration"]
