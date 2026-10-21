from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.services.structured_action_candidate_producer import (
    StructuredActionCandidateProducer,
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


def test_d172_contracts_have_no_authority_surface() -> None:
    semantic_names = {item.name for item in fields(StructuredActionSemanticInput)}
    assert semantic_names == {
        "source_turn_id",
        "source_artifact_digest",
        "semantic_action",
        "parameters",
        "missing_information",
    }

    outcome_names = {
        item.name for item in fields(StructuredActionCandidateProductionOutcome)
    }
    assert outcome_names == {
        "status",
        "reason_code",
        "candidate",
        "contract_version",
    }

    forbidden = {
        "target_kind",
        "adapter_id",
        "operation",
        "permission",
        "permission_granted",
        "owner_approval",
        "execution_authorization",
        "execute_now",
        "retry",
        "rollback",
    }
    assert semantic_names.isdisjoint(forbidden)
    assert outcome_names.isdisjoint(forbidden)

    for name in ("execute", "approve", "authorize", "deny", "retry", "rollback"):
        assert not hasattr(StructuredActionCandidateProducer, name)


def test_d172_service_imports_no_permission_runtime_provider_connector_or_persistence() -> None:
    modules = imported_modules(
        "backend/app/services/structured_action_candidate_producer.py"
    )
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
        module == prefix or module.startswith(prefix + ".")
        for module in modules
        for prefix in forbidden_prefixes
    )

    text = source("backend/app/services/structured_action_candidate_producer.py")
    for token in (
        "CapabilityPermissionPolicy",
        "AdapterRegistry",
        "ActionIntent(",
        "GovernedActionBoundary",
        "GovernedActionRuntimeIntegration",
        "GovernedActionIntentConversionService",
        "StructuredActionProposalRuntimeIntegration",
        "StructuredActionIntentProposalService",
        "ExecutionApprovalService",
        "ExecutionAuthorization",
        "ToolRuntime",
        "ModuleRuntime",
        "CommandExecutionCoordinator",
        ".execute(",
        ".approve(",
        ".authorize(",
        "OpenAI",
    ):
        assert token not in text


def test_d172_has_no_free_text_or_brain_output_action_inference_surface() -> None:
    semantic_names = {item.name for item in fields(StructuredActionSemanticInput)}
    assert semantic_names.isdisjoint(
        {
            "message",
            "prompt",
            "assistant_reply",
            "model_output",
            "planning_text",
            "goal_title",
            "trusted_experience_text",
        }
    )

    text = source("backend/app/services/structured_action_candidate_producer.py")
    for token in (
        "CognitiveExecutiveOutcome",
        "CognitivePlanningArtifact",
        "CognitiveDecisionGoalArtifact",
        "TrustedExperience",
        "CommandRequest",
        "ChatTurnResult",
        "re.",
        "casefold(",
    ):
        assert token not in text


def test_d172_is_composed_only_by_d173_and_not_invoked_from_normal_chat() -> None:
    dependencies = source("backend/app/api/dependencies.py")
    for marker in (
        "StructuredActionCandidateProducer",
        "get_structured_action_candidate_producer",
        "StructuredActionCandidateRuntimeIntegration",
        "get_structured_action_candidate_runtime_integration",
    ):
        assert marker in dependencies

    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/structured_action_intent_proposal.py",
        "backend/app/services/structured_action_proposal_runtime.py",
    ):
        assert "StructuredActionCandidateProducer" not in source(path)
        assert "StructuredActionCandidateRuntimeIntegration" not in source(path)


def test_d172_adds_no_api_model_repo_frontend_migration_or_store() -> None:
    forbidden = (
        "backend/app/models/structured_action_candidate_producer.py",
        "backend/app/repositories/structured_action_candidate_producer.py",
        "backend/app/api/v1/structured_action_candidate_producer.py",
        "backend/app/schemas/structured_action_candidate_producer.py",
        "frontend/components/structured-action-candidate-producer.tsx",
        "backend/alembic/versions/0017_structured_action_candidate_producer.py",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)

    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d172_spec_preserves_frozen_authority_boundaries() -> None:
    text = source(
        "docs/specs/D172_STRUCTURED_ACTION_CANDIDATE_PRODUCER_V1.md"
    )
    for marker in (
        "Candidate != Proposal != Approval != Execution",
        "Mapping != Permission",
        "Lineage preservation != Lineage validation",
        "no free-text -> action inference",
        "D167 remains the current-lineage authority",
        "normal Chat invocation is deferred to D173",
        "exactly six added paths",
    ):
        assert marker in text