from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeOutcome,
)
from app.services.structured_action_semantic_runtime import (
    StructuredActionSemanticRuntimeIntegration,
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


def test_d175_outcome_and_service_have_no_authority_surface() -> None:
    names = {item.name for item in fields(StructuredActionSemanticRuntimeOutcome)}
    assert names == {
        "status",
        "reason_code",
        "lineage",
        "runtime",
        "contract_version",
    }
    assert names.isdisjoint(
        {
            "permission",
            "permission_granted",
            "approved",
            "owner_decision",
            "execution_authorization",
            "execute_now",
            "capability_id",
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
        assert not hasattr(StructuredActionSemanticRuntimeIntegration, name)


def test_d175_service_imports_only_d174_d173_orchestration_boundaries() -> None:
    modules = imported_modules(
        "backend/app/services/structured_action_semantic_runtime.py"
    )
    assert modules.issubset(
        {
            "__future__",
            "app.contracts.cognitive_executive",
            "app.contracts.command",
            "app.contracts.structured_action_candidate_runtime",
            "app.contracts.structured_action_semantic_lineage",
            "app.contracts.structured_action_semantic_runtime",
            "app.services.structured_action_candidate_runtime",
            "app.services.structured_action_semantic_lineage",
        }
    )


def test_d175_has_no_direct_lower_authority_or_text_inference_surface() -> None:
    text = source("backend/app/services/structured_action_semantic_runtime.py")
    for token in (
        "StructuredActionCandidateProducer",
        "StructuredActionIntentProposalService",
        "StructuredActionProposalRuntimeIntegration",
        "GovernedActionIntentConversionService",
        "GovernedActionRuntimeIntegration",
        "GovernedActionBoundary",
        "CapabilityPermissionPolicy",
        "ExecutionApprovalService",
        "ExecutionAuthorization",
        "ToolRuntime",
        "ModuleRuntime",
        "ActionIntent(",
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
        "casefold(",
        "re.",
    ):
        assert token not in text
    assert text.count("._lineage_binder.bind(") == 1
    assert text.count("._candidate_runtime.process(") == 1


def test_d175_production_composition_is_dependency_only() -> None:
    text = source("backend/app/api/dependencies.py")
    for marker in (
        "StructuredActionSemanticLineageBinder",
        "StructuredActionSemanticRuntimeIntegration",
        "def get_structured_action_semantic_lineage_binder(",
        "def get_structured_action_semantic_runtime_integration(",
        "get_structured_action_candidate_runtime_integration",
    ):
        assert marker in text

    tree = ast.parse(text)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    binder_body = ast.get_source_segment(
        text,
        functions["get_structured_action_semantic_lineage_binder"],
    )
    runtime_body = ast.get_source_segment(
        text,
        functions["get_structured_action_semantic_runtime_integration"],
    )
    assert binder_body is not None
    assert runtime_body is not None
    assert binder_body.count("Depends(") == 0
    assert runtime_body.count("Depends(") == 2
    assert ".bind(" not in binder_body
    assert ".process(" not in binder_body
    assert ".bind(" not in runtime_body
    assert ".process(" not in runtime_body


def test_d175_is_not_invoked_by_normal_chat_or_cognitive_runtime() -> None:
    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        text = source(path)
        assert "StructuredActionSemanticRuntimeIntegration" not in text
        assert "structured_action_semantic_runtime" not in text
        assert "get_structured_action_semantic_runtime_integration" not in text


def test_d175_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/models/structured_action_semantic_runtime.py",
        "backend/app/repositories/structured_action_semantic_runtime.py",
        "backend/app/api/v1/structured_action_semantic_runtime.py",
        "backend/app/schemas/structured_action_semantic_runtime.py",
        "frontend/components/structured-action-semantic-runtime.tsx",
        "backend/alembic/versions/0017_structured_action_semantic_runtime.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d175_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d175_structured_action_semantic_runtime.py",
        "backend/tests/test_d175_structured_action_semantic_runtime_security.py",
        "backend/tests/test_d175_structured_action_semantic_runtime_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d175_spec_preserves_frozen_boundaries() -> None:
    text = source(
        "docs/specs/D175_STRUCTURED_ACTION_SEMANTIC_RUNTIME_INTEGRATION_V1.md"
    )
    for marker in (
        "Semantic draft != Semantic input",
        "Lineage binding != Lineage validation",
        "Semantic input != Candidate",
        "Mapping != Permission",
        "Proposal != Approval",
        "prepared_for_owner_review != approved",
        "D175 orchestration != Semantic inference",
        "D175 orchestration != Permission grant",
        "D175 orchestration != Execution",
        "composition != invocation",
        "EXACT 2 MODIFIED + 6 ADDED = 8 PATHS",
        "D167 remains authoritative",
        "at most Owner Review",
        "STOP",
    ):
        assert marker in text
