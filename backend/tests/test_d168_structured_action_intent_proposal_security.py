import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentProposal,
)
from app.services.structured_action_intent_proposal import (
    StructuredActionIntentProposalService,
)


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_d168_proposal_has_no_authority_surface():
    names = {item.name for item in fields(StructuredActionIntentProposal)}
    assert names == {
        "status",
        "reason_code",
        "source_turn_id",
        "source_artifact_digest",
        "target_kind",
        "adapter_id",
        "operation",
        "parameters",
        "missing_information",
        "governance_requirements",
        "contract_version",
    }
    assert names.isdisjoint(
        {
            "owner_approval",
            "permission",
            "permission_granted",
            "execution_authorization",
            "execute_now",
            "retry",
            "rollback",
        }
    )
    for forbidden in (
        "execute",
        "approve",
        "authorize",
        "deny",
        "retry",
        "rollback",
    ):
        assert not hasattr(
            StructuredActionIntentProposalService,
            forbidden,
        )


def test_d168_service_imports_no_runtime_provider_connector_or_persistence():
    path = "backend/app/services/structured_action_intent_proposal.py"
    tree = ast.parse(source(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    for prefix in (
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
    ):
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in modules
        )

    text = source(path)
    for token in (
        "ActionIntent(",
        "GovernedActionBoundary",
        "GovernedActionRuntimeIntegration",
        "ExecutionApprovalService",
        "CapabilityPermissionPolicy",
        "ToolRuntime",
        "ModuleRuntime",
        "CommandExecutionCoordinator",
        "ExecutionAuthorization",
        "OwnerApprovalEvidence",
        ".execute(",
        ".approve(",
        ".authorize(",
        "OpenAI",
    ):
        assert token not in text


def test_d168_does_not_modify_brain_or_existing_governance_into_a_producer():
    for path in (
        "backend/app/services/cognitive_executive.py",
        "backend/app/services/governed_action.py",
        "backend/app/services/governed_action_runtime.py",
        "backend/app/services/command_orchestrator.py",
    ):
        text = source(path)
        assert "StructuredActionIntentProposalService" not in text


def test_d168_adds_no_api_model_repo_frontend_migration_or_composition():
    forbidden = (
        "backend/app/models/structured_action_intent_proposal.py",
        "backend/app/repositories/structured_action_intent_proposal.py",
        "backend/app/api/v1/structured_action_intent_proposal.py",
        "backend/app/schemas/structured_action_intent_proposal.py",
        "frontend/components/structured-action-intent-proposal.tsx",
        "backend/alembic/versions/0017_structured_action_intent_proposal.py",
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


def test_d168_spec_preserves_frozen_authority_and_lineage_limits():
    text = source(
        "docs/specs/D168_STRUCTURED_ACTION_INTENT_PROPOSAL_V1.md"
    )
    for marker in (
        "Intent != Proposal != Approval != Execution",
        "Ambiguity != Permission",
        "Confidence != Authority",
        "does not create `ActionIntent`",
        "does not invoke D167",
        "no free-text -> tool inference",
        "Future governed conversion",
        "exactly six added paths",
    ):
        assert marker in text