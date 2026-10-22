from __future__ import annotations

import ast
from pathlib import Path

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


def test_d182_service_never_reads_raw_result_output_or_error():
    text = source("backend/app/services/governed_execution_outcome_feedback.py")
    assert ".output" not in text
    assert ".error" not in text
    assert "Result.output" not in text
    assert "Result.error" not in text


def test_d182_service_has_no_ai_execution_provider_network_db_or_process_dependency():
    modules = imported_modules("backend/app/services/governed_execution_outcome_feedback.py")
    joined = "\n".join(sorted(modules))
    forbidden = (
        "cognitive_executive", "cognitive_invocation", "ai_runtime",
        "execution_planner", "execution_guard", "command_execution_coordinator",
        "tool_runtime", "module_runtime", "credential", "connector",
    )
    assert all(fragment not in joined for fragment in forbidden)
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint({"requests", "httpx", "urllib", "socket", "subprocess", "sqlalchemy", "openai"})


def test_d182_service_contains_no_execution_authority_calls():
    text = source("backend/app/services/governed_execution_outcome_feedback.py")
    for marker in (".execute(", ".authorize(", ".propose(", ".approve(", ".deny("):
        assert marker not in text


def test_d182_public_execution_approval_api_is_not_modified_for_feedback():
    text = source("backend/app/api/v1/execution_approvals.py")
    assert "governed_execution_outcome_feedback" not in text
    assert "GovernedExecutionOutcomeFeedback" not in text


def test_d182_frozen_execution_engine_files_do_not_reference_d182():
    for path in (
        "backend/app/contracts/execution_approval.py",
        "backend/app/contracts/execution_integration.py",
        "backend/app/contracts/command.py",
        "backend/app/services/execution_approval_service.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/execution_planner.py",
        "backend/app/services/execution_guard.py",
        "backend/app/services/tool_runtime.py",
        "backend/app/services/module_runtime.py",
        "backend/app/api/v1/chat.py",
    ):
        text = source(path)
        assert "D182" not in text
        assert "governed_execution_outcome_feedback" not in text


def test_d182_adds_no_schema_model_repository_frontend_migration_or_config():
    forbidden = (
        "backend/app/schemas/governed_execution_outcome_feedback.py",
        "backend/app/models/governed_execution_outcome_feedback.py",
        "backend/app/repositories/governed_execution_outcome_feedback.py",
        "backend/alembic/versions/0017_governed_execution_outcome_feedback.py",
        "frontend/components/governed-execution-outcome-feedback.tsx",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)
    config = source("backend/app/core/config.py")
    assert "D182" not in config
    assert "governed_execution_outcome_feedback" not in config


def test_d182_spec_freezes_exact_scope_and_stop_boundary():
    spec = source("docs/specs/D182_GOVERNED_EXECUTION_OUTCOME_FEEDBACK_V1.md")
    for marker in (
        "EXACT 2 MODIFIED + 7 ADDED = 9 PATHS",
        "Execution Result = evidence, not authority",
        "Result.output",
        "Result.error",
        "legacy D45 behavior remains unchanged",
        "STOP",
    ):
        assert marker in spec
