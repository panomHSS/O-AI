from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
)
from app.services.explicit_action_semantic_draft_producer import (
    ExplicitActionDirectiveSemanticDraftProducer,
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


def test_d176_contract_and_service_have_no_authority_surface() -> None:
    names = {item.name for item in fields(ExplicitActionSemanticDraftProductionOutcome)}
    assert names == {"status", "reason_code", "draft", "contract_version"}
    assert names.isdisjoint(
        {
            "source_turn_id", "source_artifact_digest", "target_kind", "adapter_id",
            "operation", "permission", "approved", "owner_decision",
            "execution_authorization", "execute_now",
        }
    )
    for name in ("execute", "approve", "deny", "authorize", "dispatch", "retry", "rollback", "bind"):
        assert not hasattr(ExplicitActionDirectiveSemanticDraftProducer, name)


def test_d176_service_imports_only_uuid_contract_and_d174_draft() -> None:
    modules = imported_modules("backend/app/services/explicit_action_semantic_draft_producer.py")
    assert modules.issubset(
        {
            "__future__",
            "uuid",
            "app.contracts.explicit_action_semantic_draft_producer",
            "app.contracts.structured_action_semantic_lineage",
        }
    )


def test_d176_has_no_routing_lineage_authority_inference_or_plugin_surface() -> None:
    text = source("backend/app/services/explicit_action_semantic_draft_producer.py")
    for token in (
        "StructuredActionCandidateProducer",
        "StructuredActionCandidateRuntimeIntegration",
        "StructuredActionSemanticLineageBinder",
        "StructuredActionSemanticRuntimeIntegration",
        "StructuredActionIntentProposalService",
        "StructuredActionProposalRuntimeIntegration",
        "GovernedActionRuntimeIntegration",
        "GovernedActionBoundary",
        "CapabilityPermissionPolicy",
        "ExecutionApprovalService",
        "ExecutionAuthorization",
        "AdapterRegistry",
        "ToolRuntime",
        "ModuleRuntime",
        "CommandExecutionCoordinator",
        "ChatActionBridge",
        "ChatPluginIntentRouter",
        "Gmail",
        "Calendar",
        "GitHub",
        "OpenAI",
        "CognitiveExecutiveOutcome",
        "assistant_reply",
        "model_output",
        "planning_text",
        "goal_title",
        "trusted_experience_text",
        "source_turn_id",
        "source_artifact_digest",
        "adapter_id",
        "target_kind",
        "operation",
        ".execute(",
        ".approve(",
        ".authorize(",
        ".bind(",
        ".process(",
        "casefold(",
        "re.",
    ):
        assert token not in text


def test_d176_is_not_composed_or_invoked_from_production_paths() -> None:
    markers = (
        "ExplicitActionDirectiveSemanticDraftProducer",
        "explicit_action_semantic_draft_producer",
        "get_explicit_action_semantic_draft_producer",
    )
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/chat_action_bridge.py",
    ):
        text = source(path)
        for marker in markers:
            assert marker not in text


def test_d176_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/models/explicit_action_semantic_draft_producer.py",
        "backend/app/repositories/explicit_action_semantic_draft_producer.py",
        "backend/app/api/v1/explicit_action_semantic_draft_producer.py",
        "backend/app/schemas/explicit_action_semantic_draft_producer.py",
        "frontend/components/explicit-action-semantic-draft-producer.tsx",
        "backend/alembic/versions/0017_explicit_action_semantic_draft_producer.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d176_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = ("pytest.mark." + "skip", "pytest.mark." + "xfail", "unittest." + "skip")
    for path in (
        "backend/tests/test_d176_explicit_action_semantic_draft_producer.py",
        "backend/tests/test_d176_explicit_action_semantic_draft_producer_security.py",
        "backend/tests/test_d176_explicit_action_semantic_draft_producer_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d176_spec_preserves_frozen_boundaries() -> None:
    text = source("docs/specs/D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_V1.md")
    for marker in (
        "Explicit syntax != lineage",
        "Semantic draft != semantic input",
        "D176 = explicit syntax -> semantic meaning",
        "D172 = semantic meaning -> candidate route",
        "semantic production != owner approval",
        "no free-text -> semantic action inference",
        "composition is deferred",
        "EXACT 0 MODIFIED + 6 ADDED = 6 PATHS",
        "D167 remains authoritative",
        "STOP",
    ):
        assert marker in text
