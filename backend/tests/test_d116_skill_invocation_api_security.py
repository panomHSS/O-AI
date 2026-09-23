"""D116 owner-facing Skill invocation API security acceptance."""

from __future__ import annotations

import ast
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ENGINEERING_FILE = _BACKEND_ROOT / "app" / "api" / "v1" / "engineering.py"
_DEPENDENCIES_FILE = _BACKEND_ROOT / "app" / "api" / "dependencies.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _top_level_function(path: Path, name: str):
    matches = [
        node
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    assert len(matches) == 1, f"Expected exactly one {name}"
    return matches[0]


def _call_name(call: ast.Call) -> str:
    node = call.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def test_d116_exact_owner_facing_route_is_post_and_bounded() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")

    decorators = [
        decorator
        for decorator in route.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "router"
        and decorator.func.attr == "post"
    ]

    assert len(decorators) == 1
    decorator = decorators[0]
    assert decorator.args
    assert isinstance(decorator.args[0], ast.Constant)
    assert decorator.args[0].value == "/skills/{skill_id}/invoke"
    assert "EngineeringInvestigationResponse" in ast.unparse(decorator)


def test_d116_route_requires_existing_local_owner_marker_dependency() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")
    text = ast.unparse(route)

    assert "require_local_engineering_owner_request_marker" in text
    assert "Depends(require_local_engineering_owner_request_marker)" in text


def test_d116_route_uses_d115_bridge_as_only_invocation_entry() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")
    calls = [
        _call_name(node)
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
    ]

    assert calls.count("bridge.invoke") == 1
    assert all(not name.endswith(".investigate") for name in calls)
    assert "workflow.investigate" not in calls
    assert "EngineeringInvestigationService.investigate" not in calls


def test_d116_route_has_no_retry_loop_or_alternate_dispatch() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")

    assert not any(
        isinstance(node, (ast.For, ast.AsyncFor, ast.While))
        for node in ast.walk(route)
    )

    text = ast.unparse(route).lower()
    for fragment in (
        "retry",
        "fallback",
        "handler_registry",
        "resolve_handler",
        "import_module",
        "entry_points",
        "getattr(",
    ):
        assert fragment not in text


def test_d116_route_reuses_d113_request_response_contracts() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")
    text = ast.unparse(route)

    assert "EngineeringInvestigationCreateRequest" in text
    assert "EngineeringInvestigationRequest" in text
    assert "EngineeringInvestigationResponse.from_result" in text
    assert "workflow.workspace_scope.workspace_id.value" in text


def test_d116_route_does_not_accept_workspace_or_runtime_selection() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")
    text = ast.unparse(route).lower()

    for fragment in (
        "workspace_id:",
        "provider_id",
        "adapter_id",
        "model_id",
        "credential",
        "connector_id",
        "tool_id",
        "module_id",
        "approval",
        "apply_instruction",
    ):
        assert fragment not in text


def test_d116_dependency_builds_trusted_catalog_over_same_workflow() -> None:
    dependency = _top_level_function(
        _DEPENDENCIES_FILE,
        "get_skill_invocation_bridge",
    )
    text = ast.unparse(dependency)

    assert "get_engineering_investigation_workflow_service" in text
    assert "build_builtin_skill_catalog()" in text
    assert "SkillInvocationBridge" in text
    assert "engineering_investigation_workflow=workflow" in text


def test_d116_dependency_has_no_dynamic_or_runtime_authority() -> None:
    dependency = _top_level_function(
        _DEPENDENCIES_FILE,
        "get_skill_invocation_bridge",
    )
    text = ast.unparse(dependency).lower()

    for fragment in (
        "importlib",
        "entry_points",
        "import_module",
        "getattr(",
        "provider",
        "model_id",
        "credential",
        "resolve_tool",
        "resolve_module",
        "tool.execute",
        "module.execute",
        "executionplanner",
        "executionguard",
        "airuntime",
    ):
        assert fragment not in text


def test_d116_route_maps_skill_errors_without_arbitrary_exception_text() -> None:
    mapper = _top_level_function(_ENGINEERING_FILE, "_skill_invocation_error")
    text = ast.unparse(mapper)

    assert "SKILL_INVOCATION_SKILL_NOT_FOUND" in text
    assert "SKILL_INVOCATION_SKILL_UNSUPPORTED" in text
    assert "SKILL_INVOCATION_DESCRIPTOR_MISMATCH" in text
    assert "SKILL_INVOCATION_REQUEST_INVALID" in text
    assert "HTTP_404_NOT_FOUND" in text
    assert "HTTP_422_UNPROCESSABLE_ENTITY" in text
    assert "HTTP_503_SERVICE_UNAVAILABLE" in text
    assert "str(error)" not in text
    assert "repr(error)" not in text


def test_d116_route_and_dependency_add_no_mutation_or_execution_authority() -> None:
    route = _top_level_function(_ENGINEERING_FILE, "invoke_engineering_skill")
    dependency = _top_level_function(
        _DEPENDENCIES_FILE,
        "get_skill_invocation_bridge",
    )

    text = ast.unparse(route).lower() + "\n" + ast.unparse(dependency).lower()

    for fragment in (
        'target_kind="skill"',
        "target_kind='skill'",
        '"skill.execute"',
        "'skill.execute'",
        "engineering_change_proposal",
        "engineering_apply_execution",
        "create_proposal(",
        "approve(",
        "apply(",
        "executionplanner",
        "executionguard",
        "airuntime",
        "tool.execute",
        "module.execute",
        "credential",
    ):
        assert fragment not in text