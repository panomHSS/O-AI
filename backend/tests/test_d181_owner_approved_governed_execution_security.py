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


def test_d181_service_never_imports_or_calls_tool_module_runtime_directly():
    text = source("backend/app/services/owner_approved_governed_execution.py")
    assert "ToolRuntime" not in text
    assert "ModuleRuntime" not in text
    assert "CommandExecutionCoordinator" not in text
    assert ".execute(" not in text
    assert ".authorize(" not in text
    assert ".propose(" not in text
    assert ".approve(" in text
    assert ".deny(" in text


def test_d181_service_has_no_provider_network_database_or_process_dependency():
    modules = imported_modules("backend/app/services/owner_approved_governed_execution.py")
    roots = {module.split(".", 1)[0] for module in modules}
    assert roots.isdisjoint(
        {"requests", "httpx", "urllib", "socket", "subprocess", "sqlalchemy", "openai"}
    )


def test_d181_chat_local_guard_precedes_binding_registration():
    text = source("backend/app/api/v1/chat.py")
    start = text.index("if explicit_action_requested:")
    end = text.index("if plugin_action_requested:", start)
    block = text[start:end]
    guard = block.index("x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE")
    bind = block.index("register_cognitive_projection(")
    assert guard < bind


def test_d181_decision_api_keeps_local_marker_dependency():
    text = source("backend/app/api/v1/execution_approvals.py")
    approve = text[text.index("def approve_execution("): text.index("def deny_execution(")]
    deny = text[text.index("def deny_execution("):]
    assert "Depends(require_local_execution_request_marker)" in approve
    assert "Depends(require_local_execution_request_marker)" in deny
    assert "decision_service.approve(" in approve
    assert "decision_service.deny(" in deny


def test_d181_adds_no_schema_model_repository_frontend_or_migration():
    forbidden = (
        "backend/app/schemas/owner_approved_governed_execution.py",
        "backend/app/models/owner_approved_governed_execution.py",
        "backend/app/repositories/owner_approved_governed_execution.py",
        "backend/alembic/versions/0017_owner_approved_governed_execution.py",
        "frontend/components/owner-approved-governed-execution.tsx",
    )
    assert all(not (ROOT / path).exists() for path in forbidden)


def test_d181_frozen_execution_engine_files_do_not_reference_d181():
    for path in (
        "backend/app/services/execution_approval_service.py",
        "backend/app/services/execution_planner.py",
        "backend/app/services/execution_guard.py",
        "backend/app/services/command_execution_coordinator.py",
        "backend/app/services/tool_runtime.py",
        "backend/app/services/module_runtime.py",
    ):
        assert "D181" not in source(path)
        assert "owner_approved_governed_execution" not in source(path)


def test_d181_spec_freezes_exact_scope_and_authority_ceiling():
    spec = source("docs/specs/D181_OWNER_APPROVED_GOVERNED_EXECUTION_INTEGRATION_V1.md")
    for marker in (
        "EXACT 4 MODIFIED + 7 ADDED = 11 PATHS",
        "R0",
        "Brain thinks != may execute",
        "Approval != authorization bypass",
        "no direct ToolRuntime / ModuleRuntime dispatch",
        "legacy D45 behavior remains unchanged",
        "STOP",
    ):
        assert marker in spec
