"""D185 best-effort post-authority execution-experience runtime integration."""

from __future__ import annotations

from threading import RLock

from app.contracts.governed_execution_experience_runtime import (
    GovernedExecutionExperienceRuntimeOutcome,
)
from app.services.governed_execution_experience_candidate import (
    GovernedExecutionExperienceProjector,
)
from app.services.governed_execution_experience_review import (
    GovernedExecutionExperienceReviewEvaluator,
)
from app.services.governed_execution_outcome_feedback import (
    GovernedExecutionOutcomeFeedbackStore,
)

DEFAULT_MAX_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_OUTCOMES = 100


class GovernedExecutionExperienceRuntimeError(RuntimeError):
    reason_code = "governed_execution_experience_runtime_invalid"


class GovernedExecutionExperienceRuntimeConflictError(
    GovernedExecutionExperienceRuntimeError
):
    reason_code = "governed_execution_experience_runtime_conflict"


class GovernedExecutionExperienceRuntimeStoreFullError(
    GovernedExecutionExperienceRuntimeError
):
    reason_code = "governed_execution_experience_runtime_store_full"


class GovernedExecutionExperienceRuntimeStore:
    """Bounded process-local D185 evidence store with no silent eviction."""

    def __init__(
        self,
        *,
        max_items: int = DEFAULT_MAX_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_OUTCOMES,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._items: dict[str, GovernedExecutionExperienceRuntimeOutcome] = {}
        self._lock = RLock()

    @property
    def outcome_count(self) -> int:
        with self._lock:
            return len(self._items)

    def register(
        self,
        outcome: GovernedExecutionExperienceRuntimeOutcome,
    ) -> GovernedExecutionExperienceRuntimeOutcome:
        if type(outcome) is not GovernedExecutionExperienceRuntimeOutcome:
            raise GovernedExecutionExperienceRuntimeError(
                "The D185 runtime outcome is invalid."
            )
        outcome.__post_init__()
        with self._lock:
            existing = self._items.get(outcome.approval_id)
            if existing is not None:
                if existing == outcome:
                    return existing
                raise GovernedExecutionExperienceRuntimeConflictError(
                    "The approval already has a different D185 runtime outcome."
                )
            if len(self._items) >= self._max_items:
                raise GovernedExecutionExperienceRuntimeStoreFullError(
                    "D185 runtime evidence capacity is full."
                )
            self._items[outcome.approval_id] = outcome
            return outcome

    def get(
        self,
        approval_id: str,
    ) -> GovernedExecutionExperienceRuntimeOutcome | None:
        with self._lock:
            return self._items.get(approval_id)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class GovernedExecutionExperienceRuntimeIntegration:
    """Move exact D182 evidence through frozen D183 and D184, then stop."""

    def __init__(
        self,
        *,
        feedback_store: GovernedExecutionOutcomeFeedbackStore,
        runtime_store: GovernedExecutionExperienceRuntimeStore,
    ) -> None:
        if not isinstance(
            feedback_store,
            GovernedExecutionOutcomeFeedbackStore,
        ):
            raise TypeError(
                "feedback_store must be a GovernedExecutionOutcomeFeedbackStore."
            )
        if not isinstance(runtime_store, GovernedExecutionExperienceRuntimeStore):
            raise TypeError(
                "runtime_store must be a GovernedExecutionExperienceRuntimeStore."
            )
        self._feedback_store = feedback_store
        self._runtime_store = runtime_store

    def try_integrate(self, approval_id: str) -> bool:
        """Best-effort post-authority integration; never raise to execution."""
        try:
            outcome = self._integrate(approval_id)
            self._runtime_store.register(outcome)
            return True
        except Exception:
            return False

    def _integrate(
        self,
        approval_id: str,
    ) -> GovernedExecutionExperienceRuntimeOutcome:
        feedback = self._feedback_store.get(approval_id)
        if feedback is None:
            return GovernedExecutionExperienceRuntimeOutcome(
                approval_id=approval_id,
                runtime_status="integration_unavailable",
                source_feedback_fingerprint=None,
                candidate=None,
                review=None,
            )

        feedback.__post_init__()

        candidate = GovernedExecutionExperienceProjector.project(feedback)
        if candidate is None:
            return GovernedExecutionExperienceRuntimeOutcome(
                approval_id=feedback.approval_id,
                runtime_status="projection_failed",
                source_feedback_fingerprint=feedback.feedback_fingerprint,
                candidate=None,
                review=None,
            )

        review = GovernedExecutionExperienceReviewEvaluator.evaluate(candidate)
        status = {
            "eligible_for_owner_review": "review_eligible",
            "ineligible": "review_ineligible",
            "invalid_evidence": "invalid_evidence",
        }[review.eligibility]

        return GovernedExecutionExperienceRuntimeOutcome(
            approval_id=feedback.approval_id,
            runtime_status=status,
            source_feedback_fingerprint=feedback.feedback_fingerprint,
            candidate=candidate,
            review=review,
        )


__all__ = [
    "DEFAULT_MAX_GOVERNED_EXECUTION_EXPERIENCE_RUNTIME_OUTCOMES",
    "GovernedExecutionExperienceRuntimeConflictError",
    "GovernedExecutionExperienceRuntimeError",
    "GovernedExecutionExperienceRuntimeIntegration",
    "GovernedExecutionExperienceRuntimeStore",
    "GovernedExecutionExperienceRuntimeStoreFullError",
]
