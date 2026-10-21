from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_semantic_lineage import (
    StructuredActionSemanticDraft,
    StructuredActionSemanticLineageOutcome,
)
from app.services.structured_action_semantic_lineage import (
    StructuredActionSemanticLineageBinder,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imported_modules(path: str) -> set[str]:
    tree = ast.parse(source(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_d174_draft_and_outcome_have_no_authority_surface() -> None:
    draft_names = {item.name for item in fields(StructuredActionSemanticDraft)}
    assert draft_names == {
        "semantic_action",
        "parameters",
        "missing_information",
    }
    outcome_names = {
        item.name for item in fields(StructuredActionSemanticLineageOutcome)
    }
    assert outcome_names == {
        "status",
        "reason_code",
        "semantic",
        "contract_version",
    }
    assert (draft_names | outcome_names).isdisjoint(
        {
            "target_kind",
            "adapter_id",
            "operation",
            "permission",
            "approved",
            "owner_decision",
            "execution_authorization",
        }
    )
    for name in (
        "execute",
        "approve",
        "deny",
        "authorize",
        "dispatch",
        "retry",
        "rollback",
    ):
        assert not hasattr(StructuredActionSemanticLineageBinder, name)


def test_d174_service_imports_only_frozen_binding_boundaries() -> None:
    modules = imported_modules(
        "backend/app/services/structured_action_semantic_lineage.py"
    )
    assert modules.issubset(
        {
            "__future__",
            "app.contracts.cognitive_brain",
            "app.contracts.cognitive_executive",
            "app.contracts.command",
            "app.contracts.structured_action_candidate_producer",
            "app.contracts.structured_action_semantic_lineage",
        }
    )


def test_d174_has_no_authority_execution_or_text_inference_surface() -> None:
    text = source("backend/app/services/structured_action_semantic_lineage.py")
    for token in (
        "ActionIntent(",
        "StructuredActionCandidateProducer",
        "StructuredActionCandidateRuntimeIntegration",
        "GovernedActionBoundary",
        "GovernedActionRuntimeIntegration",
        "GovernedActionIntentConversionService",
        "CapabilityPermissionPolicy",
        "ExecutionApprovalService",
        "ExecutionAuthorization",
        "ToolRuntime",
        "ModuleRuntime",
        ".execute(",
        ".approve(",
        ".deny(",
        ".authorize(",
        "OpenAI",
        "assistant_reply",
        "model_output",
        "planning_text",
        "goal_title",
        "trusted_experience_text",
        "prompt",
        "casefold(",
        "re.",
    ):
        assert token not in text


def test_d174_is_composed_only_for_d175_and_not_invoked_from_normal_paths() -> None:
    dependencies = source("backend/app/api/dependencies.py")
    for marker in (
        "StructuredActionSemanticLineageBinder",
        "StructuredActionSemanticRuntimeIntegration",
        "def get_structured_action_semantic_lineage_binder(",
        "def get_structured_action_semantic_runtime_integration(",
    ):
        assert marker in dependencies

    tree = ast.parse(dependencies)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    runtime_body = ast.get_source_segment(
        dependencies,
        functions["get_structured_action_semantic_runtime_integration"],
    )
    assert runtime_body is not None
    assert runtime_body.count("Depends(") == 2
    assert ".bind(" not in runtime_body
    assert ".process(" not in runtime_body

    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        text = source(path)
        assert "StructuredActionSemanticLineageBinder" not in text
        assert "structured_action_semantic_lineage" not in text
        assert "StructuredActionSemanticRuntimeIntegration" not in text
        assert "structured_action_semantic_runtime" not in text


def test_d174_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/models/structured_action_semantic_lineage.py",
        "backend/app/repositories/structured_action_semantic_lineage.py",
        "backend/app/api/v1/structured_action_semantic_lineage.py",
        "backend/app/schemas/structured_action_semantic_lineage.py",
        "frontend/components/structured-action-semantic-lineage.tsx",
        "backend/alembic/versions/0017_structured_action_semantic_lineage.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d174_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d174_structured_action_semantic_lineage.py",
        "backend/tests/test_d174_structured_action_semantic_lineage_security.py",
        "backend/tests/test_d174_structured_action_semantic_lineage_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d174_spec_preserves_frozen_boundaries() -> None:
    text = source(
        "docs/specs/D174_STRUCTURED_ACTION_SEMANTIC_LINEAGE_BINDING_V1.md"
    )
    for marker in (
        "Lineage binding != Lineage validation",
        "Semantic input != Candidate",
        "Mapping != Permission",
        "Proposal != Approval",
        "Brain completion != Action authorization",
        "no free-text -> action inference",
        "EXACT 0 MODIFIED + 6 ADDED = 6 PATHS",
        "D167 remains authoritative",
        "STOP",
    ):
        assert marker in text
