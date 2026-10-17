"""D140/D141 best-effort, metadata-only cognitive runtime observability."""

from __future__ import annotations

import logging
from uuid import UUID

from app.contracts.cognitive_executive import CognitiveExecutiveOutcome
from app.contracts.cognitive_runtime_adoption import (
    CognitiveRuntimeLane,
    CognitiveRuntimeObservation,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId
from app.services.cognitive_runtime_assurance import CognitiveRuntimeAssurance
from app.services.cognitive_outcome_quality_feedback import (
    CognitiveOutcomeQualityFeedbackMonitor,
)


class CognitiveRuntimeObserver:
    """Record D140 safe metadata and D141 aggregate assurance independently."""

    def __init__(
        self,
        *,
        workspace_id: WorkspaceId,
        logger: logging.Logger | None = None,
        assurance: CognitiveRuntimeAssurance | None = None,
        outcome_quality_feedback: CognitiveOutcomeQualityFeedbackMonitor | None = None,
    ) -> None:
        if not isinstance(workspace_id, WorkspaceId):
            raise ValueError("cognitive_runtime_observer_workspace_invalid")
        self._workspace_id = workspace_id
        self._logger = logger or logging.getLogger("oai.cognitive_runtime")
        self._assurance = assurance
        self._outcome_quality_feedback = outcome_quality_feedback

    def try_record_selection(
        self,
        *,
        request_id: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
        selected_lane: CognitiveRuntimeLane,
        task_kind: AITaskKind,
    ) -> bool:
        """Record server-owned lane selection; never raise into Chat."""
        try:
            event = CognitiveRuntimeObservation(
                request_id=request_id,
                workspace_id=self._workspace_id,
                conversation_id=(
                    str(conversation_id) if conversation_id is not None else None
                ),
                project_id=(str(project_id) if project_id is not None else None),
                selected_lane=selected_lane,
                task_kind=task_kind,
            )
        except Exception:
            return False
        return self._record(event)

    def try_record_cognitive_outcome(
        self,
        *,
        request_id: str,
        conversation_id: UUID | None,
        project_id: UUID | None,
        task_kind: AITaskKind,
        outcome: CognitiveExecutiveOutcome,
    ) -> bool:
        """Record one terminal D136 outcome using only safe metadata."""
        try:
            if not isinstance(outcome, CognitiveExecutiveOutcome):
                raise ValueError("cognitive_runtime_outcome_invalid")
            if outcome.envelope.workspace_id is not self._workspace_id:
                raise ValueError("cognitive_runtime_outcome_workspace_mismatch")
            first_binding = outcome.bindings[0] if outcome.bindings else None
            event = CognitiveRuntimeObservation(
                request_id=request_id,
                workspace_id=self._workspace_id,
                conversation_id=(
                    str(conversation_id) if conversation_id is not None else None
                ),
                project_id=(str(project_id) if project_id is not None else None),
                selected_lane="cognitive",
                task_kind=task_kind,
                terminal_state=outcome.terminal_state,
                context_snapshot_digest=outcome.envelope.context_snapshot_digest,
                adapter_id=(
                    first_binding.adapter_id if first_binding is not None else None
                ),
                model_id=(first_binding.model_id if first_binding is not None else None),
                profile_id=(
                    first_binding.profile_id if first_binding is not None else None
                ),
                revision_count=outcome.revision_count,
                invocation_count=outcome.invocation_count,
                draft_generation_count=outcome.draft_generation_count,
                failure_code=outcome.failure_code,
                publication_disposition=outcome.publication_disposition,
            )
        except Exception:
            return False
        return self._record(event)

    def try_record_experience_feedback(self, candidate: object) -> bool:
        """Record D146 aggregate feedback without adding any per-turn log payload."""
        monitor = self._outcome_quality_feedback
        if monitor is None:
            return False
        try:
            return bool(monitor.try_record(candidate))
        except Exception:
            return False

    def _record(self, event: CognitiveRuntimeObservation) -> bool:
        payload = {
            "contract_version": event.contract_version,
            "request_id": event.request_id,
            "workspace_id": event.workspace_id.value,
            "conversation_id": event.conversation_id,
            "project_id": event.project_id,
            "selected_lane": event.selected_lane,
            "task_kind": event.task_kind.value,
            "terminal_state": (
                event.terminal_state.value if event.terminal_state is not None else None
            ),
            "context_snapshot_digest": event.context_snapshot_digest,
            "adapter_id": event.adapter_id,
            "model_id": event.model_id,
            "profile_id": event.profile_id,
            "revision_count": event.revision_count,
            "invocation_count": event.invocation_count,
            "draft_generation_count": event.draft_generation_count,
            "failure_code": (
                event.failure_code.value if event.failure_code is not None else None
            ),
            "publication_disposition": event.publication_disposition,
        }
        ok = True
        try:
            self._logger.info(
                "oai.cognitive_runtime",
                extra={"cognitive_runtime": payload},
            )
        except Exception:
            ok = False
        if self._assurance is not None:
            try:
                if event.terminal_state is None:
                    self._assurance.record_selection(event)
                else:
                    self._assurance.record_outcome(event)
            except Exception:
                ok = False
        return ok


__all__ = ["CognitiveRuntimeObserver"]
