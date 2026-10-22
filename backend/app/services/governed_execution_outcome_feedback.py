"""D182 deterministic, non-authoritative governed execution outcome feedback."""

from __future__ import annotations

from threading import RLock

from app.contracts.execution_approval import ExecutionApprovalDecisionOutcome
from app.contracts.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeClassification,
    GovernedExecutionOutcomeFeedback,
    compute_governed_execution_outcome_feedback_fingerprint,
)
from app.contracts.owner_approved_governed_execution import CognitiveExecutionBinding

DEFAULT_MAX_GOVERNED_EXECUTION_FEEDBACK = 100


class GovernedExecutionOutcomeFeedbackError(RuntimeError):
    reason_code = "governed_execution_feedback_invalid"


class GovernedExecutionOutcomeFeedbackConflictError(GovernedExecutionOutcomeFeedbackError):
    reason_code = "governed_execution_feedback_conflict"


class GovernedExecutionOutcomeFeedbackStoreFullError(GovernedExecutionOutcomeFeedbackError):
    reason_code = "governed_execution_feedback_store_full"


class GovernedExecutionOutcomeFeedbackStore:
    """Bounded process-local evidence store; never an execution replay source."""

    def __init__(self, *, max_items: int = DEFAULT_MAX_GOVERNED_EXECUTION_FEEDBACK) -> None:
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._items: dict[str, GovernedExecutionOutcomeFeedback] = {}
        self._lock = RLock()

    @property
    def feedback_count(self) -> int:
        with self._lock:
            return len(self._items)

    def register(self, feedback: GovernedExecutionOutcomeFeedback) -> GovernedExecutionOutcomeFeedback:
        if not isinstance(feedback, GovernedExecutionOutcomeFeedback):
            raise GovernedExecutionOutcomeFeedbackError("The governed execution feedback is invalid.")
        with self._lock:
            existing = self._items.get(feedback.approval_id)
            if existing is not None:
                if existing == feedback:
                    return existing
                raise GovernedExecutionOutcomeFeedbackConflictError(
                    "The approval already has different feedback evidence."
                )
            if len(self._items) >= self._max_items:
                raise GovernedExecutionOutcomeFeedbackStoreFullError(
                    "Governed execution feedback capacity is full."
                )
            self._items[feedback.approval_id] = feedback
            return feedback

    def get(self, approval_id: str) -> GovernedExecutionOutcomeFeedback | None:
        with self._lock:
            return self._items.get(approval_id)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class GovernedExecutionOutcomeFeedbackRecorder:
    """Validate, classify and record safe D182 evidence best-effort."""

    def __init__(self, *, store: GovernedExecutionOutcomeFeedbackStore) -> None:
        if not isinstance(store, GovernedExecutionOutcomeFeedbackStore):
            raise TypeError("store must be a GovernedExecutionOutcomeFeedbackStore.")
        self._store = store

    def try_record(self, binding: object, decision_outcome: object) -> bool:
        """Record safe evidence without ever raising into the decision lane."""
        try:
            feedback = self._project(binding, decision_outcome)
            self._store.register(feedback)
            return True
        except Exception:
            return False

    def _project(self, binding: object, decision_outcome: object) -> GovernedExecutionOutcomeFeedback:
        if not isinstance(binding, CognitiveExecutionBinding):
            raise GovernedExecutionOutcomeFeedbackError("The D181 cognitive execution binding is invalid.")
        if not isinstance(decision_outcome, ExecutionApprovalDecisionOutcome):
            raise GovernedExecutionOutcomeFeedbackError("The D45 decision outcome is invalid.")

        binding.__post_init__()
        decision_outcome.__post_init__()

        if binding.approval_id != decision_outcome.approval_id:
            raise GovernedExecutionOutcomeFeedbackError("The feedback approval identity does not match.")

        execution = decision_outcome.execution
        if binding.execution_request_id != execution.request_id:
            raise GovernedExecutionOutcomeFeedbackError("The feedback execution request identity does not match.")

        result_status = execution.result.status if execution.result is not None else None
        classification = self._classification(
            decision=decision_outcome.decision,
            execution_status=execution.status,
            result_status=result_status,
        )

        fingerprint = compute_governed_execution_outcome_feedback_fingerprint(
            workspace_id=binding.workspace_id,
            conversation_id=binding.conversation_id,
            source_turn_id=binding.source_turn_id,
            source_artifact_digest=binding.source_artifact_digest,
            intent_digest=binding.intent_digest,
            approval_id=binding.approval_id,
            execution_request_id=binding.execution_request_id,
            plan_digest=binding.plan_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            owner_decision=decision_outcome.decision,
            execution_status=execution.status,
            result_status=result_status,
            execution_reason_code=execution.reason_code,
            classification=classification,
        )

        return GovernedExecutionOutcomeFeedback(
            workspace_id=binding.workspace_id,
            conversation_id=binding.conversation_id,
            source_turn_id=binding.source_turn_id,
            source_artifact_digest=binding.source_artifact_digest,
            intent_digest=binding.intent_digest,
            approval_id=binding.approval_id,
            execution_request_id=binding.execution_request_id,
            plan_digest=binding.plan_digest,
            target_kind=binding.target_kind,
            capability_id=binding.capability_id,
            adapter_id=binding.adapter_id,
            operation=binding.operation,
            effect=binding.effect,
            risk_class=binding.risk_class,
            owner_decision=decision_outcome.decision,
            execution_status=execution.status,
            result_status=result_status,
            execution_reason_code=execution.reason_code,
            classification=classification,
            feedback_fingerprint=fingerprint,
        )

    @staticmethod
    def _classification(*, decision: str, execution_status: str, result_status: str | None) -> GovernedExecutionOutcomeClassification:
        if decision == "denied":
            if execution_status != "blocked" or result_status is not None:
                raise GovernedExecutionOutcomeFeedbackError("Owner denial outcome is incoherent.")
            return "owner_denied"
        if decision != "approved":
            raise GovernedExecutionOutcomeFeedbackError("Owner decision is unsupported.")
        if execution_status == "completed":
            mapping = {
                "succeeded": "execution_succeeded",
                "failed": "execution_failed",
                "blocked": "execution_blocked",
            }
            try:
                return mapping[result_status]  # type: ignore[index,return-value]
            except KeyError:
                raise GovernedExecutionOutcomeFeedbackError(
                    "Completed execution result status is unsupported."
                ) from None
        if result_status is not None:
            raise GovernedExecutionOutcomeFeedbackError(
                "Non-completed execution must not carry a result status."
            )
        mapping = {
            "blocked": "execution_blocked",
            "rejected": "execution_rejected",
            "unavailable": "execution_unavailable",
        }
        try:
            return mapping[execution_status]  # type: ignore[index,return-value]
        except KeyError:
            raise GovernedExecutionOutcomeFeedbackError("Execution status is unsupported.") from None


__all__ = [
    "DEFAULT_MAX_GOVERNED_EXECUTION_FEEDBACK",
    "GovernedExecutionOutcomeFeedbackConflictError",
    "GovernedExecutionOutcomeFeedbackError",
    "GovernedExecutionOutcomeFeedbackRecorder",
    "GovernedExecutionOutcomeFeedbackStore",
    "GovernedExecutionOutcomeFeedbackStoreFullError",
]
