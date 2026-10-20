import ast
from dataclasses import fields
from pathlib import Path

import pytest

from app.contracts.cognitive_brain import CognitiveTurnState
from app.contracts.governed_action_runtime import GovernedActionRuntimeOutcome
from app.contracts.workspace import WorkspaceId
from app.services.governed_action_runtime import GovernedActionRuntimeIntegration
from tests.test_d167_governed_action_runtime import (
    action, build_runtime, command, outcome,
)

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("candidate", "cmd", "brain", "reason"),
    (
        (action(turn="other"), command(), outcome(), "source_turn_request_mismatch"),
        (action(), command("other"), outcome(), "source_turn_request_mismatch"),
        (action(), command(), outcome(turn="other"), "cognitive_turn_request_mismatch"),
        (action(), command(name="tool.execute"), outcome(), "source_command_not_cognitive_chat"),
    ),
)
def test_d167_turn_lineage_fails_before_approval(candidate, cmd, brain, reason):
    runtime, store = build_runtime()
    result = runtime.prepare(candidate, command=cmd, cognitive_outcome=brain)
    assert result.status == "intent_rejected"
    assert result.reason_code == reason
    assert result.preparation is None
    assert store.pending_count == 0


def test_d167_cross_workspace_fails_before_approval():
    runtime, store = build_runtime(WorkspaceId.PERSONAL)
    result = runtime.prepare(
        action(), command=command(),
        cognitive_outcome=outcome(workspace=WorkspaceId.COMPANY),
    )
    assert result.reason_code == "cognitive_workspace_mismatch"
    assert store.pending_count == 0


@pytest.mark.parametrize(
    ("candidate", "brain", "reason"),
    (
        (action(digest="b" * 64), outcome(), "source_artifact_mismatch"),
        (action(), outcome(stage="other"), "source_artifact_unavailable"),
        (
            action(),
            outcome(state=CognitiveTurnState.VERIFYING),
            "source_artifact_unavailable",
        ),
        (
            action(),
            outcome(duplicate=True),
            "source_artifact_unavailable",
        ),
    ),
)
def test_d167_final_artifact_lineage_is_exact(candidate, brain, reason):
    runtime, store = build_runtime()
    result = runtime.prepare(candidate, command=command(), cognitive_outcome=brain)
    assert result.reason_code == reason
    assert result.preparation is None
    assert store.pending_count == 0


@pytest.mark.parametrize(
    "terminal",
    (CognitiveTurnState.FAILED, CognitiveTurnState.INSUFFICIENT),
)
def test_d167_noneligible_cognition_cannot_prepare(terminal):
    runtime, store = build_runtime()
    result = runtime.prepare(
        action(), command=command(),
        cognitive_outcome=outcome(terminal=terminal, digest=None),
    )
    assert result.reason_code == "cognitive_outcome_not_action_eligible"
    assert store.pending_count == 0


def test_d167_contract_and_service_have_no_authority_surface():
    names = {f.name for f in fields(GovernedActionRuntimeOutcome)}
    assert names == {"status", "reason_code", "intent_digest", "preparation"}
    assert names.isdisjoint({
        "owner_approval", "permission", "execution_authorization",
        "execute_now", "retry", "rollback",
    })
    for forbidden in ("execute", "approve", "deny", "retry", "rollback"):
        assert not hasattr(GovernedActionRuntimeIntegration, forbidden)


def test_d167_has_no_parser_runtime_provider_connector_or_persistence():
    path = "backend/app/services/governed_action_runtime.py"
    tree = ast.parse(source(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    for prefix in (
        "app.providers", "app.connectors", "app.repositories", "app.models",
        "sqlalchemy", "subprocess", "requests", "httpx", "urllib",
        "playwright", "selenium", "pyautogui", "re",
    ):
        assert not any(m == prefix or m.startswith(prefix + ".") for m in modules)

    text = source(path)
    for token in (
        "ToolRuntime", "ModuleRuntime", "CommandExecutionCoordinator",
        "ExecutionAuthorization", "OwnerApprovalEvidence",
        ".execute(", ".approve(", ".deny(", "OpenAI", "regex",
    ):
        assert token not in text


def test_d167_brain_is_not_modified_into_an_executor():
    executive = source("backend/app/services/cognitive_executive.py")
    planning = source("backend/app/contracts/cognitive_planning_decision_goal.py")
    for token in (
        "GovernedActionRuntimeIntegration", "GovernedActionBoundary",
        "ExecutionApprovalService", "ToolRuntime", "ModuleRuntime",
        "OwnerApprovalEvidence",
    ):
        assert token not in executive
        assert token not in planning


def test_d167_production_composition_reuses_existing_services():
    text = source("backend/app/api/dependencies.py")
    for token in (
        "def get_governed_action_boundary(",
        "get_capability_permission_policy",
        "get_execution_approval_service",
        "def get_governed_action_runtime_integration(",
        "workspace_scope: WorkspaceScope = Depends(get_workspace_scope)",
    ):
        assert token in text
    for token in ("BrainExecutionEngine", "HandsRuntimeV2", "HandsGuardV2"):
        assert token not in text


def test_d167_adds_no_api_model_repo_frontend_or_migration():
    forbidden = (
        "backend/app/models/governed_action_runtime.py",
        "backend/app/repositories/governed_action_runtime.py",
        "backend/app/api/v1/governed_action_runtime.py",
        "backend/app/schemas/governed_action_runtime.py",
        "frontend/components/governed-action-runtime.tsx",
        "backend/alembic/versions/0017_governed_action_runtime.py",
    )
    assert all(not (ROOT / p).exists() for p in forbidden)
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(p.name.startswith("0017_") for p in versions.glob("*.py"))


def test_d167_spec_preserves_frozen_limits():
    text = source("docs/specs/D167_GOVERNED_BRAIN_HANDS_RUNTIME_INTEGRATION_V1.md")
    for marker in (
        "DECISION != PERMISSION != EXECUTION",
        "no_action_intent",
        "prepared_for_owner_review",
        "D167 never reaches `ToolRuntime` or `ModuleRuntime` directly.",
        "does not make normal Chat infer tools from free text",
        "no new hand/tool/module/connector capability",
        "does not automatically invoke the seam from normal Chat",
        "does not mean that Brain can autonomously select tools",
    ):
        assert marker in text
