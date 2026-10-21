from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeOutcome,
)
from app.services.structured_action_proposal_runtime import (
    StructuredActionProposalRuntimeIntegration,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_d170_outcome_has_no_authority_surface():
    names = {item.name for item in fields(StructuredActionProposalRuntimeOutcome)}
    assert names == {
        "status",
        "reason_code",
        "conversion",
        "runtime",
        "contract_version",
    }
    assert names.isdisjoint(
        {
            "action_intent",
            "permission",
            "permission_granted",
            "approved",
            "approved_by_owner",
            "execution_authorization",
            "execute_now",
            "capability_id",
            "risk_class",
            "retry",
            "rollback",
        }
    )

    for forbidden in (
        "execute",
        "approve",
        "deny",
        "authorize",
        "dispatch",
        "retry",
        "rollback",
    ):
        assert not hasattr(
            StructuredActionProposalRuntimeIntegration,
            forbidden,
        )


def test_d170_service_imports_only_orchestration_dependencies():
    path = "backend/app/services/structured_action_proposal_runtime.py"
    tree = ast.parse(source(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    allowed = {
        "__future__",
        "app.contracts.cognitive_executive",
        "app.contracts.command",
        "app.contracts.structured_action_intent_proposal",
        "app.contracts.structured_action_proposal_runtime",
        "app.services.governed_action_intent_conversion",
        "app.services.governed_action_runtime",
    }
    assert modules.issubset(allowed)


def test_d170_has_no_direct_authority_or_execution_surface():
    text = source("backend/app/services/structured_action_proposal_runtime.py")

    assert "ActionIntent(" not in text
    for token in (
        "GovernedActionBoundary",
        "CapabilityPermissionPolicy",
        "ExecutionApprovalService",
        "PendingExecutionApprovalStore",
        "CommandExecutionCoordinator",
        "ExecutionAuthorization",
        "OwnerApprovalEvidence",
        "ToolRuntime",
        "ModuleRuntime",
        ".execute(",
        ".approve(",
        ".deny(",
        ".authorize(",
        "OpenAI",
    ):
        assert token not in text

    assert text.count("._conversion_service.convert(") == 1
    assert text.count("._runtime_integration.prepare(") == 1


def test_d170_production_composition_is_dependency_only():
    text = source("backend/app/api/dependencies.py")
    for marker in (
        "GovernedActionIntentConversionService",
        "StructuredActionProposalRuntimeIntegration",
        "def get_governed_action_intent_conversion_service(",
        "def get_structured_action_proposal_runtime_integration(",
    ):
        assert marker in text

    tree = ast.parse(text)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    composition = functions["get_structured_action_proposal_runtime_integration"]
    composition_text = ast.get_source_segment(text, composition)
    assert composition_text is not None
    assert "Depends(" in composition_text
    assert "get_governed_action_intent_conversion_service" in composition_text
    assert "get_governed_action_runtime_integration" in composition_text


def test_d170_is_not_invoked_by_normal_chat_or_cognitive_runtime():
    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        text = source(path)
        assert "StructuredActionProposalRuntimeIntegration" not in text
        assert "structured_action_proposal_runtime" not in text
        assert "get_structured_action_proposal_runtime_integration" not in text


def test_d170_adds_no_api_model_repo_frontend_or_migration():
    forbidden = (
        "backend/app/models/structured_action_proposal_runtime.py",
        "backend/app/repositories/structured_action_proposal_runtime.py",
        "backend/app/api/v1/structured_action_proposal_runtime.py",
        "backend/app/schemas/structured_action_proposal_runtime.py",
        "frontend/components/structured-action-proposal-runtime.tsx",
        "backend/alembic/versions/0017_structured_action_proposal_runtime.py",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)

    versions = ROOT / "backend/alembic/versions"
    assert (
        versions / "0016_cognitive_quality_observability.py"
    ).is_file()
    assert not any(
        path.name.startswith("0017_")
        for path in versions.glob("*.py")
    )


def test_d170_spec_preserves_frozen_runtime_limits():
    text = source(
        "docs/specs/D170_STRUCTURED_ACTION_PROPOSAL_RUNTIME_INTEGRATION_V1.md"
    )
    for marker in (
        "Runtime integration != Execution authority",
        "prepared_for_owner_review != approved",
        "Approval proposal != Owner decision",
        "does not reimplement D167 lineage checks",
        "production-composable",
        "intentionally not invoked",
        "exactly eight implementation paths",
        "at most owner-review preparation",
    ):
        assert marker in text