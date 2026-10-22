"""D179 bridge the D178 cognitive handoff into D177 without live routing."""

from __future__ import annotations

from uuid import UUID

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.command import CommandRequest
from app.contracts.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffOutcome,
)
from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.services.command_orchestrator import CommandOrchestrationOutcome
from app.services.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeIntegration,
)


_D177_STATUSES = frozenset(
    {
        "not_applicable",
        "invalid",
        "lineage_unavailable",
        "needs_clarification",
        "unsupported",
        "intent_rejected",
        "prepared_for_owner_review",
        "approval_unavailable",
    }
)


class ExplicitActionCognitiveHandoffIntegration:
    """Consume D178 metadata and call D177 once without adding authority."""

    def __init__(
        self,
        *,
        runtime: ExplicitActionSemanticRuntimeIntegration,
    ) -> None:
        if not isinstance(runtime, ExplicitActionSemanticRuntimeIntegration):
            raise TypeError(
                "runtime must be an ExplicitActionSemanticRuntimeIntegration."
            )
        self._runtime = runtime

    def process(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        command: CommandRequest,
        orchestration_outcome: CommandOrchestrationOutcome,
    ) -> ExplicitActionCognitiveHandoffOutcome:
        if not isinstance(command, CommandRequest):
            raise TypeError("command must be a CommandRequest.")
        if not isinstance(orchestration_outcome, CommandOrchestrationOutcome):
            raise TypeError(
                "orchestration_outcome must be a CommandOrchestrationOutcome."
            )

        cognitive_outcome = orchestration_outcome.cognitive_outcome
        if cognitive_outcome is None:
            return ExplicitActionCognitiveHandoffOutcome(
                status="cognitive_outcome_unavailable",
                reason_code="cognitive_outcome_unavailable",
            )
        if not isinstance(cognitive_outcome, CognitiveExecutiveOutcome):
            raise RuntimeError(
                "explicit_action_cognitive_handoff_cognitive_outcome_invalid"
            )

        runtime = self._runtime.process(
            message,
            project_id=project_id,
            command=command,
            cognitive_outcome=cognitive_outcome,
        )
        if not isinstance(runtime, ExplicitActionSemanticRuntimeOutcome):
            raise RuntimeError(
                "explicit_action_cognitive_handoff_runtime_invalid"
            )
        if runtime.status not in _D177_STATUSES:
            raise RuntimeError(
                "explicit_action_cognitive_handoff_runtime_status_invalid"
            )

        return ExplicitActionCognitiveHandoffOutcome(
            status=runtime.status,
            reason_code=runtime.reason_code,
            runtime=runtime,
        )


__all__ = ["ExplicitActionCognitiveHandoffIntegration"]
