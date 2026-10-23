from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = "backend/app/contracts/governed_execution_experience_review.py"
SERVICE = "backend/app/services/governed_execution_experience_review.py"


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_d184_has_no_raw_execution_or_sensitive_data_dependency():
    combined = (source(CONTRACT) + "\n" + source(SERVICE)).casefold()
    for fragment in (
        "result.output",
        "result.error",
        "provider_payload",
        "credential",
        "prompt_text",
        "assistant_response",
        "user_free_text",
    ):
        assert fragment not in combined


def test_d184_has_no_ai_execution_network_or_provider_dependency():
    trees = (ast.parse(source(CONTRACT)), ast.parse(source(SERVICE)))
    forbidden_roots = {
        "openai",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
    }
    forbidden_modules = (
        "execution_approval_service",
        "execution_planner",
        "execution_guard",
        "command_execution_coordinator",
        "tool_runtime",
        "module_runtime",
        "cognitive_executive",
        "cognitive_invocation",
        "ai_runtime",
        "ai_adapter",
        "credentials",
        "connectors",
    )
    for tree in trees:
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        roots = {module.split(".", 1)[0] for module in modules}
        assert roots.isdisjoint(forbidden_roots)
        assert all(
            all(fragment not in module.casefold() for fragment in forbidden_modules)
            for module in modules
        )


def test_d184_has_no_memory_or_trusted_experience_lifecycle_dependency():
    combined = (source(CONTRACT) + "\n" + source(SERVICE)).casefold()
    for fragment in (
        "memoryservice",
        "trustedexperiencelifecycleservice",
        "trustedexperiencerepository",
        "cognitivetrustedexperienceproposal",
        "evaluate_cognitive_trusted_experience_eligibility",
    ):
        assert fragment.casefold() not in combined


def test_d184_has_no_authority_invocation_markers():
    combined = (source(CONTRACT) + "\n" + source(SERVICE)).casefold()
    for marker in (
        ".execute(",
        ".authorize(",
        ".approve(",
        ".deny(",
        ".retry(",
        ".rollback(",
        ".persist(",
        ".promote(",
        ".trust(",
    ):
        assert marker not in combined


def test_d184_is_not_wired_into_frozen_production_paths():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/v1/chat.py",
        "backend/app/api/v1/execution_approvals.py",
        "backend/app/contracts/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/contracts/governed_execution_experience_candidate.py",
        "backend/app/services/governed_execution_experience_candidate.py",
        "backend/app/services/owner_approved_governed_execution.py",
        "backend/app/services/execution_approval_service.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/execution_planner.py",
        "backend/app/services/execution_guard.py",
        "backend/app/services/tool_runtime.py",
        "backend/app/services/module_runtime.py",
        "backend/app/contracts/cognitive_trusted_experience.py",
        "backend/app/services/trusted_experience_lifecycle.py",
        "backend/app/repositories/trusted_experiences.py",
    ):
        text = source(path)
        assert "D184" not in text
        assert "governed_execution_experience_review" not in text


def test_d184_adds_no_api_schema_model_repository_frontend_migration_or_config():
    forbidden_paths = (
        "backend/app/api/v1/governed_execution_experience_review.py",
        "backend/app/schemas/governed_execution_experience_review.py",
        "backend/app/models/governed_execution_experience_review.py",
        "backend/app/repositories/governed_execution_experience_review.py",
        "backend/alembic/versions/0018_governed_execution_experience_review.py",
        "frontend/components/governed-execution-experience-review.tsx",
    )
    assert all(not (ROOT / path).exists() for path in forbidden_paths)
    config = source("backend/app/core/config.py")
    assert "D184" not in config
    assert "governed_execution_experience_review" not in config


def test_d184_spec_freezes_exact_scope_and_stop_boundary():
    spec = source(
        "docs/specs/D184_GOVERNED_EXECUTION_EXPERIENCE_REVIEW_ELIGIBILITY_V1.md"
    )
    for marker in (
        "EXACT 0 MODIFIED + 6 ADDED = 6 PATHS",
        "EPHEMERAL",
        "OWNER_REVIEW_ONLY",
        "Result.output",
        "Result.error",
        "STOP",
    ):
        assert marker in spec


def test_d184_authority_defaults_are_never_true():
    tree = ast.parse(source(CONTRACT))
    watched = {
        "automatic_trust",
        "automatic_learning",
        "automatic_promotion",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not node.target.id.endswith("_authority") and node.target.id not in watched:
            continue
        assert isinstance(node.value, ast.Constant)
        assert node.value.value is False
