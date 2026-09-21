from dataclasses import fields
import inspect

from app.contracts.engineering_ai_draft import EngineeringAIDraftRequest
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.engineering_ai_draft import EngineeringAIDraftService
from app.services.execution_planner import ExecutionPlanner


def test_d110_ai_draft_input_has_no_authority_fields() -> None:
    names = {item.name for item in fields(EngineeringAIDraftRequest)}
    assert names == {"conversation_id", "relative_path", "instruction"}


def test_d110_uses_exact_software_engineering_route_and_local_adapter() -> None:
    source = inspect.getsource(EngineeringAIDraftService.draft)
    assert "task_kind=AITaskKind.SOFTWARE_ENGINEERING" in source
    assert "planning.plan.adapter_id != LOCAL_AI_ADAPTER_ID" in source
    assert source.count(".generate(") == 1


def test_d110_service_has_no_proposal_apply_shell_git_network_or_credentials() -> None:
    source = inspect.getsource(EngineeringAIDraftService)
    forbidden = (
        "EngineeringChangeProposalService",
        "EngineeringApplyExecutionService",
        "filesystem_write_tools",
        "ToolRuntime",
        "ModuleRuntime",
        "subprocess",
        "os.system",
        "Popen",
        "git commit",
        "git push",
        "requests.",
        "httpx.",
        "CredentialAccessBroker",
        "connector",
    )
    for marker in forbidden:
        assert marker not in source


def test_d110_planner_extension_defaults_to_general_chat() -> None:
    signature = inspect.signature(ExecutionPlanner.plan)
    assert signature.parameters["task_kind"].default is AITaskKind.GENERAL_CHAT
    source = inspect.getsource(ExecutionPlanner._plan_ai)
    assert "task_kind: AITaskKind" in source
    assert "if task_kind is AITaskKind.GENERAL_CHAT" in source
    assert "self._ai_router.route(decision)" in source
    assert "self._ai_router.route(decision, task_kind=task_kind)" in source


def test_d110_draft_service_does_not_import_d107_or_d108_authority_services() -> None:
    module = __import__(
        "app.services.engineering_ai_draft",
        fromlist=["EngineeringAIDraftService"],
    )
    source = inspect.getsource(module)
    assert "engineering_change_proposal import" not in source
    assert "engineering_apply_execution import" not in source
    assert "engineering_apply_approval import" not in source
