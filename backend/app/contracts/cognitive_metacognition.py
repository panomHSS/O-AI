"""D132 immutable Metacognition & Uncertainty contract.

This contract carries bounded provider-neutral epistemic metadata only. It
grants no authentication, authorization, approval, routing, provider/model
selection, publication, persistence, tool, memory, project, conversation,
calendar, or execution authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import CognitiveIntent


D132_METACOGNITION_ARTIFACT_TYPE = "cognitive.metacognition"
D132_METACOGNITION_CONTRACT_VERSION = "o-ai.cognitive-metacognition.v1"

D132_TEXT_MAX_BYTES = 2048
D132_UNKNOWN_MAX_COUNT = 160
D132_ASSUMPTION_MAX_COUNT = 320
D132_HYPOTHESIS_MAX_COUNT = 64
D132_UNCERTAINTY_REASON_MAX_COUNT = 256
D132_EVIDENCE_ID_MAX_COUNT = 256


MetacognitiveKnowledgeStatus: TypeAlias = Literal[
    "known",
    "partial",
    "insufficient",
    "unknown",
]
MetacognitiveEvidenceSufficiency: TypeAlias = Literal[
    "not_required",
    "sufficient",
    "insufficient",
]
MetacognitiveConfidenceClass: TypeAlias = Literal[
    "sufficient",
    "limited",
    "insufficient",
    "unknown",
]
MetacognitiveRecommendedAction: TypeAlias = Literal[
    "respond",
    "respond_with_uncertainty",
    "revise_reasoning",
    "ask_owner",
    "insufficient_information",
]


_COGNITIVE_INTENTS = frozenset(
    {
        "factual_lookup",
        "explanation",
        "comparison",
        "procedure",
        "troubleshooting",
        "summary",
        "general",
    }
)
_KNOWLEDGE_STATUSES = frozenset(
    {"known", "partial", "insufficient", "unknown"}
)
_EVIDENCE_SUFFICIENCY = frozenset(
    {"not_required", "sufficient", "insufficient"}
)
_CONFIDENCE_CLASSES = frozenset(
    {"sufficient", "limited", "insufficient", "unknown"}
)
_RECOMMENDED_ACTIONS = frozenset(
    {
        "respond",
        "respond_with_uncertainty",
        "revise_reasoning",
        "ask_owner",
        "insufficient_information",
    }
)


def _validate_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > max_bytes or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(code)
    return value


def _normalize_text_sequence(
    value: object,
    *,
    code: str,
    max_count: int,
) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > max_count
    ):
        raise ValueError(code)

    result: list[str] = []
    seen: set[str] = set()
    for raw in tuple(value):
        item = _validate_text(
            raw,
            code=code,
            max_bytes=D132_TEXT_MAX_BYTES,
        )
        if item in seen:
            raise ValueError(code)
        seen.add(item)
        result.append(item)
    return tuple(result)


def _validate_literal(
    value: object,
    *,
    allowed: frozenset[str],
    code: str,
) -> str:
    if type(value) is not str or value not in allowed:
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class CognitiveMetacognitionArtifact:
    """Bounded D132 metacognitive result for one frozen cognitive turn."""

    envelope: CognitiveArtifactEnvelope
    intent: CognitiveIntent

    knowledge_status: MetacognitiveKnowledgeStatus
    evidence_sufficiency: MetacognitiveEvidenceSufficiency
    confidence_class: MetacognitiveConfidenceClass
    recommended_cognitive_action: MetacognitiveRecommendedAction

    unknowns: tuple[str, ...] | Sequence[str] = ()
    assumptions: tuple[str, ...] | Sequence[str] = ()
    hypotheses: tuple[str, ...] | Sequence[str] = ()
    uncertainty_reasons: tuple[str, ...] | Sequence[str] = ()
    considered_evidence_ids: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, CognitiveArtifactEnvelope):
            raise ValueError("cognitive_metacognition_envelope_invalid")
        if (
            self.envelope.producer_organ is not CognitiveOrgan.METACOGNITION
            or self.envelope.artifact_type != D132_METACOGNITION_ARTIFACT_TYPE
            or self.envelope.contract_version
            != D132_METACOGNITION_CONTRACT_VERSION
            or self.envelope.context_snapshot_digest is None
            or self.envelope.status
            not in {
                CognitiveOrganStatus.READY,
                CognitiveOrganStatus.INSUFFICIENT,
            }
            or self.envelope.model_binding_reference is not None
        ):
            raise ValueError("cognitive_metacognition_envelope_invalid")

        _validate_literal(
            self.intent,
            allowed=_COGNITIVE_INTENTS,
            code="cognitive_metacognition_intent_invalid",
        )
        _validate_literal(
            self.knowledge_status,
            allowed=_KNOWLEDGE_STATUSES,
            code="cognitive_metacognition_knowledge_status_invalid",
        )
        _validate_literal(
            self.evidence_sufficiency,
            allowed=_EVIDENCE_SUFFICIENCY,
            code="cognitive_metacognition_evidence_sufficiency_invalid",
        )
        _validate_literal(
            self.confidence_class,
            allowed=_CONFIDENCE_CLASSES,
            code="cognitive_metacognition_confidence_class_invalid",
        )
        _validate_literal(
            self.recommended_cognitive_action,
            allowed=_RECOMMENDED_ACTIONS,
            code="cognitive_metacognition_recommended_action_invalid",
        )

        unknowns = _normalize_text_sequence(
            self.unknowns,
            code="cognitive_metacognition_unknowns_invalid",
            max_count=D132_UNKNOWN_MAX_COUNT,
        )
        assumptions = _normalize_text_sequence(
            self.assumptions,
            code="cognitive_metacognition_assumptions_invalid",
            max_count=D132_ASSUMPTION_MAX_COUNT,
        )
        hypotheses = _normalize_text_sequence(
            self.hypotheses,
            code="cognitive_metacognition_hypotheses_invalid",
            max_count=D132_HYPOTHESIS_MAX_COUNT,
        )
        uncertainty_reasons = _normalize_text_sequence(
            self.uncertainty_reasons,
            code="cognitive_metacognition_uncertainty_reasons_invalid",
            max_count=D132_UNCERTAINTY_REASON_MAX_COUNT,
        )
        considered_evidence_ids = _normalize_text_sequence(
            self.considered_evidence_ids,
            code="cognitive_metacognition_evidence_ids_invalid",
            max_count=D132_EVIDENCE_ID_MAX_COUNT,
        )

        expected = {
            "sufficient": (
                "known",
                CognitiveOrganStatus.READY,
                frozenset({"respond", "ask_owner"}),
            ),
            "limited": (
                "partial",
                CognitiveOrganStatus.READY,
                frozenset(
                    {
                        "respond_with_uncertainty",
                        "revise_reasoning",
                        "ask_owner",
                    }
                ),
            ),
            "insufficient": (
                "insufficient",
                CognitiveOrganStatus.INSUFFICIENT,
                frozenset({"insufficient_information"}),
            ),
            "unknown": (
                "unknown",
                CognitiveOrganStatus.INSUFFICIENT,
                frozenset({"insufficient_information"}),
            ),
        }[self.confidence_class]

        expected_knowledge, expected_status, allowed_actions = expected
        if (
            self.knowledge_status != expected_knowledge
            or self.envelope.status is not expected_status
            or self.recommended_cognitive_action not in allowed_actions
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        if (
            self.evidence_sufficiency == "insufficient"
            and self.confidence_class != "insufficient"
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        bounded_uncertainty = bool(
            assumptions or hypotheses or uncertainty_reasons
        )

        if self.confidence_class == "sufficient" and (
            unknowns or bounded_uncertainty
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        if self.confidence_class == "limited" and (
            unknowns or not bounded_uncertainty
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        if (
            self.recommended_cognitive_action == "revise_reasoning"
            and not hypotheses
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        if (
            self.recommended_cognitive_action == "respond_with_uncertainty"
            and not bounded_uncertainty
        ):
            raise ValueError("cognitive_metacognition_self_consistency_invalid")

        object.__setattr__(self, "unknowns", unknowns)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "hypotheses", hypotheses)
        object.__setattr__(self, "uncertainty_reasons", uncertainty_reasons)
        object.__setattr__(
            self,
            "considered_evidence_ids",
            considered_evidence_ids,
        )


__all__ = [
    "D132_ASSUMPTION_MAX_COUNT",
    "D132_EVIDENCE_ID_MAX_COUNT",
    "D132_HYPOTHESIS_MAX_COUNT",
    "D132_METACOGNITION_ARTIFACT_TYPE",
    "D132_METACOGNITION_CONTRACT_VERSION",
    "D132_TEXT_MAX_BYTES",
    "D132_UNCERTAINTY_REASON_MAX_COUNT",
    "D132_UNKNOWN_MAX_COUNT",
    "CognitiveMetacognitionArtifact",
    "MetacognitiveConfidenceClass",
    "MetacognitiveEvidenceSufficiency",
    "MetacognitiveKnowledgeStatus",
    "MetacognitiveRecommendedAction",
]
