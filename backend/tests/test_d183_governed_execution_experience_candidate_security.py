from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACT = "backend/app/contracts/governed_execution_experience_candidate.py"
SERVICE = "backend/app/services/governed_execution_experience_candidate.py"


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


def test_d183_production_code_never_reads_raw_result_output_or_error():
    for path in (CONTRACT, SERVICE):
        text = source(path)
        assert ".output" not in text
        assert ".error" not in text
        assert "Result.output" not in text
        assert "Result.error" not in text


def test_d183_service_has_no_ai_execution_provider_network_db_or_process_dependency():
    modules = imported_modules(SERVICE)
    joined = "\n".join(sorted(modules))
    forbidden = (
        "execution_approval_service",
        "execution_planner",
        "execution_guard",
        "command_execution_coordinator",
        "tool_runtime",
        "module_runtime",
        "cognitive_executive",
        "cognitive_invocation",
        "ai_runtime",
        "memory",
        "trusted_experience",
        "credential",
        "connector",
    )
    assert all(fragment not in joined for fragment in forbidden)
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {
            "requests",
            "httpx",
            "urllib",
            "socket",
            "subprocess",
            "sqlalchemy",
            "openai",
        }
    )


def test_d183_contains_no_authority_calls():
    for path in (CONTRACT, SERVICE):
        text = source(path)
        for marker in (
            ".execute(",
            ".authorize(",
            ".approve(",
            ".deny(",
            ".propose(",
            ".retry(",
            ".rollback(",
        ):
            assert marker not in text


def test_d183_has_no_memory_or_trusted_experience_mutation_dependency():
    combined = "\n".join(
        sorted(imported_modules(CONTRACT) | imported_modules(SERVICE))
    )
    for fragment in (
        "memory_service",
        "trusted_experience_lifecycle",
        "trusted_experiences",
        "cognitive_experience",
        "cognitive_outcome_quality_feedback",
        "cognitive_trusted_experience",
    ):
        assert fragment not in combined


def test_d183_is_not_wired_into_frozen_production_paths():
    for path in (
        "backend/app/api/dependencies.py",
        "backend/app/api/v1/chat.py",
        "backend/app/api/v1/execution_approvals.py",
        "backend/app/contracts/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/services/owner_approved_governed_execution.py",
        "backend/app/services/execution_approval_service.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/execution_planner.py",
        "backend/app/services/execution_guard.py",
        "backend/app/services/tool_runtime.py",
        "backend/app/services/module_runtime.py",
    ):
        text = source(path)
        assert "D183" not in text
        assert "governed_execution_experience_candidate" not in text


def test_d183_adds_no_api_schema_model_repository_frontend_migration_or_config():
    forbidden_paths = (
        "backend/app/api/v1/governed_execution_experience.py",
        "backend/app/schemas/governed_execution_experience_candidate.py",
        "backend/app/models/governed_execution_experience_candidate.py",
        "backend/app/repositories/governed_execution_experience_candidate.py",
        "backend/alembic/versions/0017_governed_execution_experience_candidate.py",
        "frontend/components/governed-execution-experience-candidate.tsx",
    )
    assert all(not (ROOT / path).exists() for path in forbidden_paths)
    config = source("backend/app/core/config.py")
    assert "D183" not in config
    assert "governed_execution_experience_candidate" not in config


def test_d183_spec_freezes_exact_scope_and_stop_boundary():
    spec = source("docs/specs/D183_GOVERNED_EXECUTION_EXPERIENCE_CANDIDATE_V1.md")
    for marker in (
        "EXACT 0 MODIFIED + 6 ADDED = 6 PATHS",
        "EPHEMERAL",
        "CANDIDATE_ONLY",
        "Result.output",
        "Result.error",
        "STOP",
    ):
        assert marker in spec


def test_d183_authority_defaults_are_not_true():
    tree = ast.parse(source(CONTRACT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not node.target.id.endswith("_authority") and node.target.id not in {
            "automatic_trust",
            "automatic_promotion",
        }:
            continue
        assert isinstance(node.value, ast.Constant)
        assert node.value.value is False
