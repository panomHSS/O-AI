"""D126 immutable Cognitive Brain constitution and core data contracts.

These contracts are provider-neutral metadata only. They grant no
authentication, authorization, approval, routing, credential, connector,
model, profile, memory-mutation, or execution authority.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId


COGNITIVE_ID_MAX_BYTES = 512
COGNITIVE_ARTIFACT_TYPE_MAX_BYTES = 128
COGNITIVE_CONTRACT_VERSION_MAX_BYTES = 128
COGNITIVE_REFERENCE_DIGEST_MAX_COUNT = 64
COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT = 128
COGNITIVE_REVISION_COUNT_MAX = 1
SHA256_HEX_LENGTH = 64
COGNITIVE_TASK_SEMANTICS_VERSION = "o-ai.cognitive-task-semantics.v1"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class CognitiveOrgan(Enum):
    """The exact 17 frozen Cognitive Brain V1 organ identities."""

    SELF_IDENTITY = "self_identity"
    PERCEPTION = "perception"
    ATTENTION = "attention"
    TASK_UNDERSTANDING = "task_understanding"
    WORKING_MEMORY = "working_memory"
    MEMORY_RETRIEVAL = "memory_retrieval"
    CONTEXT_INTELLIGENCE = "context_intelligence"
    REASONING = "reasoning"
    PREDICTION = "prediction"
    COGNITIVE_PLANNING = "cognitive_planning"
    DECISION_GOAL = "decision_goal"
    VERIFICATION_CRITIC = "verification_critic"
    METACOGNITION = "metacognition"
    MODEL_INTELLIGENCE = "model_intelligence"
    EXPERIENCE_SYSTEM = "experience_system"
    COMMUNICATION_RESPONSE = "communication_response"
    COGNITIVE_EXECUTIVE = "cognitive_executive"


class CognitiveOrganStatus(Enum):
    """One organ's exact non-authoritative result status for one turn."""

    READY = "ready"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT = "insufficient"
    FAILED = "failed"


class CognitiveTurnState(Enum):
    """Frozen Cognitive Brain V1 lifecycle vocabulary."""

    RECEIVED = "received"
    ACCEPTED = "accepted"
    COGNITIVE_LANE = "cognitive_lane"
    BOUND = "bound"
    CONTEXT_RESOLVING = "context_resolving"
    CONTEXT_FROZEN = "context_frozen"
    THINKING = "thinking"
    MODEL_READY = "model_ready"
    GENERATING = "generating"
    VERIFYING = "verifying"
    REVISING = "revising"
    FINALIZING = "finalizing"
    PERSISTING = "persisting"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT = "insufficient"


class CognitiveInvocationPurpose(Enum):
    """Server-owned bounded AI invocation purposes; never routing authority."""

    PRIMARY_SYNTHESIS = "primary_synthesis"
    CRITIC = "critic"
    REVISION = "revision"
    POST_REVISION_CRITIC = "post_revision_critic"


class CognitiveFailureCode(Enum):
    """Small Architecture-level safe failure vocabulary."""

    TURN_IN_PROGRESS = "turn_in_progress"
    TURN_DEADLINE_EXCEEDED = "turn_deadline_exceeded"
    CONTEXT_UNSTABLE = "context_unstable"
    INVALID_COGNITION = "invalid_cognition"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CRITIC_UNAVAILABLE = "critic_unavailable"
    STALE_LATE_RESULT = "stale_late_result"
    CONTRACT_VIOLATION = "contract_violation"


_TERMINAL_TURN_STATES = frozenset(
    {
        CognitiveTurnState.COMPLETED,
        CognitiveTurnState.FAILED,
        CognitiveTurnState.INSUFFICIENT,
    }
)


def _validate_identifier(
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


def _validate_optional_identifier(
    value: object,
    *,
    code: str,
    max_bytes: int = COGNITIVE_ID_MAX_BYTES,
) -> str | None:
    if value is None:
        return None
    return _validate_identifier(value, code=code, max_bytes=max_bytes)


def _validate_digest(value: object, *, code: str) -> str:
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _validate_optional_digest(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _validate_digest(value, code=code)


def _normalize_digest_sequence(
    value: object,
    *,
    code: str,
    max_count: int,
) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
    ):
        raise ValueError(code)
    if len(value) > max_count:
        raise ValueError(code)

    items = tuple(value)
    validated: list[str] = []
    seen: set[str] = set()
    for item in items:
        digest = _validate_digest(item, code=code)
        if digest in seen:
            raise ValueError(code)
        seen.add(digest)
        validated.append(digest)
    return tuple(validated)


def is_terminal_cognitive_turn_state(state: object) -> bool:
    """Return true only for the three exact terminal D126 turn states."""

    if not isinstance(state, CognitiveTurnState):
        raise ValueError("cognitive_turn_state_invalid")
    return state in _TERMINAL_TURN_STATES


@dataclass(frozen=True, slots=True)
class CognitiveArtifactEnvelope:
    """Immutable provenance envelope for one cross-organ cognitive artifact."""

    turn_id: str
    artifact_type: str
    contract_version: str
    producer_organ: CognitiveOrgan
    workspace_id: WorkspaceId
    context_snapshot_digest: str | None
    created_at: datetime
    status: CognitiveOrganStatus
    input_reference_digests: tuple[str, ...] | Sequence[str] = ()
    model_binding_reference: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(
            self.turn_id,
            code="cognitive_turn_id_invalid",
            max_bytes=COGNITIVE_ID_MAX_BYTES,
        )
        _validate_identifier(
            self.artifact_type,
            code="cognitive_artifact_type_invalid",
            max_bytes=COGNITIVE_ARTIFACT_TYPE_MAX_BYTES,
        )
        _validate_identifier(
            self.contract_version,
            code="cognitive_contract_version_invalid",
            max_bytes=COGNITIVE_CONTRACT_VERSION_MAX_BYTES,
        )
        if not isinstance(self.producer_organ, CognitiveOrgan):
            raise ValueError("cognitive_organ_invalid")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")

        _validate_optional_digest(
            self.context_snapshot_digest,
            code="context_snapshot_digest_invalid",
        )

        if type(self.created_at) is not datetime:
            raise ValueError("cognitive_created_at_invalid")
        try:
            offset = self.created_at.utcoffset()
        except Exception:
            raise ValueError("cognitive_created_at_invalid") from None
        if self.created_at.tzinfo is None or offset is None:
            raise ValueError("cognitive_created_at_invalid")
        try:
            created_at_utc = self.created_at.astimezone(timezone.utc)
        except Exception:
            raise ValueError("cognitive_created_at_invalid") from None
        object.__setattr__(self, "created_at", created_at_utc)

        if not isinstance(self.status, CognitiveOrganStatus):
            raise ValueError("cognitive_organ_status_invalid")

        input_reference_digests = _normalize_digest_sequence(
            self.input_reference_digests,
            code="cognitive_input_reference_digests_invalid",
            max_count=COGNITIVE_REFERENCE_DIGEST_MAX_COUNT,
        )
        object.__setattr__(
            self,
            "input_reference_digests",
            input_reference_digests,
        )

        _validate_optional_digest(
            self.model_binding_reference,
            code="cognitive_model_binding_reference_invalid",
        )


@dataclass(frozen=True, slots=True)
class CognitiveTurnManifest:
    """Immutable safe metadata for one Cognitive Turn; never authorization."""

    turn_id: str
    workspace_id: WorkspaceId
    conversation_id: str
    task_semantics_version: str = COGNITIVE_TASK_SEMANTICS_VERSION
    project_id: str | None = None
    terminal_state: CognitiveTurnState | None = None
    context_snapshot_digest: str | None = None
    authoritative_ai_task_kind: AITaskKind | None = None
    authorized_adapter_id: str | None = None
    authorized_model_id: str | None = None
    authorized_profile_id: str | None = None
    revision_count: int = 0
    failure_code: CognitiveFailureCode | None = None
    artifact_digests: tuple[str, ...] | Sequence[str] = ()

    def __post_init__(self) -> None:
        _validate_identifier(
            self.turn_id,
            code="cognitive_turn_id_invalid",
            max_bytes=COGNITIVE_ID_MAX_BYTES,
        )
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        _validate_identifier(
            self.conversation_id,
            code="cognitive_conversation_id_invalid",
            max_bytes=COGNITIVE_ID_MAX_BYTES,
        )
        if self.task_semantics_version != COGNITIVE_TASK_SEMANTICS_VERSION:
            raise ValueError("cognitive_task_semantics_version_invalid")

        _validate_optional_identifier(
            self.project_id,
            code="cognitive_project_id_invalid",
        )

        if self.terminal_state is not None:
            if not isinstance(self.terminal_state, CognitiveTurnState):
                raise ValueError("cognitive_terminal_state_invalid")
            if not is_terminal_cognitive_turn_state(self.terminal_state):
                raise ValueError("cognitive_terminal_state_invalid")

        _validate_optional_digest(
            self.context_snapshot_digest,
            code="context_snapshot_digest_invalid",
        )

        if (
            self.authoritative_ai_task_kind is not None
            and not isinstance(self.authoritative_ai_task_kind, AITaskKind)
        ):
            raise ValueError("invalid_task_kind")

        _validate_optional_identifier(
            self.authorized_adapter_id,
            code="cognitive_authorized_adapter_id_invalid",
        )
        _validate_optional_identifier(
            self.authorized_model_id,
            code="cognitive_authorized_model_id_invalid",
        )
        _validate_optional_identifier(
            self.authorized_profile_id,
            code="cognitive_authorized_profile_id_invalid",
        )

        if (
            type(self.revision_count) is not int
            or self.revision_count < 0
            or self.revision_count > COGNITIVE_REVISION_COUNT_MAX
        ):
            raise ValueError("cognitive_revision_count_invalid")

        if self.failure_code is not None and not isinstance(
            self.failure_code,
            CognitiveFailureCode,
        ):
            raise ValueError("cognitive_failure_code_invalid")

        if (
            self.terminal_state is CognitiveTurnState.COMPLETED
            and self.failure_code is not None
        ):
            raise ValueError("cognitive_completed_failure_invalid")
        if (
            self.terminal_state is CognitiveTurnState.FAILED
            and self.failure_code is None
        ):
            raise ValueError("cognitive_failed_reason_required")

        artifact_digests = _normalize_digest_sequence(
            self.artifact_digests,
            code="cognitive_artifact_digests_invalid",
            max_count=COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT,
        )
        object.__setattr__(self, "artifact_digests", artifact_digests)


__all__ = [
    "COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT",
    "COGNITIVE_ARTIFACT_TYPE_MAX_BYTES",
    "COGNITIVE_CONTRACT_VERSION_MAX_BYTES",
    "COGNITIVE_ID_MAX_BYTES",
    "COGNITIVE_REFERENCE_DIGEST_MAX_COUNT",
    "COGNITIVE_REVISION_COUNT_MAX",
    "COGNITIVE_TASK_SEMANTICS_VERSION",
    "SHA256_HEX_LENGTH",
    "CognitiveArtifactEnvelope",
    "CognitiveFailureCode",
    "CognitiveInvocationPurpose",
    "CognitiveOrgan",
    "CognitiveOrganStatus",
    "CognitiveTurnManifest",
    "CognitiveTurnState",
    "is_terminal_cognitive_turn_state",
]
