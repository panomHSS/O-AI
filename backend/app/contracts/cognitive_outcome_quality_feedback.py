"""D146 immutable Outcome / Quality Feedback V1 contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

D146_REFERENCE_BASELINE = "bd773c16b154b23bdd57381ca8f6b25def29adb4"
D146_CONTRACT_VERSION = "1"
D146_SAMPLE_SCOPE = "cognitive_experience_candidates"
D146_COUNTER_MAX = 9_223_372_036_854_775_807

CognitiveOutcomeQualityClassification: TypeAlias = Literal[
    "verified_success",
    "bounded_insufficiency",
    "adverse_outcome",
    "invalid_evidence",
]
CognitiveOutcomeQualityReasonCode: TypeAlias = Literal[
    "verified_success",
    "bounded_insufficiency",
    "critic_exhausted",
    "invalid_cognition",
    "terminal_failure",
    "invalid_experience_candidate",
]

_VALID_REASON_CLASSIFICATION = {
    ("verified_success", "verified_success"),
    ("bounded_insufficiency", "bounded_insufficiency"),
    ("critic_exhausted", "adverse_outcome"),
    ("invalid_cognition", "adverse_outcome"),
    ("terminal_failure", "adverse_outcome"),
    ("invalid_experience_candidate", "invalid_evidence"),
}
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _counter(value: object, *, code: str) -> int:
    if (
        isinstance(value, bool)
        or type(value) is not int
        or not 0 <= value <= D146_COUNTER_MAX
    ):
        raise ValueError(code)
    return value


def compute_cognitive_outcome_quality_feedback_fingerprint(
    *,
    candidate_fingerprint: str,
    classification: CognitiveOutcomeQualityClassification,
    reason_code: CognitiveOutcomeQualityReasonCode,
) -> str:
    """Hash only the frozen D146 integrity projection."""

    if (
        type(candidate_fingerprint) is not str
        or _SHA256_HEX.fullmatch(candidate_fingerprint) is None
    ):
        raise ValueError("cognitive_outcome_quality_candidate_fingerprint_invalid")
    if (reason_code, classification) not in _VALID_REASON_CLASSIFICATION:
        raise ValueError("cognitive_outcome_quality_mapping_invalid")
    if classification == "invalid_evidence":
        raise ValueError("cognitive_outcome_quality_invalid_evidence_fingerprint")

    payload = {
        "candidate_fingerprint": candidate_fingerprint,
        "classification": classification,
        "contract_version": D146_CONTRACT_VERSION,
        "reason_code": reason_code,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveOutcomeQualityFeedbackAssessment:
    """One deterministic D134-derived quality assessment with no authority."""

    classification: CognitiveOutcomeQualityClassification
    reason_code: CognitiveOutcomeQualityReasonCode
    source_candidate_fingerprint: str | None
    feedback_fingerprint: str | None

    contract_version: Literal["1"] = D146_CONTRACT_VERSION
    reference_baseline: str = D146_REFERENCE_BASELINE

    learning_authority: Literal[False] = False
    retention_authority: Literal[False] = False
    experience_promotion_authority: Literal[False] = False
    memory_write_authority: Literal[False] = False
    routing_authority: Literal[False] = False
    model_selection_authority: Literal[False] = False
    execution_authority: Literal[False] = False
    configuration_authority: Literal[False] = False
    rollout_authority: Literal[False] = False
    automatic_learning: Literal[False] = False
    automatic_promotion: Literal[False] = False

    def __post_init__(self) -> None:
        if self.contract_version != D146_CONTRACT_VERSION:
            raise ValueError("cognitive_outcome_quality_contract_version_invalid")
        if self.reference_baseline != D146_REFERENCE_BASELINE:
            raise ValueError("cognitive_outcome_quality_baseline_invalid")
        if (self.reason_code, self.classification) not in _VALID_REASON_CLASSIFICATION:
            raise ValueError("cognitive_outcome_quality_mapping_invalid")

        if self.classification == "invalid_evidence":
            if (
                self.reason_code != "invalid_experience_candidate"
                or self.source_candidate_fingerprint is not None
                or self.feedback_fingerprint is not None
            ):
                raise ValueError("cognitive_outcome_quality_invalid_evidence_projection")
        else:
            if (
                type(self.source_candidate_fingerprint) is not str
                or _SHA256_HEX.fullmatch(self.source_candidate_fingerprint) is None
                or type(self.feedback_fingerprint) is not str
                or _SHA256_HEX.fullmatch(self.feedback_fingerprint) is None
            ):
                raise ValueError("cognitive_outcome_quality_fingerprint_invalid")
            expected = compute_cognitive_outcome_quality_feedback_fingerprint(
                candidate_fingerprint=self.source_candidate_fingerprint,
                classification=self.classification,
                reason_code=self.reason_code,
            )
            if self.feedback_fingerprint != expected:
                raise ValueError("cognitive_outcome_quality_fingerprint_mismatch")

        for name in (
            "learning_authority",
            "retention_authority",
            "experience_promotion_authority",
            "memory_write_authority",
            "routing_authority",
            "model_selection_authority",
            "execution_authority",
            "configuration_authority",
            "rollout_authority",
            "automatic_learning",
            "automatic_promotion",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"cognitive_outcome_quality_{name}_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveOutcomeQualityFeedbackSnapshot:
    """Process-local aggregate D146 evidence only."""

    observed: int = 0
    verified_success: int = 0
    bounded_insufficiency: int = 0
    adverse_outcome: int = 0
    invalid_evidence: int = 0

    lesson_verified_success: int = 0
    lesson_bounded_insufficiency: int = 0
    lesson_critic_exhausted: int = 0
    lesson_invalid_cognition: int = 0
    lesson_terminal_failure: int = 0

    contract_version: Literal["1"] = D146_CONTRACT_VERSION
    reference_baseline: str = D146_REFERENCE_BASELINE
    sample_scope: Literal["cognitive_experience_candidates"] = D146_SAMPLE_SCOPE
    reset_on_restart: Literal[True] = True

    def __post_init__(self) -> None:
        counter_names = (
            "observed",
            "verified_success",
            "bounded_insufficiency",
            "adverse_outcome",
            "invalid_evidence",
            "lesson_verified_success",
            "lesson_bounded_insufficiency",
            "lesson_critic_exhausted",
            "lesson_invalid_cognition",
            "lesson_terminal_failure",
        )
        for name in counter_names:
            _counter(
                getattr(self, name),
                code=f"cognitive_outcome_quality_{name}_invalid",
            )

        if (
            self.verified_success
            + self.bounded_insufficiency
            + self.adverse_outcome
            + self.invalid_evidence
            != self.observed
        ):
            raise ValueError("cognitive_outcome_quality_classification_count_invalid")

        if (
            self.lesson_verified_success
            + self.lesson_bounded_insufficiency
            + self.lesson_critic_exhausted
            + self.lesson_invalid_cognition
            + self.lesson_terminal_failure
            != self.observed - self.invalid_evidence
        ):
            raise ValueError("cognitive_outcome_quality_lesson_count_invalid")

        if self.contract_version != D146_CONTRACT_VERSION:
            raise ValueError("cognitive_outcome_quality_snapshot_version_invalid")
        if self.reference_baseline != D146_REFERENCE_BASELINE:
            raise ValueError("cognitive_outcome_quality_snapshot_baseline_invalid")
        if self.sample_scope != D146_SAMPLE_SCOPE:
            raise ValueError("cognitive_outcome_quality_snapshot_scope_invalid")
        if self.reset_on_restart is not True:
            raise ValueError("cognitive_outcome_quality_snapshot_reset_invalid")


__all__ = [
    "D146_CONTRACT_VERSION",
    "D146_COUNTER_MAX",
    "D146_REFERENCE_BASELINE",
    "D146_SAMPLE_SCOPE",
    "CognitiveOutcomeQualityClassification",
    "CognitiveOutcomeQualityFeedbackAssessment",
    "CognitiveOutcomeQualityFeedbackSnapshot",
    "CognitiveOutcomeQualityReasonCode",
    "compute_cognitive_outcome_quality_feedback_fingerprint",
]
