from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = "backend/app/contracts/governed_execution_experience_runtime.py"
SERVICE = "backend/app/services/governed_execution_experience_runtime.py"


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_d185_contract_has_no_raw_execution_or_sensitive_field_surface():
    from app.contracts.governed_execution_experience_runtime import (
        GovernedExecutionExperienceRuntimeOutcome,
    )

    names = {
        field.name.casefold()
        for field in fields(GovernedExecutionExperienceRuntimeOutcome)
    }
    assert names.isdisjoint(
        {
            "output",
            "error",
            "parameters",
            "payload",
            "prompt",
            "response",
            "credentials",
            "token",
            "secret",
        }
    )


def test_d185_service_has_no_execution_ai_network_memory_or_trust_dependency():
    tree = ast.parse(source(SERVICE))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {
            "openai",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "subprocess",
            "sqlalchemy",
            "sqlite3",
            "multiprocessing",
            "queue",
        }
    )

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
        "ai_adapter",
        "memory",
        "trusted_experience",
        "credential",
        "connector",
        "provider",
    )
    assert all(
        all(fragment not in module.casefold() for fragment in forbidden)
        for module in modules
    )


def test_d185_service_has_no_authority_invocation_markers():
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


def test_d185_does_not_modify_frozen_d182_d183_d184_services():
    for path in (
        "backend/app/services/governed_execution_outcome_feedback.py",
        "backend/app/services/governed_execution_experience_candidate.py",
        "backend/app/services/governed_execution_experience_review.py",
    ):
        text = source(path)
        assert "D185" not in text
        assert "governed_execution_experience_runtime" not in text


def test_d185_adds_no_public_api_config_db_repository_model_schema_migration_or_frontend():
    forbidden_paths = (
        "backend/app/api/v1/governed_execution_experience_runtime.py",
        "backend/app/schemas/governed_execution_experience_runtime.py",
        "backend/app/models/governed_execution_experience_runtime.py",
        "backend/app/repositories/governed_execution_experience_runtime.py",
        "backend/alembic/versions/0019_governed_execution_experience_runtime.py",
        "frontend/components/governed-execution-experience-runtime.tsx",
    )
    assert all(not (ROOT / path).exists() for path in forbidden_paths)

    config = source("backend/app/core/config.py")
    assert "D185" not in config
    assert "governed_execution_experience_runtime" not in config

    execution_api = source("backend/app/api/v1/execution_approvals.py")
    assert "D185" not in execution_api
    assert "governed_execution_experience_runtime" not in execution_api


def test_d185_production_seam_is_strictly_after_successful_d182_record():
    text = source("backend/app/services/owner_approved_governed_execution.py")
    assert "recorded = recorder.try_record(binding, outcome)" in text
    assert "if not recorded:" in text
    assert "integration.try_integrate(binding.approval_id)" in text
    assert text.index("recorded = recorder.try_record(binding, outcome)") < text.index(
        "integration.try_integrate(binding.approval_id)"
    )


def test_d185_dependencies_compose_only_existing_d182_store_plus_d185_store():
    text = source("backend/app/api/dependencies.py")
    assert "get_governed_execution_experience_runtime_store" in text
    assert "get_governed_execution_experience_runtime_integration" in text
    assert "feedback_store=get_governed_execution_outcome_feedback_store()" in text
    assert "runtime_store=get_governed_execution_experience_runtime_store()" in text


def test_d185_authority_defaults_are_never_true():
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


def test_d185_spec_freezes_exact_scope_authority_and_stop_boundary():
    spec = source("docs/specs/D185_EXECUTION_EXPERIENCE_RUNTIME_INTEGRATION_V1.md")
    for marker in (
        "EXACT 2 MODIFIED + 7 ADDED = 9 PATHS",
        "POST-AUTHORITY",
        "EPHEMERAL",
        "Result.output",
        "Result.error",
        "D182 → D185 → D183 → D184",
        "STOP",
        "Experience can influence advice. Experience cannot grant authority.",
    ):
        assert marker in spec
