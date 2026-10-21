from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_candidate_runtime import StructuredActionCandidateRuntimeOutcome
from app.services.structured_action_candidate_runtime import StructuredActionCandidateRuntimeIntegration

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


def test_d173_outcome_has_no_authority_surface():
    names = {f.name for f in fields(StructuredActionCandidateRuntimeOutcome)}
    assert names == {
        "status", "reason_code", "production", "proposal", "runtime", "contract_version"
    }
    assert names.isdisjoint({
        "action_intent", "permission", "permission_granted", "approved",
        "owner_decision", "execution_authorization", "execute_now", "capability_id",
    })
    for name in ("execute", "approve", "deny", "authorize", "dispatch", "retry", "rollback"):
        assert not hasattr(StructuredActionCandidateRuntimeIntegration, name)


def test_d173_service_imports_only_frozen_orchestration_boundaries():
    modules = imported_modules("backend/app/services/structured_action_candidate_runtime.py")
    assert modules.issubset({
        "__future__",
        "app.contracts.cognitive_executive",
        "app.contracts.command",
        "app.contracts.structured_action_candidate_producer",
        "app.contracts.structured_action_candidate_runtime",
        "app.contracts.structured_action_intent_proposal",
        "app.contracts.structured_action_proposal_runtime",
        "app.services.structured_action_candidate_producer",
        "app.services.structured_action_intent_proposal",
        "app.services.structured_action_proposal_runtime",
    })


def test_d173_has_no_direct_authority_execution_or_text_inference_surface():
    text = source("backend/app/services/structured_action_candidate_runtime.py")
    for token in (
        "ActionIntent(", "CapabilityPermissionPolicy", "AdapterRegistry",
        "GovernedActionBoundary", "GovernedActionRuntimeIntegration",
        "GovernedActionIntentConversionService", "ExecutionApprovalService",
        "PendingExecutionApprovalStore", "CommandExecutionCoordinator",
        "ExecutionAuthorization", "ToolRuntime", "ModuleRuntime",
        ".execute(", ".approve(", ".deny(", ".authorize(", "OpenAI",
        "assistant_reply", "model_output", "planning_text", "goal_title",
        "trusted_experience_text", "casefold(", "re.",
    ):
        assert token not in text
    assert text.count("._candidate_producer.produce(") == 1
    assert text.count("._proposal_service.propose(") == 1
    assert text.count("._proposal_runtime.process(") == 1


def test_d173_production_composition_is_dependency_only():
    text = source("backend/app/api/dependencies.py")
    for marker in (
        "StructuredActionCandidateProducer",
        "StructuredActionIntentProposalService",
        "StructuredActionCandidateRuntimeIntegration",
        "def get_structured_action_candidate_producer(",
        "def get_structured_action_intent_proposal_service(",
        "def get_structured_action_candidate_runtime_integration(",
        "get_structured_action_proposal_runtime_integration",
    ):
        assert marker in text
    tree = ast.parse(text)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    body = ast.get_source_segment(
        text, functions["get_structured_action_candidate_runtime_integration"]
    )
    assert body is not None
    assert body.count("Depends(") == 3
    assert ".process(" not in body


def test_d173_is_not_invoked_by_normal_chat_or_cognitive_runtime():
    for path in (
        "backend/app/api/v1/chat.py",
        "backend/app/services/command_orchestrator.py",
        "backend/app/services/cognitive_executive.py",
    ):
        text = source(path)
        assert "StructuredActionCandidateRuntimeIntegration" not in text
        assert "structured_action_candidate_runtime" not in text
        assert "get_structured_action_candidate_runtime_integration" not in text


def test_d173_adds_no_api_model_repo_frontend_store_or_migration():
    for path in (
        "backend/app/models/structured_action_candidate_runtime.py",
        "backend/app/repositories/structured_action_candidate_runtime.py",
        "backend/app/api/v1/structured_action_candidate_runtime.py",
        "backend/app/schemas/structured_action_candidate_runtime.py",
        "frontend/components/structured-action-candidate-runtime.tsx",
        "backend/alembic/versions/0017_structured_action_candidate_runtime.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(p.name.startswith("0017_") for p in versions.glob("*.py"))


def test_d173_new_tests_add_no_skip_or_xfail_debt():
    forbidden_markers = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d173_structured_action_candidate_runtime.py",
        "backend/tests/test_d173_structured_action_candidate_runtime_security.py",
        "backend/tests/test_d173_structured_action_candidate_runtime_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden_markers)


def test_d173_spec_preserves_frozen_boundaries():
    text = source("docs/specs/D173_STRUCTURED_ACTION_CANDIDATE_RUNTIME_INTEGRATION_V1.md")
    for marker in (
        "Candidate != Proposal != Approval != Execution",
        "Mapping != Permission",
        "Lineage preservation != Lineage validation",
        "Runtime integration != Execution authority",
        "prepared_for_owner_review != approved",
        "composition != invocation",
        "no free-text -> action inference",
        "exactly two modified and six added paths",
        "at most owner-review preparation",
    ):
        assert marker in text
