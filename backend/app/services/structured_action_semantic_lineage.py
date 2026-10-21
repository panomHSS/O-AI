"""D174 bind already-structured action semantics to current publication lineage."""

from __future__ import annotations

from app.contracts.cognitive_brain import CognitiveOrganStatus, CognitiveTurnState
from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.structured_action_candidate_producer import (
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
    StructuredActionSemanticLineageOutcome,
)


class StructuredActionSemanticLineageBinder:
    """Bind current server-owned publication lineage without validating authority."""

    def bind(
        self,
        draft: StructuredActionSemanticDraft | None,
        *,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> StructuredActionSemanticLineageOutcome:
        if draft is not None and not isinstance(draft, StructuredActionSemanticDraft):
            raise TypeError(
                "draft must be a StructuredActionSemanticDraft or None."
            )
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise TypeError(
                "cognitive_outcome must be a CognitiveExecutiveOutcome."
            )

        if draft is None:
            return StructuredActionSemanticLineageOutcome(
                status="not_applicable",
                reason_code="no_structured_action_semantic_draft",
            )

        if (
            command.command != "chat.message"
            or cognitive_outcome.envelope.turn_id != command.request_id
            or cognitive_outcome.terminal_state is not CognitiveTurnState.COMPLETED
            or cognitive_outcome.publication_disposition != "eligible"
        ):
            return self._lineage_unavailable()

        events = tuple(
            event
            for event in cognitive_outcome.trace
            if event.stage == "publication_accepted"
        )
        if len(events) != 1:
            return self._lineage_unavailable()

        event = events[0]
        if (
            event.state is not CognitiveTurnState.FINALIZING
            or event.status is not CognitiveOrganStatus.READY
            or event.artifact_digest is None
        ):
            return self._lineage_unavailable()

        semantic = StructuredActionSemanticInput(
            source_turn_id=command.request_id,
            source_artifact_digest=event.artifact_digest,
            semantic_action=draft.semantic_action,
            parameters=draft.parameters,
            missing_information=draft.missing_information,
        )
        return StructuredActionSemanticLineageOutcome(
            status="semantic_ready",
            reason_code="structured_action_semantic_ready",
            semantic=semantic,
        )

    @staticmethod
    def _lineage_unavailable() -> StructuredActionSemanticLineageOutcome:
        return StructuredActionSemanticLineageOutcome(
            status="lineage_unavailable",
            reason_code="current_cognitive_publication_unavailable",
        )


__all__ = ["StructuredActionSemanticLineageBinder"]
