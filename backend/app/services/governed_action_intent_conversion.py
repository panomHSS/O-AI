"""D169 deterministic D168 proposal -> D166 ActionIntent conversion."""

from __future__ import annotations

from app.contracts.governed_action import ActionIntent
from app.contracts.governed_action_intent_conversion import (
    GovernedActionIntentConversionOutcome,
)
from app.contracts.structured_action_intent_proposal import (
    D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION,
    StructuredActionGovernanceRequirements,
    StructuredActionIntentProposal,
)


_NOT_CONVERTIBLE_REASONS = {
    "not_applicable": "proposal_not_applicable",
    "needs_clarification": "proposal_needs_clarification",
    "unsupported": "proposal_unsupported",
}


def _strict_governance_requirements(
    proposal: StructuredActionIntentProposal,
) -> bool:
    governance = proposal.governance_requirements
    return (
        isinstance(governance, StructuredActionGovernanceRequirements)
        and governance.owner_approval_required is True
        and governance.execution_authority_required is True
        and governance.capability_validation_required is True
    )


class GovernedActionIntentConversionService:
    """Convert complete D168 proposals to non-authoritative D166 intents."""

    def convert(
        self,
        proposal: StructuredActionIntentProposal,
    ) -> GovernedActionIntentConversionOutcome:
        if not isinstance(proposal, StructuredActionIntentProposal):
            raise TypeError(
                "proposal must be a StructuredActionIntentProposal."
            )

        if (
            proposal.contract_version
            != D168_STRUCTURED_ACTION_INTENT_PROPOSAL_CONTRACT_VERSION
        ):
            raise ValueError(
                "governed_action_intent_conversion_proposal_contract_invalid"
            )

        if proposal.status == "not_applicable":
            return GovernedActionIntentConversionOutcome(
                status="not_convertible",
                reason_code="proposal_not_applicable",
            )

        if not _strict_governance_requirements(proposal):
            raise ValueError(
                "governed_action_intent_conversion_governance_invalid"
            )

        reason = _NOT_CONVERTIBLE_REASONS.get(proposal.status)
        if reason is not None:
            return GovernedActionIntentConversionOutcome(
                status="not_convertible",
                reason_code=reason,
            )

        if proposal.status != "proposal_ready":
            raise ValueError(
                "governed_action_intent_conversion_proposal_status_invalid"
            )

        if (
            proposal.reason_code != "structured_action_proposal_ready"
            or proposal.source_turn_id is None
            or proposal.source_artifact_digest is None
            or proposal.target_kind is None
            or proposal.adapter_id is None
            or proposal.operation is None
            or proposal.missing_information
        ):
            raise ValueError(
                "governed_action_intent_conversion_proposal_invalid"
            )

        intent = ActionIntent(
            source_turn_id=proposal.source_turn_id,
            source_artifact_digest=proposal.source_artifact_digest,
            target_kind=proposal.target_kind,
            adapter_id=proposal.adapter_id,
            operation=proposal.operation,
            parameters=proposal.parameters,
        )

        return GovernedActionIntentConversionOutcome(
            status="converted_for_lineage_validation",
            reason_code="proposal_converted_for_lineage_validation",
            action_intent=intent,
        )


__all__ = ["GovernedActionIntentConversionService"]