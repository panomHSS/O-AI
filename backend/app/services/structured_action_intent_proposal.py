"""D168 deterministic structured action intent proposal projection."""

from __future__ import annotations

from app.contracts.structured_action_intent_proposal import (
    StructuredActionGovernanceRequirements,
    StructuredActionIntentCandidate,
    StructuredActionIntentProposal,
)


_SUPPORTED_TARGET_KINDS = frozenset({"tool", "module"})


class StructuredActionIntentProposalService:
    """Project structured candidates into proposals without creating authority."""

    def propose(
        self,
        candidate: StructuredActionIntentCandidate | None,
    ) -> StructuredActionIntentProposal:
        if candidate is None:
            return StructuredActionIntentProposal(
                status="not_applicable",
                reason_code="no_structured_action_candidate",
            )
        if not isinstance(candidate, StructuredActionIntentCandidate):
            raise TypeError(
                "candidate must be a StructuredActionIntentCandidate or None."
            )

        governance = StructuredActionGovernanceRequirements()

        if (
            candidate.target_kind is not None
            and candidate.target_kind not in _SUPPORTED_TARGET_KINDS
        ):
            return StructuredActionIntentProposal(
                status="unsupported",
                reason_code="unsupported_target_kind",
                source_turn_id=candidate.source_turn_id,
                source_artifact_digest=candidate.source_artifact_digest,
                governance_requirements=governance,
            )

        missing = set(candidate.missing_information)
        if candidate.target_kind is None:
            missing.add("target_kind")
        if candidate.adapter_id is None:
            missing.add("adapter_id")
        if candidate.operation is None:
            missing.add("operation")

        if missing:
            return StructuredActionIntentProposal(
                status="needs_clarification",
                reason_code="structured_action_information_missing",
                source_turn_id=candidate.source_turn_id,
                source_artifact_digest=candidate.source_artifact_digest,
                target_kind=candidate.target_kind,  # type: ignore[arg-type]
                adapter_id=candidate.adapter_id,
                operation=candidate.operation,
                parameters=candidate.parameters,
                missing_information=tuple(sorted(missing)),
                governance_requirements=governance,
            )

        return StructuredActionIntentProposal(
            status="proposal_ready",
            reason_code="structured_action_proposal_ready",
            source_turn_id=candidate.source_turn_id,
            source_artifact_digest=candidate.source_artifact_digest,
            target_kind=candidate.target_kind,  # type: ignore[arg-type]
            adapter_id=candidate.adapter_id,
            operation=candidate.operation,
            parameters=candidate.parameters,
            governance_requirements=governance,
        )


__all__ = ["StructuredActionIntentProposalService"]