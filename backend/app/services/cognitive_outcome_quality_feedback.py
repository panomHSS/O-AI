"""D146 deterministic outcome / quality feedback evaluation and aggregation."""

from __future__ import annotations

from threading import Lock

from app.contracts.cognitive_experience import CognitiveExperienceCandidateArtifact
from app.contracts.cognitive_outcome_quality_feedback import (
    D146_COUNTER_MAX,
    CognitiveOutcomeQualityFeedbackAssessment,
    CognitiveOutcomeQualityFeedbackSnapshot,
    compute_cognitive_outcome_quality_feedback_fingerprint,
)


class CognitiveOutcomeQualityFeedbackEvaluator:
    """Pure D134-candidate evaluator; never learning, routing, or execution."""

    _CLASSIFICATION_BY_LESSON = {
        "verified_success": "verified_success",
        "bounded_insufficiency": "bounded_insufficiency",
        "critic_exhausted": "adverse_outcome",
        "invalid_cognition": "adverse_outcome",
        "terminal_failure": "adverse_outcome",
    }

    @staticmethod
    def _invalid() -> CognitiveOutcomeQualityFeedbackAssessment:
        return CognitiveOutcomeQualityFeedbackAssessment(
            classification="invalid_evidence",
            reason_code="invalid_experience_candidate",
            source_candidate_fingerprint=None,
            feedback_fingerprint=None,
        )

    @classmethod
    def evaluate(
        cls,
        candidate: object,
    ) -> CognitiveOutcomeQualityFeedbackAssessment:
        if type(candidate) is not CognitiveExperienceCandidateArtifact:
            return cls._invalid()
        try:
            candidate.__post_init__()
            classification = cls._CLASSIFICATION_BY_LESSON[candidate.lesson_code]
            reason_code = candidate.lesson_code
            feedback_fingerprint = (
                compute_cognitive_outcome_quality_feedback_fingerprint(
                    candidate_fingerprint=candidate.candidate_fingerprint,
                    classification=classification,  # type: ignore[arg-type]
                    reason_code=reason_code,  # type: ignore[arg-type]
                )
            )
            return CognitiveOutcomeQualityFeedbackAssessment(
                classification=classification,  # type: ignore[arg-type]
                reason_code=reason_code,  # type: ignore[arg-type]
                source_candidate_fingerprint=candidate.candidate_fingerprint,
                feedback_fingerprint=feedback_fingerprint,
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return cls._invalid()


class CognitiveOutcomeQualityFeedbackMonitor:
    """Thread-safe process-local aggregate monitor with saturating int64 counts."""

    def __init__(
        self,
        *,
        evaluator: type[CognitiveOutcomeQualityFeedbackEvaluator] = (
            CognitiveOutcomeQualityFeedbackEvaluator
        ),
    ) -> None:
        self._evaluator = evaluator
        self._lock = Lock()
        self._counts = {
            "observed": 0,
            "verified_success": 0,
            "bounded_insufficiency": 0,
            "adverse_outcome": 0,
            "invalid_evidence": 0,
            "lesson_verified_success": 0,
            "lesson_bounded_insufficiency": 0,
            "lesson_critic_exhausted": 0,
            "lesson_invalid_cognition": 0,
            "lesson_terminal_failure": 0,
        }

    def try_record(self, candidate: object) -> bool:
        """Best-effort aggregation; malformed evidence is counted, not trusted."""

        try:
            assessment = self._evaluator.evaluate(candidate)
            if not isinstance(
                assessment,
                CognitiveOutcomeQualityFeedbackAssessment,
            ):
                return False
            assessment.__post_init__()
        except Exception:
            return False

        try:
            with self._lock:
                if self._counts["observed"] >= D146_COUNTER_MAX:
                    return True

                self._counts["observed"] += 1
                self._counts[assessment.classification] += 1

                if assessment.classification != "invalid_evidence":
                    lesson_counter = f"lesson_{assessment.reason_code}"
                    if lesson_counter not in self._counts:
                        return False
                    self._counts[lesson_counter] += 1
            return True
        except Exception:
            return False

    def snapshot(self) -> CognitiveOutcomeQualityFeedbackSnapshot:
        with self._lock:
            values = dict(self._counts)
        return CognitiveOutcomeQualityFeedbackSnapshot(**values)


__all__ = [
    "CognitiveOutcomeQualityFeedbackEvaluator",
    "CognitiveOutcomeQualityFeedbackMonitor",
]
