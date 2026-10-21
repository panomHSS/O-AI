"""D172 immutable structured action candidate producer contracts.

D172 carries structured semantic action metadata only. It grants no
authentication, authorization, permission, approval, capability, persistence,
connector, tool/module runtime, or execution authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
    freeze_structured_action_parameters,
)


D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION = (
    "o-ai.structured-action-candidate-producer.v1"
)

StructuredActionCandidateProductionStatus: TypeAlias = Literal[
    "not_applicable",
    "needs_clarification",
    "unsupported",
    "candidate_ready",
]

_STATUSES = frozenset(
    {
        "not_applicable",
        "needs_clarification",
        "unsupported",
        "candidate_ready",
    }
)
_HEX = frozenset("0123456789abcdef")
_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_MAX_TEXT_BYTES = 1024
_MAX_CODE_BYTES = 128
_MAX_MISSING_INFORMATION = 32


def _text(value: object, *, code: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > _MAX_TEXT_BYTES
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _digest(value: object, *, code: str) -> str:
    text = _text(value, code=code)
    if len(text) != 64 or any(character not in _HEX for character in text):
        raise ValueError(code)
    return text


def _code(value: object, *, error: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(error)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(error) from None
    if (
        len(encoded) > _MAX_CODE_BYTES
        or value[0] not in frozenset("abcdefghijklmnopqrstuvwxyz")
        or any(character not in _CODE_CHARS for character in value)
    ):
        raise ValueError(error)
    return value


def _normalize_missing_information(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > _MAX_MISSING_INFORMATION
    ):
        raise ValueError("structured_action_semantic_missing_information_invalid")
    normalized = tuple(
        _code(
            item,
            error="structured_action_semantic_missing_information_invalid",
        )
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError("structured_action_semantic_missing_information_invalid")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class StructuredActionSemanticInput:
    """Already-structured non-authoritative action semantics for D172."""

    source_turn_id: str
    source_artifact_digest: str
    semantic_action: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    missing_information: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_turn_id",
            _text(
                self.source_turn_id,
                code="structured_action_semantic_source_turn_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "source_artifact_digest",
            _digest(
                self.source_artifact_digest,
                code="structured_action_semantic_source_artifact_digest_invalid",
            ),
        )
        object.__setattr__(
            self,
            "semantic_action",
            _code(
                self.semantic_action,
                error="structured_action_semantic_action_invalid",
            ),
        )
        object.__setattr__(
            self,
            "parameters",
            freeze_structured_action_parameters(self.parameters),
        )
        object.__setattr__(
            self,
            "missing_information",
            _normalize_missing_information(self.missing_information),
        )


@dataclass(frozen=True, slots=True)
class StructuredActionCandidateProductionOutcome:
    """D172 result only; never permission, approval, or execution authority."""

    status: StructuredActionCandidateProductionStatus
    reason_code: str
    candidate: StructuredActionIntentCandidate | None = None
    contract_version: str = (
        D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_candidate_status_invalid")
        if (
            self.contract_version
            != D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION
        ):
            raise ValueError("structured_action_candidate_contract_version_invalid")

        expected_reason = {
            "not_applicable": "no_structured_action_semantics",
            "needs_clarification": "structured_action_information_missing",
            "unsupported": "structured_action_semantic_unsupported",
            "candidate_ready": "structured_action_candidate_ready",
        }[self.status]
        if self.reason_code != expected_reason:
            raise ValueError("structured_action_candidate_reason_invalid")

        if self.status in {"not_applicable", "unsupported"}:
            if self.candidate is not None:
                raise ValueError("structured_action_candidate_absence_invalid")
            return

        if not isinstance(self.candidate, StructuredActionIntentCandidate):
            raise ValueError("structured_action_candidate_required")

        if self.status == "needs_clarification":
            if not self.candidate.missing_information:
                raise ValueError("structured_action_candidate_clarification_invalid")
            return

        if self.candidate.missing_information:
            raise ValueError("structured_action_candidate_ready_invalid")


__all__ = [
    "D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_CONTRACT_VERSION",
    "StructuredActionCandidateProductionOutcome",
    "StructuredActionCandidateProductionStatus",
    "StructuredActionSemanticInput",
]