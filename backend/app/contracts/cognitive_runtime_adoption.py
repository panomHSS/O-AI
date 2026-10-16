"""D140 immutable cognitive runtime production-adoption observation contract.

This contract carries allowlisted operational metadata only. It grants no
authentication, authorization, routing, provider/model/profile selection,
publication, persistence, tool, module, plugin, connector, or execution
authority and never contains prompts, response text, Context, Memory, or
credential material.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.cognitive_brain import (
    COGNITIVE_REVISION_COUNT_MAX,
    CognitiveFailureCode,
    CognitiveTurnState,
)
from app.contracts.cognitive_executive import (
    D136_MAX_DRAFT_GENERATIONS,
    D136_MAX_MODEL_INVOCATIONS,
)
from app.contracts.cognitive_verification import PublicationDisposition
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId


D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION = (
    "o-ai.cognitive-runtime-adoption.v1"
)

CognitiveRuntimeLane: TypeAlias = Literal["cognitive", "legacy"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LANES = frozenset({"cognitive", "legacy"})
_PUBLICATION_DISPOSITIONS = frozenset(
    {
        "eligible",
        "bounded_insufficiency_only",
        "revision_required",
        "blocked",
    }
)
_MAX_IDENTIFIER_BYTES = 512


def _text(value: object, *, code: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    if len(value.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        raise ValueError(code)
    return value


def _optional_text(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _text(value, code=code)


def _optional_digest(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _optional_count(
    value: object,
    *,
    code: str,
    maximum: int,
) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or type(value) is not int
        or not 0 <= value <= maximum
    ):
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class CognitiveRuntimeObservation:
    """One safe D140 production-adoption observation."""

    request_id: str
    workspace_id: WorkspaceId
    selected_lane: CognitiveRuntimeLane
    task_kind: AITaskKind
    conversation_id: str | None = None
    project_id: str | None = None
    terminal_state: CognitiveTurnState | None = None
    context_snapshot_digest: str | None = None
    adapter_id: str | None = None
    model_id: str | None = None
    profile_id: str | None = None
    revision_count: int | None = None
    invocation_count: int | None = None
    draft_generation_count: int | None = None
    failure_code: CognitiveFailureCode | None = None
    publication_disposition: PublicationDisposition | None = None
    contract_version: str = D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _text(self.request_id, code="cognitive_runtime_request_id_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("cognitive_runtime_workspace_invalid")
        if self.selected_lane not in _LANES:
            raise ValueError("cognitive_runtime_lane_invalid")
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("cognitive_runtime_task_kind_invalid")

        _optional_text(
            self.conversation_id,
            code="cognitive_runtime_conversation_id_invalid",
        )
        _optional_text(
            self.project_id,
            code="cognitive_runtime_project_id_invalid",
        )
        _optional_digest(
            self.context_snapshot_digest,
            code="cognitive_runtime_context_digest_invalid",
        )
        _optional_text(
            self.adapter_id,
            code="cognitive_runtime_adapter_id_invalid",
        )
        _optional_text(
            self.model_id,
            code="cognitive_runtime_model_id_invalid",
        )
        _optional_text(
            self.profile_id,
            code="cognitive_runtime_profile_id_invalid",
        )

        if self.terminal_state is not None and not isinstance(
            self.terminal_state,
            CognitiveTurnState,
        ):
            raise ValueError("cognitive_runtime_terminal_state_invalid")

        revision_count = _optional_count(
            self.revision_count,
            code="cognitive_runtime_revision_count_invalid",
            maximum=COGNITIVE_REVISION_COUNT_MAX,
        )
        invocation_count = _optional_count(
            self.invocation_count,
            code="cognitive_runtime_invocation_count_invalid",
            maximum=D136_MAX_MODEL_INVOCATIONS,
        )
        draft_generation_count = _optional_count(
            self.draft_generation_count,
            code="cognitive_runtime_draft_generation_count_invalid",
            maximum=D136_MAX_DRAFT_GENERATIONS,
        )
        object.__setattr__(self, "revision_count", revision_count)
        object.__setattr__(self, "invocation_count", invocation_count)
        object.__setattr__(
            self,
            "draft_generation_count",
            draft_generation_count,
        )

        if self.failure_code is not None and not isinstance(
            self.failure_code,
            CognitiveFailureCode,
        ):
            raise ValueError("cognitive_runtime_failure_code_invalid")
        if (
            self.publication_disposition is not None
            and self.publication_disposition
            not in _PUBLICATION_DISPOSITIONS
        ):
            raise ValueError("cognitive_runtime_publication_invalid")
        if (
            self.contract_version
            != D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION
        ):
            raise ValueError("cognitive_runtime_contract_version_invalid")

        outcome_values = (
            self.context_snapshot_digest,
            self.adapter_id,
            self.model_id,
            self.profile_id,
            self.revision_count,
            self.invocation_count,
            self.draft_generation_count,
            self.failure_code,
            self.publication_disposition,
        )
        if self.terminal_state is None:
            if any(value is not None for value in outcome_values):
                raise ValueError("cognitive_runtime_nonterminal_payload_invalid")
            return

        if self.selected_lane != "cognitive":
            raise ValueError("cognitive_runtime_legacy_terminal_invalid")
        if (
            self.revision_count is None
            or self.invocation_count is None
            or self.draft_generation_count is None
        ):
            raise ValueError("cognitive_runtime_terminal_counts_required")

        if self.terminal_state is CognitiveTurnState.COMPLETED:
            if (
                self.failure_code is not None
                or self.publication_disposition != "eligible"
            ):
                raise ValueError("cognitive_runtime_completed_invalid")
        elif self.terminal_state is CognitiveTurnState.INSUFFICIENT:
            if (
                self.failure_code
                is not CognitiveFailureCode.INSUFFICIENT_EVIDENCE
                or self.publication_disposition
                != "bounded_insufficiency_only"
            ):
                raise ValueError("cognitive_runtime_insufficient_invalid")
        elif self.terminal_state is CognitiveTurnState.FAILED:
            if (
                not isinstance(self.failure_code, CognitiveFailureCode)
                or self.publication_disposition is not None
            ):
                raise ValueError("cognitive_runtime_failed_invalid")
        else:
            raise ValueError("cognitive_runtime_terminal_state_invalid")


__all__ = [
    "D140_COGNITIVE_RUNTIME_ADOPTION_CONTRACT_VERSION",
    "CognitiveRuntimeLane",
    "CognitiveRuntimeObservation",
]
