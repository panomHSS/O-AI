from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.governed_action import ActionIntent, RecoveryState
from app.services.governed_action import GovernedActionBoundary


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"
SPEC = ROOT / "docs/specs/D166_GOVERNED_BRAIN_HANDS_ACTION_BOUNDARY_V1.md"


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def imports(relative: str) -> set[str]:
    tree = ast.parse(source(relative))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_d166_action_intent_has_no_authority_fields() -> None:
    names = {field.name for field in fields(ActionIntent)}
    assert names == {
        "source_turn_id",
        "source_artifact_digest",
        "target_kind",
        "adapter_id",
        "operation",
        "parameters",
    }
    assert names.isdisjoint(
        {
            "owner_approval",
            "approved_by_owner",
            "permission",
            "permission_decision",
            "execution_authorization",
            "execution_plan",
            "execute_now",
            "confirmation_bypass",
            "workspace_id",
        }
    )


def test_d166_boundary_has_no_execution_or_decision_authority_methods() -> None:
    for forbidden in (
        "execute",
        "approve",
        "deny",
        "retry",
        "rollback",
        "send",
        "run",
    ):
        assert not hasattr(GovernedActionBoundary, forbidden)


def test_d166_service_imports_no_runtime_connector_provider_or_persistence() -> None:
    modules = imports("backend/app/services/governed_action.py")
    forbidden_prefixes = (
        "app.providers",
        "app.connectors",
        "app.repositories",
        "app.models",
        "sqlalchemy",
        "subprocess",
        "requests",
        "httpx",
        "urllib",
        "playwright",
        "selenium",
        "pyautogui",
    )
    assert not any(
        module.startswith(forbidden_prefixes)
        for module in modules
    )

    text = source("backend/app/services/governed_action.py")
    for forbidden in (
        "ToolRuntime",
        "ModuleRuntime",
        "CommandExecutionCoordinator",
        ".execute(",
        ".approve(",
        ".deny(",
        "OpenAI",
        "Anthropic",
        "Gemini",
        "requests.",
        "httpx.",
        "urllib.request",
    ):
        assert forbidden not in text


def test_d166_contracts_grant_no_retry_or_rollback_authority() -> None:
    names = {field.name for field in fields(RecoveryState)}
    assert names == {
        "side_effect_state",
        "rollback_available",
        "disposition",
        "reason_code",
    }
    assert "retry" not in names
    assert "rollback_action" not in names
    assert "execute_rollback" not in names


def test_d166_does_not_create_persistence_api_frontend_or_migration() -> None:
    forbidden = (
        APP / "models/governed_action.py",
        APP / "repositories/governed_action.py",
        APP / "api/v1/governed_action.py",
        ROOT / "frontend/components/governed-action.tsx",
        ROOT / "backend/alembic/versions/0017_governed_action.py",
    )
    assert all(not path.exists() for path in forbidden)

    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(
        path.name.startswith("0017_")
        for path in versions.glob("*.py")
    )


def test_d166_brain_still_has_no_execution_authority_surface() -> None:
    planning = source(
        "backend/app/contracts/cognitive_planning_decision_goal.py"
    )
    executive = source(
        "backend/app/services/cognitive_executive.py"
    )

    for forbidden in (
        "ExecutionAuthorization",
        "OwnerApprovalEvidence",
        "ToolRuntime",
        "ModuleRuntime",
        "ExecutionApprovalService",
        "GovernedActionBoundary",
    ):
        assert forbidden not in planning
        assert forbidden not in executive


def test_d166_nonconfirmation_policy_stops_before_approval_proposal() -> None:
    text = source("backend/app/services/governed_action.py")

    check = text.index("if not permission.owner_approval_required:")
    propose = text.index("self._approval_service.propose(")
    assert check < propose
    assert 'reason_code="structured_confirmation_not_required"' in text


def test_d166_existing_structured_approval_guard_is_preserved() -> None:
    bridge = source("backend/app/services/chat_action_bridge.py")

    assert "GMAIL_STRUCTURED_APPROVAL_REQUIRED_REPLY" in bridge
    assert "CALENDAR_STRUCTURED_APPROVAL_REQUIRED_REPLY" in bridge
    assert "process_pending_gmail_plaintext_approval" in bridge
    assert "process_pending_calendar_plaintext_approval" in bridge


def test_d166_spec_freezes_non_authoritative_boundary() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for marker in (
        "DECISION != PERMISSION != EXECUTION",
        "Risk classification is not permission.",
        "execution_succeeded != result_verified",
        "D166 does not invent verification evidence.",
        "It performs no retry and no automatic rollback.",
        "no DB table",
        "no provider/LLM call",
        "no composition-root wiring",
    ):
        assert marker in text
