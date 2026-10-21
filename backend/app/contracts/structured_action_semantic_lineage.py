"""D174 immutable structured action semantic lineage binding contracts.

D174 binds already-structured non-authoritative action semantics to the current
cognitive publication lineage. It grants no permission, approval,
authorization, routing, persistence, provider, connector, runtime, or execution
authority.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from app.contracts.structured_action_candidate_producer import (
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_intent_proposal import (
    freeze_structured_action_parameters,
)


D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION = (
    "o-ai.structured-action-semantic-lineage.v1"
)

StructuredActionSemanticLineageStatus: TypeAlias = Literal[
    "not_applicable",
    "lineage_unavailable",
    "semantic_ready",
]

_STATUSES = frozenset(
    {"not_applicable", "lineage_unavailable", "semantic_ready"}
)
_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_MAX_CODE_BYTES = 128
_MAX_MISSING_INFORMATION = 32


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
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(error)
    return value


def _normalize_missing_information(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > _MAX_MISSING_INFORMATION
    ):
        raise ValueError("structured_action_semantic_draft_missing_information_invalid")
    normalized = tuple(
        _code(
            item,
            error="structured_action_semantic_draft_missing_information_invalid",
        )
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError("structured_action_semantic_draft_missing_information_invalid")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class StructuredActionSemanticDraft:
    """Already-structured action meaning without caller-supplied lineage."""

    semantic_action: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    missing_information: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "semantic_action",
            _code(
                self.semantic_action,
                error="structured_action_semantic_draft_action_invalid",
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
class StructuredActionSemanticLineageOutcome:
    """D174 binding result only; never current-lineage validation authority."""

    status: StructuredActionSemanticLineageStatus
    reason_code: str
    semantic: StructuredActionSemanticInput | None = None
    contract_version: str = (
        D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("structured_action_semantic_lineage_status_invalid")
        expected_reason = {
            "not_applicable": "no_structured_action_semantic_draft",
            "lineage_unavailable": "current_cognitive_publication_unavailable",
            "semantic_ready": "structured_action_semantic_ready",
        }[self.status]
        if self.reason_code != expected_reason:
            raise ValueError("structured_action_semantic_lineage_reason_invalid")
        if (
            self.contract_version
            != D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION
        ):
            raise ValueError("structured_action_semantic_lineage_version_invalid")

        if self.status == "semantic_ready":
            if not isinstance(self.semantic, StructuredActionSemanticInput):
                raise ValueError("structured_action_semantic_lineage_semantic_required")
            return
        if self.semantic is not None:
            raise ValueError("structured_action_semantic_lineage_semantic_forbidden")


__all__ = [
    "D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_CONTRACT_VERSION",
    "StructuredActionSemanticDraft",
    "StructuredActionSemanticLineageOutcome",
    "StructuredActionSemanticLineageStatus",
]
