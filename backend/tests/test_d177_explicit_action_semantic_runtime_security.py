from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeOutcome,
)
from app.services.explicit_action_semantic_runtime import (
    ExplicitActionSemanticRuntimeIntegration,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def imported_modules(path: str) -> set[str]:
    tree = ast.parse(source(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_d177_outcome_and_service_have_no_authority_surface() -> None:
    names = {item.name for item in fields(ExplicitActionSemanticRuntimeOutcome)}
    assert names == {
        "status",
        "reason_code",
        "production",
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
        "bind",
    ):
        assert not hasattr(ExplicitActionSemanticRuntimeIntegration, name)


def test_d177_service_imports_only_d176_d175_orchestration_boundaries() -> None:
    modules = imported_modules(
        "backend/app/services/explicit_action_semantic_runtime.py"
    )
    assert modules.issubset(
        {
            "__future__",
            "uuid",
            "app.contracts.cognitive_executive",
            "app.contracts.command",
            "app.contracts.explicit_action_semantic_draft_producer",
            "app.contracts.explicit_action_semantic_runtime",
            "app.contracts.structured_action_semantic_runtime",
            "app.services.explicit_action_semantic_draft_producer",
            "app.services.structured_action_semantic_runtime",
        }
    )


def test_d177_has_no_parser_inference_or_direct_lower_authority_surface() -> None:
    text = source("backend/app/services/explicit_action_semantic_runtime.py")
    for token in (
        '"/action"',
        "ACTION_PREFIX",
        "_FIXED_SEMANTICS",
        "_REMAINDER_SEMANTICS",
        "StructuredActionSemanticLineageBinder",
        "StructuredActionCandidateRuntimeIntegration",
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
    assert text.count("._producer.produce(") == 1
    assert text.count("._semantic_runtime.process(") == 1


def test_d177_production_composition_is_dependency_only() -> None:
    text = source("backend/app/api/dependencies.py")
    for marker in (
        "ExplicitActionDirectiveSemanticDraftProducer",
        "ExplicitActionSemanticRuntimeIntegration",
        "def get_explicit_action_semantic_draft_producer(",
        "def get_explicit_action_semantic_runtime_integration(",
        "get_structured_action_semantic_runtime_integration",
    ):
        assert marker in text

    tree = ast.parse(text)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    producer_body = ast.get_source_segment(
        text,
        functions["get_explicit_action_semantic_draft_producer"],
    )
    runtime_body = ast.get_source_segment(
        text,
        functions["get_explicit_action_semantic_runtime_integration"],
    )
    assert producer_body is not None
    assert runtime_body is not None
    assert producer_body.count("Depends(") == 0
    assert runtime_body.count("Depends(") == 2
    assert ".produce(" not in producer_body
    assert ".process(" not in producer_body
    assert ".produce(" not in runtime_body
    assert ".process(" not in runtime_body


def test_d177_is_not_invoked_by_normal_chat_or_cognitive_runtime() -> None:
    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/chat_action_bridge.py",
    ):
        text = source(path)
        assert "ExplicitActionSemanticRuntimeIntegration" not in text
        assert "explicit_action_semantic_runtime" not in text
        assert "get_explicit_action_semantic_runtime_integration" not in text


def test_d177_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/models/explicit_action_semantic_runtime.py",
        "backend/app/repositories/explicit_action_semantic_runtime.py",
        "backend/app/api/v1/explicit_action_semantic_runtime.py",
        "backend/app/schemas/explicit_action_semantic_runtime.py",
        "frontend/components/explicit-action-semantic-runtime.tsx",
        "backend/alembic/versions/0017_explicit_action_semantic_runtime.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d177_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d177_explicit_action_semantic_runtime.py",
        "backend/tests/test_d177_explicit_action_semantic_runtime_security.py",
        "backend/tests/test_d177_explicit_action_semantic_runtime_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d177_spec_preserves_frozen_authority_boundaries() -> None:
    text = source(
        "docs/specs/D177_EXPLICIT_ACTION_SEMANTIC_RUNTIME_INTEGRATION_V1.md"
    )
    for marker in (
        "D176 owns explicit syntax -> semantic draft",
        "D177 owns D176 -> D175 orchestration",
        "composition != invocation",
        "Explicit syntax != lineage",
        "Semantic draft != semantic input",
        "D167 remains authoritative",
        "prepared_for_owner_review != approved",
        "D177 orchestration != Permission grant",
        "D177 orchestration != Execution",
        "EXACT 2 MODIFIED + 6 ADDED = 8 PATHS",
        "at most Owner Review",
        "STOP",
    ):
        assert marker in text
