"""D127 immutable Perception, Attention, and Task Understanding contracts.

These contracts are provider-neutral cognitive metadata only. They grant no
authentication, authorization, approval, routing, model, profile, connector,
tool, memory-mutation, persistence, or execution authority.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import CognitiveArtifactEnvelope, CognitiveOrgan
from app.contracts.context import ContextSourceRef
from app.contracts.task_aware_ai_routing import AITaskKind


D127_PERCEPTION_ARTIFACT_TYPE = "cognitive.perception"
D127_PERCEPTION_CONTRACT_VERSION = "o-ai.cognitive-perception.v1"
D127_ATTENTION_ARTIFACT_TYPE = "cognitive.attention"
D127_ATTENTION_CONTRACT_VERSION = "o-ai.cognitive-attention.v1"
D127_TASK_DESCRIPTION_ARTIFACT_TYPE = "cognitive.task_description"
D127_TASK_DESCRIPTION_CONTRACT_VERSION = "o-ai.cognitive-task-description.v1"
D127_ATTENTION_SELECTION_POLICY = "d95_context_resolver.v1"

D127_NORMALIZED_REQUEST_MAX_BYTES = 16_384
D127_TASK_METADATA_ITEM_MAX_BYTES = 128
D127_TASK_METADATA_MAX_COUNT = 32
D127_PERCEPTION_MAX_PERCEPTS = 16_384
D127_ATTENTION_MAX_SELECTED_SOURCES = 256


CognitiveInteractionIntent: TypeAlias = Literal[
    "chat",
    "action_request",
    "approval_related_input",
    "runtime_status_request",
    "unknown",
]

CognitiveIntent: TypeAlias = Literal[
    "factual_lookup",
    "explanation",
    "comparison",
    "procedure",
    "troubleshooting",
    "summary",
    "general",
]


_INTERACTION_INTENTS = frozenset(
    {
        "chat",
        "action_request",
        "approval_related_input",
        "runtime_status_request",
        "unknown",
    }
)
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


def _validate_interaction_intent(value: object) -> CognitiveInteractionIntent:
    if type(value) is not str or value not in _INTERACTION_INTENTS:
        raise ValueError("cognitive_interaction_intent_invalid")
    return value  # type: ignore[return-value]


def _validate_cognitive_intent(value: object) -> CognitiveIntent:
    if type(value) is not str or value not in _COGNITIVE_INTENTS:
        raise ValueError("cognitive_intent_invalid")
    return value  # type: ignore[return-value]


def _validate_metadata_item(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("cognitive_task_metadata_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("cognitive_task_metadata_invalid") from None
    if len(encoded) > D127_TASK_METADATA_ITEM_MAX_BYTES or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError("cognitive_task_metadata_invalid")
    return value


def _normalize_metadata_sequence(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
    ):
        raise ValueError("cognitive_task_metadata_invalid")
    if len(value) > D127_TASK_METADATA_MAX_COUNT:
        raise ValueError("cognitive_task_metadata_invalid")

    copied = tuple(value)
    validated: list[str] = []
    seen: set[str] = set()
    for item in copied:
        validated_item = _validate_metadata_item(item)
        if validated_item in seen:
            raise ValueError("cognitive_task_metadata_invalid")
        seen.add(validated_item)
        validated.append(validated_item)
    return tuple(validated)


def _validate_normalized_request(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("cognitive_normalized_request_invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("cognitive_normalized_request_invalid") from None
    if (
        len(encoded) > D127_NORMALIZED_REQUEST_MAX_BYTES
        or any(unicodedata.category(character) == "Cc" for character in value)
        or value != " ".join(value.split())
    ):
        raise ValueError("cognitive_normalized_request_invalid")
    return value


def _require_envelope(
    envelope: object,
    *,
    organ: CognitiveOrgan,
    artifact_type: str,
    contract_version: str,
    code: str,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise ValueError(code)
    if (
        envelope.producer_organ is not organ
        or envelope.artifact_type != artifact_type
        or envelope.contract_version != contract_version
    ):
        raise ValueError(code)
    return envelope


def _source_identity(source: ContextSourceRef) -> tuple[object, object, str]:
    return (source.workspace_id, source.layer, source.source_id)


@dataclass(frozen=True, slots=True)
class CognitivePerceptRef:
    """Safe source metadata for one pre-selection Context candidate."""

    source: ContextSourceRef
    candidate_rank: int
    relevance: int | float | None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ContextSourceRef):
            raise ValueError("cognitive_percept_source_invalid")
        if (
            type(self.candidate_rank) is not int
            or self.candidate_rank < 1
            or self.candidate_rank > D127_PERCEPTION_MAX_PERCEPTS
        ):
            raise ValueError("cognitive_percept_rank_invalid")
        if self.relevance is not None:
            if (
                isinstance(self.relevance, bool)
                or not isinstance(self.relevance, (int, float))
                or not math.isfinite(float(self.relevance))
            ):
                raise ValueError("cognitive_percept_relevance_invalid")


@dataclass(frozen=True, slots=True)
class CognitivePerceptionArtifact:
    """Perception records safe candidate metadata without copying Context text."""

    envelope: CognitiveArtifactEnvelope
    percepts: tuple[CognitivePerceptRef, ...] | Sequence[CognitivePerceptRef] = ()

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.PERCEPTION,
            artifact_type=D127_PERCEPTION_ARTIFACT_TYPE,
            contract_version=D127_PERCEPTION_CONTRACT_VERSION,
            code="cognitive_perception_envelope_invalid",
        )
        if (
            isinstance(self.percepts, (str, bytes, bytearray))
            or not isinstance(self.percepts, Sequence)
            or len(self.percepts) > D127_PERCEPTION_MAX_PERCEPTS
        ):
            raise ValueError("cognitive_perception_percepts_invalid")

        percepts = tuple(self.percepts)
        for index, percept in enumerate(percepts, start=1):
            if not isinstance(percept, CognitivePerceptRef):
                raise ValueError("cognitive_perception_percepts_invalid")
            if percept.candidate_rank != index:
                raise ValueError("cognitive_perception_rank_sequence_invalid")
            if percept.source.workspace_id is not envelope.workspace_id:
                raise ValueError("cognitive_perception_workspace_mismatch")

        object.__setattr__(self, "percepts", percepts)


@dataclass(frozen=True, slots=True)
class CognitiveAttentionArtifact:
    """Attention records D95-selected source identities in their selected order."""

    envelope: CognitiveArtifactEnvelope
    selected_sources: tuple[ContextSourceRef, ...] | Sequence[ContextSourceRef] = ()
    selection_policy: str = D127_ATTENTION_SELECTION_POLICY

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.ATTENTION,
            artifact_type=D127_ATTENTION_ARTIFACT_TYPE,
            contract_version=D127_ATTENTION_CONTRACT_VERSION,
            code="cognitive_attention_envelope_invalid",
        )
        if self.selection_policy != D127_ATTENTION_SELECTION_POLICY:
            raise ValueError("cognitive_attention_selection_policy_invalid")
        if (
            isinstance(self.selected_sources, (str, bytes, bytearray))
            or not isinstance(self.selected_sources, Sequence)
            or len(self.selected_sources) > D127_ATTENTION_MAX_SELECTED_SOURCES
        ):
            raise ValueError("cognitive_attention_selected_sources_invalid")

        selected_sources = tuple(self.selected_sources)
        seen: set[tuple[object, object, str]] = set()
        for source in selected_sources:
            if not isinstance(source, ContextSourceRef):
                raise ValueError("cognitive_attention_selected_sources_invalid")
            if source.workspace_id is not envelope.workspace_id:
                raise ValueError("cognitive_attention_workspace_mismatch")
            identity = _source_identity(source)
            if identity in seen:
                raise ValueError("cognitive_attention_duplicate_source")
            seen.add(identity)

        object.__setattr__(self, "selected_sources", selected_sources)


@dataclass(frozen=True, slots=True)
class CognitiveTaskDescription:
    """Canonical non-authoritative task semantics for one cognitive turn."""

    envelope: CognitiveArtifactEnvelope
    interaction_intent: CognitiveInteractionIntent
    cognitive_intent: CognitiveIntent
    authoritative_ai_task_kind: AITaskKind
    normalized_request: str
    required_information: tuple[str, ...] | Sequence[str]
    information_gaps: tuple[str, ...] | Sequence[str] = ()
    constraints: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.TASK_UNDERSTANDING,
            artifact_type=D127_TASK_DESCRIPTION_ARTIFACT_TYPE,
            contract_version=D127_TASK_DESCRIPTION_CONTRACT_VERSION,
            code="cognitive_task_description_envelope_invalid",
        )
        _validate_interaction_intent(self.interaction_intent)
        _validate_cognitive_intent(self.cognitive_intent)
        if not isinstance(self.authoritative_ai_task_kind, AITaskKind):
            raise ValueError("invalid_task_kind")
        _validate_normalized_request(self.normalized_request)

        object.__setattr__(
            self,
            "required_information",
            _normalize_metadata_sequence(self.required_information),
        )
        object.__setattr__(
            self,
            "information_gaps",
            _normalize_metadata_sequence(self.information_gaps),
        )
        object.__setattr__(
            self,
            "constraints",
            _normalize_metadata_sequence(self.constraints),
        )


__all__ = [
    "D127_ATTENTION_ARTIFACT_TYPE",
    "D127_ATTENTION_CONTRACT_VERSION",
    "D127_ATTENTION_MAX_SELECTED_SOURCES",
    "D127_ATTENTION_SELECTION_POLICY",
    "D127_NORMALIZED_REQUEST_MAX_BYTES",
    "D127_PERCEPTION_ARTIFACT_TYPE",
    "D127_PERCEPTION_CONTRACT_VERSION",
    "D127_PERCEPTION_MAX_PERCEPTS",
    "D127_TASK_DESCRIPTION_ARTIFACT_TYPE",
    "D127_TASK_DESCRIPTION_CONTRACT_VERSION",
    "D127_TASK_METADATA_ITEM_MAX_BYTES",
    "D127_TASK_METADATA_MAX_COUNT",
    "CognitiveAttentionArtifact",
    "CognitiveInteractionIntent",
    "CognitiveIntent",
    "CognitivePerceptRef",
    "CognitivePerceptionArtifact",
    "CognitiveTaskDescription",
]
