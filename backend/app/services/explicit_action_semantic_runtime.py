"""D177 compose D176 explicit semantic production into D175 governed runtime."""

from __future__ import annotations

from uuid import UUID

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
)
from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)
from app.services.explicit_action_semantic_draft_producer import (
    ExplicitActionDirectiveSemanticDraftProducer,
)
from app.services.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeIntegration,
)


_DOWNSTREAM = frozenset(
    {
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


class ExplicitActionSemanticRuntimeIntegration:
    """Compose D176 -> D175 without reparsing, inference, or new authority."""

    def __init__(
        self,
        *,
        producer: ExplicitActionDirectiveSemanticDraftProducer,
        semantic_runtime: StructuredActionSemanticRuntimeIntegration,
    ) -> None:
        if not isinstance(producer, ExplicitActionDirectiveSemanticDraftProducer):
            raise TypeError(
                "producer must be an ExplicitActionDirectiveSemanticDraftProducer."
            )
        if not isinstance(
            semantic_runtime,
            StructuredActionSemanticRuntimeIntegration,
        ):
            raise TypeError(
                "semantic_runtime must be a "
                "StructuredActionSemanticRuntimeIntegration."
            )
        self._producer = producer
        self._semantic_runtime = semantic_runtime

    def process(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        command: CommandRequest,
        cognitive_outcome: CognitiveExecutiveOutcome,
    ) -> ExplicitActionSemanticRuntimeOutcome:
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise TypeError(
                "cognitive_outcome must be a CognitiveExecutiveOutcome."
            )

        production = self._producer.produce(
            message,
            project_id=project_id,
        )
        if not isinstance(
            production,
            ExplicitActionSemanticDraftProductionOutcome,
        ):
            raise RuntimeError(
                "explicit_action_semantic_runtime_production_invalid"
            )

        if production.status == "not_applicable":
            return ExplicitActionSemanticRuntimeOutcome(
                status="not_applicable",
                reason_code=production.reason_code,
                production=production,
            )

        if production.status == "invalid":
            return ExplicitActionSemanticRuntimeOutcome(
                status="invalid",
                reason_code=production.reason_code,
                production=production,
            )

        if production.status != "semantic_ready":
            raise RuntimeError(
                "explicit_action_semantic_runtime_production_status_invalid"
            )

        draft = production.draft
        if draft is None:
            raise RuntimeError(
                "explicit_action_semantic_runtime_draft_missing"
            )

        runtime = self._semantic_runtime.process(
            draft,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )
        if not isinstance(runtime, StructuredActionSemanticRuntimeOutcome):
            raise RuntimeError(
                "explicit_action_semantic_runtime_downstream_invalid"
            )
        if runtime.status == "not_applicable":
            raise RuntimeError(
                "explicit_action_semantic_runtime_downstream_invariant"
            )
        if runtime.status not in _DOWNSTREAM:
            raise RuntimeError(
                "explicit_action_semantic_runtime_downstream_status_invalid"
            )

        return ExplicitActionSemanticRuntimeOutcome(
            status=runtime.status,
            reason_code=runtime.reason_code,
            production=production,
            runtime=runtime,
        )


__all__ = ["ExplicitActionSemanticRuntimeIntegration"]
