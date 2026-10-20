from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.governed_action_intent_conversion import (
    GovernedActionIntentConversionOutcome,
)
from app.services.governed_action_intent_conversion import (
    GovernedActionIntentConversionService,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_d169_outcome_has_no_authority_surface():
    names = {item.name for item in fields(GovernedActionIntentConversionOutcome)}
    assert names == {"status", "reason_code", "action_intent", "contract_version"}
    assert names.isdisjoint(
        {
            "permission",
            "permission_granted",
            "capability_id",
            "risk_class",
            "owner_approval",
            "approved_by_owner",
            "execution_authorization",
            "execution_ready",
            "execute_now",
            "retry",
            "rollback",
        }
    )
    for forbidden in (
        "execute",
        "approve",
        "authorize",
        "prepare",
        "dispatch",
        "retry",
        "rollback",
    ):
        assert not hasattr(GovernedActionIntentConversionService, forbidden)


def test_d169_service_imports_only_contract_side_dependencies():
    path = "backend/app/services/governed_action_intent_conversion.py"
    tree = ast.parse(source(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    allowed = {
        "app.contracts.governed_action",
        "app.contracts.governed_action_intent_conversion",
        "app.contracts.structured_action_intent_proposal",
        "__future__",
    }
    assert modules.issubset(allowed)


def test_d169_service_has_no_permission_approval_runtime_or_d167_invocation():
    text = source("backend/app/services/governed_action_intent_conversion.py")
    for token in (
        "CapabilityPermissionPolicy",
        "ExecutionApprovalService",
        "GovernedActionBoundary",
        "GovernedActionRuntimeIntegration",
        "ToolRuntime",
        "ModuleRuntime",
        "CommandExecutionCoordinator",
        "OwnerApprovalEvidence",
        "ExecutionAuthorization",
        ".prepare(",
        ".execute(",
        ".approve(",
        ".authorize(",
        "OpenAI",
    ):
        assert token not in text
    assert text.count("ActionIntent(") == 1


def test_d169_does_not_wire_itself_into_existing_production_paths():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/governed_action.py",
        "backend/app/services/governed_action_runtime.py",
        "backend/app/services/structured_action_intent_proposal.py",
    ):
        text = source(path)
        assert "GovernedActionIntentConversionService" not in text
        assert "governed_action_intent_conversion" not in text


def test_d169_adds_no_api_model_repo_frontend_or_migration():
    forbidden = (
        "backend/app/models/governed_action_intent_conversion.py",
        "backend/app/repositories/governed_action_intent_conversion.py",
        "backend/app/api/v1/governed_action_intent_conversion.py",
        "backend/app/schemas/governed_action_intent_conversion.py",
        "frontend/components/governed-action-intent-conversion.tsx",
        "backend/alembic/versions/0017_governed_action_intent_conversion.py",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)
    assert (
        ROOT
        / "backend/alembic/versions/0016_cognitive_quality_observability.py"
    ).is_file()


def test_d169_spec_preserves_frozen_conversion_and_authority_limits():
    text = source(
        "docs/specs/D169_GOVERNED_PROPOSAL_ACTION_INTENT_CONVERSION_V1.md"
    )
    for marker in (
        "Conversion != Permission",
        "Conversion != Approval",
        "Conversion != Execution",
        "ActionIntent creation != authority",
        "Lineage preservation != Lineage validation",
        "Semantic completeness != Capability permission",
        "does not invoke D167",
        "no production composition-root wiring",
        "exactly six added paths",
    ):
        assert marker in text