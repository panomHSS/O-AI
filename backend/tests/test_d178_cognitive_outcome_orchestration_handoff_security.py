from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.services.command_orchestrator import CommandOrchestrationOutcome


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


def test_d178_handoff_contract_has_no_action_authority_surface() -> None:
    names = {item.name for item in fields(CommandOrchestrationOutcome)}
    assert names == {"response", "chat_turn", "cognitive_outcome"}
    assert names.isdisjoint(
        {
            "action_intent",
            "proposal",
            "permission",
            "approved",
            "owner_decision",
            "execution_authorization",
            "execute_now",
        }
    )


def test_d178_command_orchestrator_imports_cognitive_contract_but_not_action_stack() -> None:
    modules = imported_modules("backend/app/services/command_orchestrator.py")
    assert "app.contracts.cognitive_executive" in modules
    for forbidden in (
        "app.services.explicit_action_semantic_runtime",
        "app.services.explicit_action_semantic_draft_producer",
        "app.services.structured_action_semantic_runtime",
        "app.services.structured_action_semantic_lineage",
        "app.services.structured_action_candidate_runtime",
        "app.services.structured_action_candidate_producer",
        "app.services.structured_action_intent_proposal",
        "app.services.structured_action_proposal_runtime",
        "app.services.governed_action_runtime",
        "app.services.governed_action",
    ):
        assert forbidden not in modules


def test_d178_command_orchestrator_does_not_invoke_d176_d177_or_lower_action_chain() -> None:
    text = source("backend/app/services/command_orchestrator.py")
    for token in (
        "ExplicitActionSemanticRuntimeIntegration",
        "ExplicitActionDirectiveSemanticDraftProducer",
        "StructuredActionSemanticRuntimeIntegration",
        "StructuredActionSemanticLineageBinder",
        "StructuredActionCandidateRuntimeIntegration",
        "StructuredActionCandidateProducer",
        "StructuredActionIntentProposalService",
        "StructuredActionProposalRuntimeIntegration",
        "GovernedActionRuntimeIntegration",
        "GovernedActionBoundary",
        "prepared_for_owner_review",
    ):
        assert token not in text


def test_d178_handoff_is_internal_and_not_read_by_chat_api() -> None:
    chat = source("backend/app/api/v1/chat.py")
    assert "cognitive_outcome" not in chat
    assert ".cognitive_outcome" not in chat


def test_d178_handoff_is_not_exposed_in_chat_schema() -> None:
    schema = source("backend/app/schemas/chat.py")
    assert "cognitive_outcome" not in schema


def test_d178_adds_no_api_model_repo_frontend_store_or_migration() -> None:
    for path in (
        "backend/app/api/v1/cognitive_outcome_handoff.py",
        "backend/app/schemas/cognitive_outcome_handoff.py",
        "backend/app/models/cognitive_outcome_handoff.py",
        "backend/app/repositories/cognitive_outcome_handoff.py",
        "frontend/components/cognitive-outcome-handoff.tsx",
        "backend/alembic/versions/0017_cognitive_outcome_handoff.py",
    ):
        assert not (ROOT / path).exists()
    versions = ROOT / "backend/alembic/versions"
    assert (versions / "0016_cognitive_quality_observability.py").is_file()
    assert not any(path.name.startswith("0017_") for path in versions.glob("*.py"))


def test_d178_production_change_has_exact_single_handoff_assignment() -> None:
    text = source("backend/app/services/command_orchestrator.py")
    assert text.count("cognitive_outcome: CognitiveExecutiveOutcome | None = None") == 1
    assert text.count("cognitive_outcome=cognitive_result.outcome") == 1
    assert text.count("_cognitive_executive.process_chat(") == 1


def test_d178_new_tests_add_no_skip_or_xfail_debt() -> None:
    forbidden = (
        "pytest.mark." + "skip",
        "pytest.mark." + "xfail",
        "unittest." + "skip",
    )
    for path in (
        "backend/tests/test_d178_cognitive_outcome_orchestration_handoff.py",
        "backend/tests/test_d178_cognitive_outcome_orchestration_handoff_security.py",
        "backend/tests/test_d178_cognitive_outcome_orchestration_handoff_reproducibility.py",
    ):
        lowered = source(path).casefold()
        assert all(marker not in lowered for marker in forbidden)


def test_d178_spec_preserves_frozen_boundaries() -> None:
    text = source("docs/specs/D178_COGNITIVE_OUTCOME_ORCHESTRATION_HANDOFF_V1.md")
    for marker in (
        "D178 = cognitive outcome handoff only",
        "Cognitive outcome != Action Intent",
        "Cognitive outcome != Permission",
        "Cognitive outcome != Approval",
        "Cognitive outcome != Execution",
        "D174/D167 remain lineage authority",
        "D177 invocation is deferred",
        "internal server-side metadata only",
        "EXACT 1 MODIFIED + 4 ADDED = 5 PATHS",
        "STOP",
    ):
        assert marker in text
