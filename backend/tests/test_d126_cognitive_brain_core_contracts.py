from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from app.contracts.cognitive_brain import (
    COGNITIVE_TASK_SEMANTICS_VERSION,
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveInvocationPurpose,
    CognitiveOrgan,
    CognitiveOrganStatus,
    CognitiveTurnManifest,
    CognitiveTurnState,
    is_terminal_cognitive_turn_state,
)
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.workspace import WorkspaceId


D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def envelope(**changes):
    values = dict(
        turn_id="turn-1",
        artifact_type="reasoning",
        contract_version="o-ai.reasoning.v1",
        producer_organ=CognitiveOrgan.REASONING,
        workspace_id=WorkspaceId.PERSONAL,
        context_snapshot_digest=None,
        created_at=datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc),
        status=CognitiveOrganStatus.READY,
        input_reference_digests=(D1, D2),
        model_binding_reference=None,
    )
    values.update(changes)
    return CognitiveArtifactEnvelope(**values)


def manifest(**changes):
    values = dict(
        turn_id="turn-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id="conversation-1",
    )
    values.update(changes)
    return CognitiveTurnManifest(**values)


def test_frozen_enum_values_are_exact():
    assert [item.value for item in CognitiveOrgan] == [
        "self_identity",
        "perception",
        "attention",
        "task_understanding",
        "working_memory",
        "memory_retrieval",
        "context_intelligence",
        "reasoning",
        "prediction",
        "cognitive_planning",
        "decision_goal",
        "verification_critic",
        "metacognition",
        "model_intelligence",
        "experience_system",
        "communication_response",
        "cognitive_executive",
    ]
    assert [item.value for item in CognitiveOrganStatus] == [
        "ready",
        "not_applicable",
        "insufficient",
        "failed",
    ]
    assert [item.value for item in CognitiveTurnState] == [
        "received",
        "accepted",
        "cognitive_lane",
        "bound",
        "context_resolving",
        "context_frozen",
        "thinking",
        "model_ready",
        "generating",
        "verifying",
        "revising",
        "finalizing",
        "persisting",
        "completed",
        "failed",
        "insufficient",
    ]
    assert [item.value for item in CognitiveInvocationPurpose] == [
        "primary_synthesis",
        "critic",
        "revision",
        "post_revision_critic",
    ]
    assert [item.value for item in CognitiveFailureCode] == [
        "turn_in_progress",
        "turn_deadline_exceeded",
        "context_unstable",
        "invalid_cognition",
        "insufficient_evidence",
        "critic_unavailable",
        "stale_late_result",
        "contract_violation",
    ]


@pytest.mark.parametrize(
    "state, expected",
    [
        (CognitiveTurnState.RECEIVED, False),
        (CognitiveTurnState.PERSISTING, False),
        (CognitiveTurnState.COMPLETED, True),
        (CognitiveTurnState.FAILED, True),
        (CognitiveTurnState.INSUFFICIENT, True),
    ],
)
def test_terminal_state_helper(state, expected):
    assert is_terminal_cognitive_turn_state(state) is expected


@pytest.mark.parametrize("workspace", [WorkspaceId.PERSONAL, WorkspaceId.COMPANY])
def test_envelope_accepts_exact_workspace_identity(workspace):
    assert envelope(workspace_id=workspace).workspace_id is workspace


def test_envelope_allows_pre_freeze_absent_context_digest():
    assert envelope(context_snapshot_digest=None).context_snapshot_digest is None


def test_envelope_accepts_context_and_model_binding_digests():
    item = envelope(
        context_snapshot_digest=D1,
        model_binding_reference=D3,
    )
    assert item.context_snapshot_digest == D1
    assert item.model_binding_reference == D3


def test_envelope_normalizes_aware_datetime_to_utc():
    source = datetime(
        2026,
        10,
        12,
        19,
        30,
        tzinfo=timezone(timedelta(hours=7)),
    )
    item = envelope(created_at=source)
    assert item.created_at == datetime(
        2026,
        10,
        12,
        12,
        30,
        tzinfo=timezone.utc,
    )
    assert item.created_at.tzinfo is timezone.utc


def test_envelope_copies_digest_sequence_to_immutable_ordered_tuple():
    source = [D2, D1]
    item = envelope(input_reference_digests=source)
    source.append(D3)
    assert item.input_reference_digests == (D2, D1)
    assert isinstance(item.input_reference_digests, tuple)
    with pytest.raises(FrozenInstanceError):
        item.turn_id = "changed"


@pytest.mark.parametrize(
    "task_kind",
    [AITaskKind.GENERAL_CHAT, AITaskKind.SOFTWARE_ENGINEERING],
)
def test_manifest_reuses_exact_existing_ai_task_kind(task_kind):
    item = manifest(authoritative_ai_task_kind=task_kind)
    assert item.authoritative_ai_task_kind is task_kind
    assert type(item.authoritative_ai_task_kind) is AITaskKind


def test_manifest_task_semantics_version_is_exact_v1():
    item = manifest()
    assert item.task_semantics_version == COGNITIVE_TASK_SEMANTICS_VERSION
    assert item.task_semantics_version == "o-ai.cognitive-task-semantics.v1"


def test_manifest_completed_and_failed_terminal_rules():
    completed = manifest(terminal_state=CognitiveTurnState.COMPLETED)
    failed = manifest(
        terminal_state=CognitiveTurnState.FAILED,
        failure_code=CognitiveFailureCode.CONTRACT_VIOLATION,
    )
    assert completed.failure_code is None
    assert failed.failure_code is CognitiveFailureCode.CONTRACT_VIOLATION


@pytest.mark.parametrize("revision_count", [0, 1])
def test_manifest_accepts_frozen_revision_count_range(revision_count):
    assert manifest(revision_count=revision_count).revision_count == revision_count


def test_manifest_copies_artifact_digests_to_immutable_tuple():
    source = [D1, D2]
    item = manifest(artifact_digests=source)
    source.append(D3)
    assert item.artifact_digests == (D1, D2)
    assert isinstance(item.artifact_digests, tuple)


def test_contract_equality_is_deterministic_for_equal_values():
    left_envelope = envelope()
    right_envelope = envelope()
    left_manifest = manifest(artifact_digests=(D1,))
    right_manifest = manifest(artifact_digests=(D1,))
    assert left_envelope == right_envelope
    assert left_manifest == right_manifest
