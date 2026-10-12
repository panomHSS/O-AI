import ast
import inspect
import sqlite3
import socket
from dataclasses import fields
from datetime import datetime, timezone

import pytest

import app.contracts.cognitive_brain as cognitive_brain
from app.contracts.cognitive_brain import (
    COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT,
    COGNITIVE_ID_MAX_BYTES,
    COGNITIVE_REFERENCE_DIGEST_MAX_COUNT,
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


@pytest.mark.parametrize(
    "enum_type, bad_value",
    [
        (CognitiveOrgan, "arbitrary"),
        (CognitiveOrgan, "SELF_IDENTITY"),
        (CognitiveOrganStatus, "READY"),
        (CognitiveTurnState, "COMPLETED"),
        (CognitiveInvocationPurpose, "PRIMARY_SYNTHESIS"),
        (CognitiveFailureCode, "CONTRACT_VIOLATION"),
    ],
)
def test_unknown_or_wrong_case_enum_values_fail_closed(enum_type, bad_value):
    with pytest.raises(ValueError):
        enum_type(bad_value)


def test_terminal_helper_rejects_raw_string():
    with pytest.raises(ValueError, match="cognitive_turn_state_invalid"):
        is_terminal_cognitive_turn_state("completed")


def test_envelope_rejects_raw_workspace_string():
    with pytest.raises(ValueError, match="workspace_id_invalid"):
        envelope(workspace_id="personal")


@pytest.mark.parametrize("turn_id", ["", " turn", "turn ", "turn\x00bad"])
def test_invalid_turn_identifier_fails_closed(turn_id):
    with pytest.raises(ValueError, match="cognitive_turn_id_invalid"):
        envelope(turn_id=turn_id)


def test_oversized_identifier_fails_closed():
    with pytest.raises(ValueError, match="cognitive_turn_id_invalid"):
        envelope(turn_id="x" * (COGNITIVE_ID_MAX_BYTES + 1))


@pytest.mark.parametrize(
    "digest",
    [
        "A" * 64,
        "1" * 63,
        "1" * 65,
        "g" * 64,
        "",
    ],
)
def test_invalid_digest_forms_fail_closed(digest):
    with pytest.raises(ValueError, match="context_snapshot_digest_invalid"):
        envelope(context_snapshot_digest=digest)


def test_duplicate_reference_digests_fail_closed():
    with pytest.raises(ValueError, match="cognitive_input_reference_digests_invalid"):
        envelope(input_reference_digests=[D1, D1])


def test_too_many_reference_digests_fail_closed():
    values = [f"{index:064x}" for index in range(
        COGNITIVE_REFERENCE_DIGEST_MAX_COUNT + 1
    )]
    with pytest.raises(ValueError, match="cognitive_input_reference_digests_invalid"):
        envelope(input_reference_digests=values)


def test_naive_datetime_fails_closed():
    with pytest.raises(ValueError, match="cognitive_created_at_invalid"):
        envelope(created_at=datetime(2026, 10, 12, 12, 0))


@pytest.mark.parametrize(
    "state",
    [
        CognitiveTurnState.RECEIVED,
        CognitiveTurnState.CONTEXT_FROZEN,
        CognitiveTurnState.VERIFYING,
    ],
)
def test_manifest_rejects_non_terminal_value_in_terminal_state(state):
    with pytest.raises(ValueError, match="cognitive_terminal_state_invalid"):
        manifest(terminal_state=state)


def test_completed_manifest_rejects_failure_code():
    with pytest.raises(ValueError, match="cognitive_completed_failure_invalid"):
        manifest(
            terminal_state=CognitiveTurnState.COMPLETED,
            failure_code=CognitiveFailureCode.CONTRACT_VIOLATION,
        )


def test_failed_manifest_requires_failure_code():
    with pytest.raises(ValueError, match="cognitive_failed_reason_required"):
        manifest(terminal_state=CognitiveTurnState.FAILED)


@pytest.mark.parametrize("revision_count", [True, -1, 2])
def test_manifest_rejects_invalid_revision_count(revision_count):
    with pytest.raises(ValueError, match="cognitive_revision_count_invalid"):
        manifest(revision_count=revision_count)


def test_manifest_rejects_raw_or_richer_cognitive_task_as_authoritative_kind():
    for value in ("general_chat", "troubleshooting", "architecture_analysis"):
        with pytest.raises(ValueError, match="invalid_task_kind"):
            manifest(authoritative_ai_task_kind=value)


def test_manifest_rejects_non_v1_task_semantics_version():
    with pytest.raises(ValueError, match="cognitive_task_semantics_version_invalid"):
        manifest(task_semantics_version="o-ai.cognitive-task-semantics.v2")


def test_insufficient_state_does_not_overfreeze_failure_mapping():
    without_failure = manifest(terminal_state=CognitiveTurnState.INSUFFICIENT)
    with_failure = manifest(
        terminal_state=CognitiveTurnState.INSUFFICIENT,
        failure_code=CognitiveFailureCode.INSUFFICIENT_EVIDENCE,
    )
    assert without_failure.failure_code is None
    assert with_failure.failure_code is CognitiveFailureCode.INSUFFICIENT_EVIDENCE


def test_too_many_artifact_digests_fail_closed():
    values = [
        f"{index:064x}"
        for index in range(COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT + 1)
    ]
    with pytest.raises(ValueError, match="cognitive_artifact_digests_invalid"):
        manifest(artifact_digests=values)


def test_model_binding_reference_is_digest_only_not_authorization_object():
    class ForgedAuthorization:
        pass

    with pytest.raises(
        ValueError,
        match="cognitive_model_binding_reference_invalid",
    ):
        envelope(model_binding_reference=ForgedAuthorization())


def test_contract_fields_expose_no_authority_secret_or_raw_reasoning_surface():
    forbidden = {
        "owner_approval",
        "execution_authorization",
        "execution_plan",
        "api_key",
        "credential",
        "provider_secret",
        "raw_prompt",
        "system_prompt",
        "hidden_reasoning",
        "raw_context",
        "memory_value",
        "tool_permission",
    }
    envelope_fields = {field.name for field in fields(CognitiveArtifactEnvelope)}
    manifest_fields = {field.name for field in fields(CognitiveTurnManifest)}
    assert forbidden.isdisjoint(envelope_fields)
    assert forbidden.isdisjoint(manifest_fields)


def test_contract_construction_does_not_call_network_or_database(monkeypatch):
    def forbidden_call(*args, **kwargs):
        raise AssertionError("external call attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden_call)
    monkeypatch.setattr(sqlite3, "connect", forbidden_call)

    assert envelope().producer_organ is CognitiveOrgan.REASONING
    assert manifest(
        authoritative_ai_task_kind=AITaskKind.GENERAL_CHAT
    ).task_semantics_version == COGNITIVE_TASK_SEMANTICS_VERSION


def test_contract_module_imports_only_contract_authority_neutral_app_modules():
    source = inspect.getsource(cognitive_brain)
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden_prefixes = (
        "app.services",
        "app.adapters",
        "app.repositories",
        "app.models",
        "app.db",
        "openai",
        "ollama",
        "httpx",
        "requests",
    )
    assert not any(
        name.startswith(forbidden_prefixes)
        for name in imported
    )
    assert "app.contracts.task_aware_ai_routing" in imported
    assert "app.contracts.workspace" in imported


def test_contract_module_defines_no_retry_or_fallback_operation():
    source = inspect.getsource(cognitive_brain)
    tree = ast.parse(source)
    function_names = {
        node.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not any("retry" in name or "fallback" in name for name in function_names)
