"""D115 bounded Skill invocation bridge security acceptance."""

from __future__ import annotations

import ast
from pathlib import Path

from app.services.builtin_skills import (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
)
from app.services.skill_invocation_bridge import SkillInvocationBridge


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_BRIDGE_FILE = (
    _BACKEND_ROOT
    / "app"
    / "services"
    / "skill_invocation_bridge.py"
)

_FORBIDDEN_IMPORT_MODULES = frozenset(
    {
        "importlib",
        "subprocess",
        "socket",
        "sqlite3",
        "sqlalchemy",
        "requests",
        "httpx",
        "app.services.ai_runtime",
        "app.services.execution_guard",
        "app.services.execution_planner",
        "app.services.tool_runtime",
        "app.services.module_runtime",
        "app.services.credential_access_broker",
        "app.services.engineering_investigation",
        "app.services.engineering_change_proposal",
        "app.services.engineering_apply_execution",
    }
)

_FORBIDDEN_IMPORT_NAMESPACES = (
    "app.adapters",
    "app.connectors",
    "app.providers",
    "app.plugins",
)

_FORBIDDEN_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
}


def _tree() -> ast.Module:
    return ast.parse(
        _BRIDGE_FILE.read_text(encoding="utf-8"),
        filename=str(_BRIDGE_FILE),
    )


def _imports() -> tuple[str, ...]:
    imports: list[str] = []

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)

    return tuple(imports)


def test_bridge_imports_no_execution_authority_or_direct_d113_service() -> None:
    imports = _imports()

    for imported in imports:
        assert imported not in _FORBIDDEN_IMPORT_MODULES, (
            "D115 bridge imports forbidden authority module: "
            f"{imported}"
        )
        assert not imported.startswith(_FORBIDDEN_IMPORT_NAMESPACES), (
            "D115 bridge imports forbidden authority namespace: "
            f"{imported}"
        )

    assert (
        "app.services.engineering_investigation_workflow"
        in imports
    )
    assert "app.services.engineering_investigation" not in imports


def test_bridge_has_no_dynamic_execution_primitives() -> None:
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            assert node.func.id not in _FORBIDDEN_CALL_NAMES


def test_bridge_has_no_dynamic_dispatch_or_handler_lookup() -> None:
    source = _BRIDGE_FILE.read_text(encoding="utf-8").lower()

    forbidden_fragments = (
        "getattr(",
        "entry_points(",
        "import_module(",
        "spec_from_file_location(",
        "load_module(",
        "skill_manifest",
        "skills.json",
        "skills.yaml",
        "skills.yml",
        "handler_registry",
        "resolve_handler",
        "register_handler",
    )

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_bridge_does_not_define_skill_execution_target() -> None:
    source = _BRIDGE_FILE.read_text(encoding="utf-8")

    assert 'target_kind="skill"' not in source
    assert "target_kind='skill'" not in source
    assert '"skill.execute"' not in source
    assert "'skill.execute'" not in source


def test_bridge_surface_is_bounded_not_registry_like() -> None:
    for forbidden_name in (
        "register",
        "unregister",
        "install",
        "load",
        "resolve_handler",
        "set_handler",
        "add_handler",
        "execute",
        "run",
    ):
        assert not hasattr(SkillInvocationBridge, forbidden_name)

    assert hasattr(SkillInvocationBridge, "invoke")


def test_bridge_source_contains_exact_builtin_skill_identity() -> None:
    source = _BRIDGE_FILE.read_text(encoding="utf-8")

    assert "ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID" in source
    assert ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID == (
        "engineering.investigation_change_plan"
    )


def test_bridge_does_not_import_provider_tool_module_or_credential_authority() -> None:
    source = _BRIDGE_FILE.read_text(encoding="utf-8").lower()

    forbidden_fragments = (
        "provider_id",
        "adapter_id",
        "model_id",
        "credential",
        "resolve_tool",
        "resolve_module",
        "tool.execute",
        "module.execute",
        "ownerapprovalevidence",
        "executionauthorization",
        "executionplanningoutcome",
    )

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_bridge_does_not_import_engineering_proposal_or_apply_authority() -> None:
    source = _BRIDGE_FILE.read_text(encoding="utf-8").lower()

    assert "engineering_change_proposal" not in source
    assert "engineering_apply" not in source
    assert "create_proposal" not in source
    assert "approve(" not in source
    assert "apply(" not in source