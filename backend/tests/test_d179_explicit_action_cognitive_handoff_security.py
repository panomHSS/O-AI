from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffOutcome,
)
from app.services.explicit_action_cognitive_handoff import (
    ExplicitActionCognitiveHandoffIntegration,
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


def test_d179_contract_and_service_have_no_authority_surface() -> None:
    names = {item.name for item in fields(ExplicitActionCognitiveHandoffOutcome)}
    assert names == {"status", "reason_code", "runtime", "contract_version"}
    assert names.isdisjoint(
        {
            "permission",
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
        assert not hasattr(ExplicitActionCognitiveHandoffIntegration, name)


def test_d179_service_imports_only_d178_d177_handoff_boundaries() -> None:
    modules = imported_modules(
        "backend/app/services/explicit_action_cognitive_handoff.py"
    )
    assert modules.issubset(
        {
            "__future__",
            "uuid",
            "app.contracts.cognitive_executive",
            "app.contracts.command",
            "app.contracts.explicit_action_cognitive_handoff",
            "app.contracts.explicit_action_semantic_runtime",
            "app.services.command_orchestrator",
            "app.services.explicit_action_semantic_runtime",
        }
    )


def test_d179_has_no_direct_lower_action_or_execution_authority() -> None:
    text = source("backend/app/services/explicit_action_cognitive_handoff.py")
    for token in (
        "ExplicitActionDirectiveSemanticDraftProducer",
        "StructuredActionSemanticRuntimeIntegration",
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
        ".execute(",
        ".approve(",
        ".deny(",
        ".authorize(",
        "OpenAI",
    ):
        assert token not in text
    assert text.count("self._runtime.process(") == 1


def test_d179_dependency_composition_has_exactly_one_d177_dependency() -> None:
    text = source("backend/app/api/dependencies.py")
    tree = ast.parse(text)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    body = ast.get_source_segment(
        text,
        functions["get_explicit_action_cognitive_handoff_integration"],
    )
    assert body is not None
    assert body.count("Depends(") == 1
    assert "get_explicit_action_semantic_runtime_integration" in body
    assert ".process(" not in body
    assert "ExplicitActionCognitiveHandoffIntegration(" in body


def test_d179_live_adoption_is_only_through_d180_boundary() -> None:
    chat = source("backend/app/api/v1/chat.py")
    assert "ExplicitActionCognitiveHandoffIntegration" not in chat
    assert "get_explicit_action_cognitive_handoff_integration" not in chat
    assert "ExplicitActionLiveChatRoutingService" in chat
    assert "get_explicit_action_live_chat_routing_service" in chat

    for path in (
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/chat_action_bridge.py",
    ):
        text = source(path)
        assert "ExplicitActionCognitiveHandoffIntegration" not in text
        assert "explicit_action_cognitive_handoff" not in text
        assert "get_explicit_action_cognitive_handoff_integration" not in text


def test_d179_legacy_action_bridge_remains_d180_rollback_path() -> None:
    chat = source("backend/app/api/v1/chat.py")
    bridge = source("backend/app/services/chat_action_bridge.py")
    assert "chat_action_bridge.is_action_directive(payload.message)" in chat
    assert 'route_mode == "cognitive"' in chat
    assert "action_outcome = chat_action_bridge.process(" in chat
    assert 'ACTION_PREFIX = "/action"' in bridge
    assert "return self._propose(" in bridge


def test_d179_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/api/v1/explicit_action_cognitive_handoff.py",
        "backend/app/schemas/explicit_action_cognitive_handoff.py",
        "backend/app/models/explicit_action_cognitive_handoff.py",
        "backend/app/repositories/explicit_action_cognitive_handoff.py",
        "frontend/components/explicit-action-cognitive-handoff.tsx",
        "backend/alembic/versions/0017_explicit_action_cognitive_handoff.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d179_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d179_explicit_action_cognitive_handoff.py",
        "backend/tests/test_d179_explicit_action_cognitive_handoff_security.py",
        "backend/tests/test_d179_explicit_action_cognitive_handoff_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d179_spec_preserves_frozen_boundaries() -> None:
    text = source(
        "docs/specs/D179_EXPLICIT_ACTION_COGNITIVE_HANDOFF_INTEGRATION_V1.md"
    )
    for marker in (
        "D179 = isolated D178 -> D177 handoff",
        "composition != invocation",
        "D46 live routing remains unchanged",
        "D174/D167 remain lineage authority",
        "D179 handoff != Permission",
        "D179 handoff != Approval",
        "D179 handoff != Execution",
        "EXACT 1 MODIFIED + 6 ADDED = 7 PATHS",
        "at most Owner Review",
        "STOP",
    ):
        assert marker in text
