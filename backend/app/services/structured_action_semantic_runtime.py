"""D175 compose D174 lineage binding into the existing D173 governed runtime."""

from __future__ import annotations

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeOutcome,
)
from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
    StructuredActionSemanticLineageOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)
from app.services.structured_action_candidate_runtime import (
    StructuredActionCandidateRuntimeIntegration,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)


_DOWNSTREAM = frozenset(
    {
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


class StructuredActionSemanticRuntimeIntegration:
    """Compose D174 -> D173 without semantic inference or new authority."""

    def __init__(
        self,
        *,
        lineage_binder: StructuredActionSemanticLineageBinder,
        candidate_runtime: StructuredActionCandidateRuntimeIntegration,
    ) -> None:
        if not isinstance(lineage_binder, StructuredActionSemanticLineageBinder):
            raise TypeError(
                "lineage_binder must be a StructuredActionSemanticLineageBinder."
            )
        if not isinstance(
            candidate_runtime,
            StructuredActionCandidateRuntimeIntegration,
        ):
            raise TypeError(
                "candidate_runtime must be a "
                "StructuredActionCandidateRuntimeIntegration."
            )
        self._lineage_binder = lineage_binder
        self._candidate_runtime = candidate_runtime

    def process(
        self,
        draft: StructuredActionSemanticDraft | None,
        *,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> StructuredActionSemanticRuntimeOutcome:
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

        lineage = self._lineage_binder.bind(
            draft,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )
        if not isinstance(lineage, StructuredActionSemanticLineageOutcome):
            raise RuntimeError(
                "structured_action_semantic_runtime_lineage_invalid"
            )

        if lineage.status == "not_applicable":
            return StructuredActionSemanticRuntimeOutcome(
                status="not_applicable",
                reason_code=lineage.reason_code,
                lineage=lineage,
            )

        if lineage.status == "lineage_unavailable":
            return StructuredActionSemanticRuntimeOutcome(
                status="lineage_unavailable",
                reason_code=lineage.reason_code,
                lineage=lineage,
            )

        if lineage.status != "semantic_ready":
            raise RuntimeError(
                "structured_action_semantic_runtime_lineage_status_invalid"
            )

        semantic = lineage.semantic
        if semantic is None:
            raise RuntimeError(
                "structured_action_semantic_runtime_semantic_missing"
            )

        runtime = self._candidate_runtime.process(
            semantic,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )
        if not isinstance(runtime, StructuredActionCandidateRuntimeOutcome):
            raise RuntimeError(
                "structured_action_semantic_runtime_downstream_invalid"
            )
        if runtime.status == "no_action_semantics":
            raise RuntimeError(
                "structured_action_semantic_runtime_downstream_invariant"
            )
        if runtime.status not in _DOWNSTREAM:
            raise RuntimeError(
                "structured_action_semantic_runtime_downstream_status_invalid"
            )

        return StructuredActionSemanticRuntimeOutcome(
            status=runtime.status,
            reason_code=runtime.reason_code,
            lineage=lineage,
            runtime=runtime,
        )


__all__ = ["StructuredActionSemanticRuntimeIntegration"]
