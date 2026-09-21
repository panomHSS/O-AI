from __future__ import annotations

import inspect

from app.contracts.ai_brain_routing import AIMode
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.ai_router import AIRouter
from app.services.execution_planner import ExecutionPlanner


def test_d111_planner_mode_extension_is_optional_and_server_typed() -> None:
    signature = inspect.signature(ExecutionPlanner.plan)
    assert signature.parameters["task_kind"].default is AITaskKind.GENERAL_CHAT
    assert signature.parameters["ai_mode"].default is None


def test_d111_planner_uses_brain_route_only_when_structured_mode_exists() -> None:
    source = inspect.getsource(ExecutionPlanner._plan_ai)

    assert "ai_mode: AIMode | None" in source
    assert "if ai_mode is not None:" in source
    assert "self._ai_router.route_mode(" in source

    # Preserve the legacy compatibility path required by D110/general chat.
    assert "if task_kind is AITaskKind.GENERAL_CHAT" in source
    assert "self._ai_router.route(decision)" in source
    assert "self._ai_router.route(decision, task_kind=task_kind)" in source


def test_d111_brain_route_is_selection_only_and_never_executes() -> None:
    source = inspect.getsource(AIRouter.route_mode)

    for forbidden in (
        ".generate(",
        "AIRuntime",
        "ExecutionGuard",
        "authorize(",
        "execution_plan",
        "model_id",
        "api_key",
        "credential",
        "repository_root",
        "subprocess",
        "git push",
    ):
        assert forbidden not in source


def test_d111_brain_route_accepts_only_existing_task_and_mode_contracts() -> None:
    parameters = inspect.signature(AIRouter.route_mode).parameters
    assert tuple(parameters) == (
        "self",
        "decision",
        "task_kind",
        "requested_mode",
    )


def test_d111_execution_layers_do_not_import_brain_route_decision_as_authority() -> None:
    from app.services import ai_runtime, execution_guard

    runtime_source = inspect.getsource(ai_runtime)
    guard_source = inspect.getsource(execution_guard)

    assert "AIBrainRouteDecision" not in runtime_source
    assert "AIBrainRouteDecision" not in guard_source
    assert "AIMode" not in runtime_source
    assert "AIMode" not in guard_source


def test_d111_no_new_cloud_adapter_or_provider_runtime_is_added() -> None:
    router_source = inspect.getsource(AIRouter)
    planner_source = inspect.getsource(ExecutionPlanner)

    assert "ChatGPTAdapter(" not in router_source
    assert "OpenAIChatProvider(" not in router_source
    assert "ChatGPTAdapter(" not in planner_source
    assert "OpenAIChatProvider(" not in planner_source
