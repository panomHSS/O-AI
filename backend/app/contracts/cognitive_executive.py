"""D136 immutable Cognitive Executive / Integrated Brain Runtime contracts.

These contracts carry bounded orchestration metadata only. They grant no
authentication, authorization, approval, routing, provider/model/profile
selection, persistence, tool, module, plugin, connector, or execution authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from app.contracts.cognitive_brain import (
    COGNITIVE_REVISION_COUNT_MAX,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnState,
    is_terminal_cognitive_turn_state,
)
from app.contracts.cognitive_verification import PublicationDisposition
from app.contracts.task_aware_ai_routing import AITaskKind


D136_EXECUTIVE_ARTIFACT_TYPE = "cognitive.executive_outcome"
D136_EXECUTIVE_CONTRACT_VERSION = "o-ai.cognitive-executive.v1"
D136_EXECUTIVE_TRACE_VERSION = "o-ai.cognitive-executive-trace.v1"
D136_INVOCATION_BINDING_VERSION = "o-ai.cognitive-invocation-binding.v1"

D136_MAX_MODEL_INVOCATIONS = 4
D136_MAX_DRAFT_GENERATIONS = 2
D136_MAX_TRACE_EVENTS = 64
D136_MAX_SAFE_REASON_CODES = 32

D136_TRACE_STAGE_MAX_BYTES = 128
D136_REASON_CODE_MAX_BYTES = 128
D136_IDENTIFIER_MAX_BYTES = 512

ExecutiveTraceDisposition: TypeAlias = str

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, *, code: str, max_bytes: int) -> str:
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


def _optional_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str | None:
    if value is None:
        return None
    return _text(value, code=code, max_bytes=max_bytes)


def _digest(value: object, *, code: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _optional_digest(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _digest(value, code=code)


def _finite_positive(value: object, *, code: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ValueError(code)
    return float(value)


@dataclass(frozen=True, slots=True)
class CognitiveTurnDeadline:
    """One server-owned monotonic turn deadline."""

    started_monotonic: float
    deadline_monotonic: float

    def __post_init__(self) -> None:
        started = _finite_positive(
            self.started_monotonic,
            code="cognitive_executive_deadline_invalid",
        )
        deadline = _finite_positive(
            self.deadline_monotonic,
            code="cognitive_executive_deadline_invalid",
        )
        if deadline <= started:
            raise ValueError("cognitive_executive_deadline_invalid")
        object.__setattr__(self, "started_monotonic", started)
        object.__setattr__(self, "deadline_monotonic", deadline)


@dataclass(frozen=True, slots=True)
class CognitiveInvocationBinding:
    """Safe metadata describing one independently authorized AI invocation."""

    purpose: CognitiveInvocationPurpose
    ordinal: int
    request_id: str
    adapter_id: str
    model_id: str
    profile_id: str | None
    task_kind: AITaskKind
    plan_digest: str
    binding_reference: str
    effective_timeout_seconds: float
    version: str = D136_INVOCATION_BINDING_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, CognitiveInvocationPurpose):
            raise ValueError("cognitive_invocation_purpose_invalid")
        if (
            type(self.ordinal) is not int
            or self.ordinal < 1
            or self.ordinal > D136_MAX_MODEL_INVOCATIONS
        ):
            raise ValueError("cognitive_invocation_ordinal_invalid")
        _text(
            self.request_id,
            code="cognitive_invocation_request_id_invalid",
            max_bytes=D136_IDENTIFIER_MAX_BYTES,
        )
        _text(
            self.adapter_id,
            code="cognitive_invocation_adapter_id_invalid",
            max_bytes=D136_IDENTIFIER_MAX_BYTES,
        )
        _text(
            self.model_id,
            code="cognitive_invocation_model_id_invalid",
            max_bytes=D136_IDENTIFIER_MAX_BYTES,
        )
        _optional_text(
            self.profile_id,
            code="cognitive_invocation_profile_id_invalid",
            max_bytes=D136_IDENTIFIER_MAX_BYTES,
        )
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("cognitive_invocation_task_kind_invalid")
        _digest(
            self.plan_digest,
            code="cognitive_invocation_plan_digest_invalid",
        )
        _digest(
            self.binding_reference,
            code="cognitive_invocation_binding_reference_invalid",
        )
        timeout = _finite_positive(
            self.effective_timeout_seconds,
            code="cognitive_invocation_timeout_invalid",
        )
        if timeout > 600:
            raise ValueError("cognitive_invocation_timeout_invalid")
        object.__setattr__(self, "effective_timeout_seconds", timeout)
        if self.version != D136_INVOCATION_BINDING_VERSION:
            raise ValueError("cognitive_invocation_binding_version_invalid")


def compute_cognitive_invocation_binding_reference(
    *,
    purpose: CognitiveInvocationPurpose,
    ordinal: int,
    request_id: str,
    adapter_id: str,
    model_id: str,
    profile_id: str | None,
    task_kind: AITaskKind,
    plan_digest: str,
) -> str:
    """Hash one safe authorized binding description."""

    if not isinstance(purpose, CognitiveInvocationPurpose):
        raise ValueError("cognitive_invocation_purpose_invalid")
    if type(ordinal) is not int or not 1 <= ordinal <= D136_MAX_MODEL_INVOCATIONS:
        raise ValueError("cognitive_invocation_ordinal_invalid")
    request_id = _text(
        request_id,
        code="cognitive_invocation_request_id_invalid",
        max_bytes=D136_IDENTIFIER_MAX_BYTES,
    )
    adapter_id = _text(
        adapter_id,
        code="cognitive_invocation_adapter_id_invalid",
        max_bytes=D136_IDENTIFIER_MAX_BYTES,
    )
    model_id = _text(
        model_id,
        code="cognitive_invocation_model_id_invalid",
        max_bytes=D136_IDENTIFIER_MAX_BYTES,
    )
    profile_id = _optional_text(
        profile_id,
        code="cognitive_invocation_profile_id_invalid",
        max_bytes=D136_IDENTIFIER_MAX_BYTES,
    )
    if not isinstance(task_kind, AITaskKind):
        raise ValueError("cognitive_invocation_task_kind_invalid")
    plan_digest = _digest(
        plan_digest,
        code="cognitive_invocation_plan_digest_invalid",
    )
    payload = {
        "adapter_id": adapter_id,
        "model_id": model_id,
        "ordinal": ordinal,
        "plan_digest": plan_digest,
        "profile_id": profile_id,
        "purpose": purpose.value,
        "request_id": request_id,
        "task_kind": task_kind.value,
        "version": D136_INVOCATION_BINDING_VERSION,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CognitiveExecutiveTraceEvent:
    """One bounded safe lifecycle event; never raw prompt or chain-of-thought."""

    sequence: int
    state: CognitiveTurnState
    stage: str
    status: CognitiveOrganStatus
    reason_code: str | None = None
    invocation_purpose: CognitiveInvocationPurpose | None = None
    invocation_ordinal: int | None = None
    artifact_digest: str | None = None
    trace_version: str = D136_EXECUTIVE_TRACE_VERSION

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int
            or self.sequence < 1
            or self.sequence > D136_MAX_TRACE_EVENTS
        ):
            raise ValueError("cognitive_executive_trace_sequence_invalid")
        if not isinstance(self.state, CognitiveTurnState):
            raise ValueError("cognitive_executive_trace_state_invalid")
        _text(
            self.stage,
            code="cognitive_executive_trace_stage_invalid",
            max_bytes=D136_TRACE_STAGE_MAX_BYTES,
        )
        if not isinstance(self.status, CognitiveOrganStatus):
            raise ValueError("cognitive_executive_trace_status_invalid")
        _optional_text(
            self.reason_code,
            code="cognitive_executive_trace_reason_invalid",
            max_bytes=D136_REASON_CODE_MAX_BYTES,
        )
        if self.invocation_purpose is not None and not isinstance(
            self.invocation_purpose,
            CognitiveInvocationPurpose,
        ):
            raise ValueError("cognitive_executive_trace_purpose_invalid")
        if self.invocation_ordinal is not None and (
            type(self.invocation_ordinal) is not int
            or not 1 <= self.invocation_ordinal <= D136_MAX_MODEL_INVOCATIONS
        ):
            raise ValueError("cognitive_executive_trace_ordinal_invalid")
        if (self.invocation_purpose is None) != (
            self.invocation_ordinal is None
        ):
            raise ValueError("cognitive_executive_trace_invocation_pair_invalid")
        _optional_digest(
            self.artifact_digest,
            code="cognitive_executive_trace_digest_invalid",
        )
        if self.trace_version != D136_EXECUTIVE_TRACE_VERSION:
            raise ValueError("cognitive_executive_trace_version_invalid")


@dataclass(frozen=True, slots=True)
class CognitiveExecutiveOutcome:
    """Immutable terminal D136 orchestration outcome."""

    envelope: CognitiveArtifactEnvelope
    terminal_state: CognitiveTurnState
    failure_code: CognitiveFailureCode | None
    revision_count: int
    invocation_count: int
    draft_generation_count: int
    publication_disposition: PublicationDisposition | None
    trace: tuple[CognitiveExecutiveTraceEvent, ...] | Sequence[CognitiveExecutiveTraceEvent]
    bindings: tuple[CognitiveInvocationBinding, ...] | Sequence[CognitiveInvocationBinding]

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, CognitiveArtifactEnvelope):
            raise ValueError("cognitive_executive_envelope_invalid")
        if (
            self.envelope.producer_organ is not CognitiveOrgan.COGNITIVE_EXECUTIVE
            or self.envelope.artifact_type != D136_EXECUTIVE_ARTIFACT_TYPE
            or self.envelope.contract_version != D136_EXECUTIVE_CONTRACT_VERSION
            or self.envelope.model_binding_reference is not None
        ):
            raise ValueError("cognitive_executive_envelope_invalid")
        if not isinstance(self.terminal_state, CognitiveTurnState):
            raise ValueError("cognitive_executive_terminal_state_invalid")
        if not is_terminal_cognitive_turn_state(self.terminal_state):
            raise ValueError("cognitive_executive_terminal_state_invalid")

        expected_status = {
            CognitiveTurnState.COMPLETED: CognitiveOrganStatus.READY,
            CognitiveTurnState.INSUFFICIENT: CognitiveOrganStatus.INSUFFICIENT,
            CognitiveTurnState.FAILED: CognitiveOrganStatus.FAILED,
        }[self.terminal_state]
        if self.envelope.status is not expected_status:
            raise ValueError("cognitive_executive_status_invalid")
        if self.terminal_state in {
            CognitiveTurnState.COMPLETED,
            CognitiveTurnState.INSUFFICIENT,
        } and self.envelope.context_snapshot_digest is None:
            raise ValueError("cognitive_executive_context_digest_required")
        if self.terminal_state is CognitiveTurnState.COMPLETED:
            if self.failure_code is not None:
                raise ValueError("cognitive_executive_failure_invalid")
            if self.publication_disposition != "eligible":
                raise ValueError("cognitive_executive_publication_invalid")
        elif self.terminal_state is CognitiveTurnState.INSUFFICIENT:
            if self.failure_code is not CognitiveFailureCode.INSUFFICIENT_EVIDENCE:
                raise ValueError("cognitive_executive_failure_invalid")
            if self.publication_disposition != "bounded_insufficiency_only":
                raise ValueError("cognitive_executive_publication_invalid")
        else:
            if not isinstance(self.failure_code, CognitiveFailureCode):
                raise ValueError("cognitive_executive_failure_invalid")

        if (
            type(self.revision_count) is not int
            or not 0 <= self.revision_count <= COGNITIVE_REVISION_COUNT_MAX
        ):
            raise ValueError("cognitive_executive_revision_count_invalid")
        if (
            type(self.invocation_count) is not int
            or not 0 <= self.invocation_count <= D136_MAX_MODEL_INVOCATIONS
        ):
            raise ValueError("cognitive_executive_invocation_count_invalid")
        if (
            type(self.draft_generation_count) is not int
            or not 0 <= self.draft_generation_count <= D136_MAX_DRAFT_GENERATIONS
        ):
            raise ValueError("cognitive_executive_draft_generation_count_invalid")

        if isinstance(self.trace, (str, bytes, bytearray)) or not isinstance(
            self.trace, Sequence
        ):
            raise ValueError("cognitive_executive_trace_invalid")
        trace = tuple(self.trace)
        if not trace or len(trace) > D136_MAX_TRACE_EVENTS:
            raise ValueError("cognitive_executive_trace_invalid")
        if any(
            not isinstance(item, CognitiveExecutiveTraceEvent)
            or item.sequence != index
            for index, item in enumerate(trace, start=1)
        ):
            raise ValueError("cognitive_executive_trace_invalid")
        reason_codes = tuple(
            item.reason_code for item in trace if item.reason_code is not None
        )
        if len(set(reason_codes)) > D136_MAX_SAFE_REASON_CODES:
            raise ValueError("cognitive_executive_reason_codes_invalid")

        if isinstance(self.bindings, (str, bytes, bytearray)) or not isinstance(
            self.bindings, Sequence
        ):
            raise ValueError("cognitive_executive_bindings_invalid")
        bindings = tuple(self.bindings)
        if len(bindings) != self.invocation_count:
            raise ValueError("cognitive_executive_bindings_invalid")
        if any(
            not isinstance(item, CognitiveInvocationBinding)
            or item.ordinal != index
            for index, item in enumerate(bindings, start=1)
        ):
            raise ValueError("cognitive_executive_bindings_invalid")
        if len({item.purpose for item in bindings}) != len(bindings):
            raise ValueError("cognitive_executive_duplicate_purpose")
        if self.draft_generation_count > 0 and (
            not bindings
            and self.terminal_state is CognitiveTurnState.COMPLETED
        ):
            raise ValueError("cognitive_executive_generation_binding_invalid")

        object.__setattr__(self, "trace", trace)
        object.__setattr__(self, "bindings", bindings)


__all__ = [
    "D136_EXECUTIVE_ARTIFACT_TYPE",
    "D136_EXECUTIVE_CONTRACT_VERSION",
    "D136_EXECUTIVE_TRACE_VERSION",
    "D136_INVOCATION_BINDING_VERSION",
    "D136_MAX_DRAFT_GENERATIONS",
    "D136_MAX_MODEL_INVOCATIONS",
    "D136_MAX_SAFE_REASON_CODES",
    "D136_MAX_TRACE_EVENTS",
    "CognitiveExecutiveOutcome",
    "CognitiveExecutiveTraceEvent",
    "CognitiveInvocationBinding",
    "CognitiveTurnDeadline",
    "compute_cognitive_invocation_binding_reference",
]
