import asyncio
import json
import unittest
from typing import Any
from urllib.parse import urlsplit

from app.api.dependencies import (
    get_chat_plugin_action_completion_service,
    get_execution_approval_service,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.command import CommandRequest, ExecutionPlan, Result
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.main import app
from app.services.adapter_registry import AdapterRegistry
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_execution_coordinator import CommandExecutionCoordinator
from app.services.execution_approval_service import (
    ExecutionApprovalService,
    PendingExecutionApprovalStore,
)
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.module_runtime import ModuleRuntime
from app.services.tool_runtime import ToolRuntime


class StubToolAdapter:
    adapter_id = "tool.api"
    tool_name = "api"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.calls = 0
        self.error: str | None = None

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.calls += 1
        if self.error is not None:
            return Result(
                request_id=request.request_id,
                status="failed",
                error=self.error,
            )
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={
                "value": plan.steps[0].parameters.get("value")
            },
        )


class NoopChatPluginActionCompletion:
    def complete(self, approval_id, outcome):
        return None


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.index = 0

    def __call__(self) -> str:
        self.index += 1
        return f"{self.prefix}-{self.index}"


async def invoke_app(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    target = urlsplit(path)
    encoded_body = (
        json.dumps(body).encode("utf-8")
        if body is not None
        else b""
    )
    received = False
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {
            "type": "http.request",
            "body": encoded_body,
            "more_body": False,
        }

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    request_headers = (
        {"Content-Type": "application/json"}
        if body is not None
        else {}
    )
    request_headers.update(headers or {})
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": target.path,
        "raw_path": target.path.encode(),
        "query_string": target.query.encode(),
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in request_headers.items()
        ],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)

    start = next(
        message
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]
    }
    return (
        start["status"],
        response_headers,
        json.loads(response_body),
    )


class ExecutionApprovalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides.clear()
        self.tool = StubToolAdapter()
        registry = AdapterRegistry((self.tool,))
        policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(
                ExecutableCapabilityPermission(
                    "exec.test.api",
                    "tool",
                    "tool.api",
                    "echo",
                    "none",
                    "none",
                    True,
                ),
            ),
        )
        planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=object(),  # type: ignore[arg-type]
            ai_discovery=object(),  # type: ignore[arg-type]
            permission_policy=policy,
        )
        guard = ExecutionGuard(
            registry=registry,
            permission_policy=policy,
        )
        coordinator = CommandExecutionCoordinator(
            planner=planner,
            guard=guard,
            tool_runtime=ToolRuntime(registry=registry),
            module_runtime=ModuleRuntime(registry=registry),
        )
        store = PendingExecutionApprovalStore(
            approval_id_factory=SequenceFactory("approval"),
        )
        self.service = ExecutionApprovalService(
            planner=planner,
            permission_policy=policy,
            coordinator=coordinator,
            store=store,
            request_id_factory=SequenceFactory("execution"),
        )
        app.dependency_overrides[
            get_execution_approval_service
        ] = lambda: self.service
        app.dependency_overrides[
            get_chat_plugin_action_completion_service
        ] = lambda: NoopChatPluginActionCompletion()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def request(self, *args: Any, **kwargs: Any):
        return asyncio.run(invoke_app(*args, **kwargs))

    @staticmethod
    def create_body() -> dict[str, Any]:
        return {
            "target_kind": "tool",
            "adapter_id": "tool.api",
            "operation": "echo",
            "parameters": {"value": "hello"},
        }

    @staticmethod
    def local_headers(**extra: str) -> dict[str, str]:
        headers = {"X-OAI-Local-Request": "1"}
        headers.update(extra)
        return headers

    def create_pending(self):
        status_code, _, body = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=self.create_body(),
            headers=self.local_headers(),
        )
        self.assertEqual(status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "pending")
        return body["data"]

    def test_local_request_marker_is_required(self) -> None:
        status_code, _, body = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=self.create_body(),
        )

        self.assertEqual(status_code, 403)
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "HTTP_403")
        self.assertEqual(self.tool.calls, 0)

    def test_create_uses_standard_envelope_and_separate_execution_request_id(self) -> None:
        status_code, headers, body = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=self.create_body(),
            headers=self.local_headers(
                **{"X-Request-ID": "transport-request"}
            ),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["request_id"], "execution-1")
        self.assertNotEqual(data["request_id"], "transport-request")
        self.assertEqual(
            headers["x-request-id"],
            "transport-request",
        )
        self.assertEqual(
            data["capability"],
            {
                "capability_id": "exec.test.api",
                "effect": "none",
                "data_class": "none",
            },
        )
        self.assertEqual(len(data["plan_digest"]), 64)
        self.assertEqual(self.tool.calls, 0)

    def test_unpermitted_operation_returns_rejected_without_ticket(self) -> None:
        body = self.create_body()
        body["operation"] = "delete"

        status_code, _, response = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=body,
            headers=self.local_headers(),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "rejected")
        self.assertEqual(
            response["data"]["reason_code"],
            "capability_not_permitted",
        )
        self.assertIsNone(response["data"]["approval_id"])
        self.assertEqual(self.tool.calls, 0)

    def test_approve_executes_once_and_replay_returns_not_pending(self) -> None:
        proposal = self.create_pending()
        path = (
            "/api/v1/execution-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        decision_body = {"plan_digest": proposal["plan_digest"]}

        status_code, _, body = self.request(
            path,
            method="POST",
            body=decision_body,
            headers=self.local_headers(),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "completed")
        self.assertEqual(
            body["data"]["result"]["status"],
            "succeeded",
        )
        self.assertEqual(self.tool.calls, 1)

        replay_status, _, replay = self.request(
            path,
            method="POST",
            body=decision_body,
            headers=self.local_headers(),
        )
        self.assertEqual(replay_status, 404)
        self.assertEqual(
            replay["error"]["code"],
            "approval_not_pending",
        )
        self.assertEqual(self.tool.calls, 1)

    def test_deny_blocks_without_execution(self) -> None:
        proposal = self.create_pending()
        path = (
            "/api/v1/execution-approvals/"
            f"{proposal['approval_id']}/deny"
        )

        status_code, _, body = self.request(
            path,
            method="POST",
            body={"plan_digest": proposal["plan_digest"]},
            headers=self.local_headers(),
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(body["data"]["status"], "blocked")
        self.assertEqual(
            body["data"]["reason_code"],
            "owner_approval_denied",
        )
        self.assertIsNone(body["data"]["result"])
        self.assertEqual(self.tool.calls, 0)

    def test_digest_mismatch_is_conflict_and_invalidates_ticket(self) -> None:
        proposal = self.create_pending()
        path = (
            "/api/v1/execution-approvals/"
            f"{proposal['approval_id']}/approve"
        )
        wrong = "0" * 64
        if wrong == proposal["plan_digest"]:
            wrong = "f" * 64

        status_code, _, body = self.request(
            path,
            method="POST",
            body={"plan_digest": wrong},
            headers=self.local_headers(),
        )

        self.assertEqual(status_code, 409)
        self.assertEqual(
            body["error"]["code"],
            "approval_plan_mismatch",
        )
        self.assertEqual(self.tool.calls, 0)

        retry_status, _, retry = self.request(
            path,
            method="POST",
            body={"plan_digest": proposal["plan_digest"]},
            headers=self.local_headers(),
        )
        self.assertEqual(retry_status, 404)
        self.assertEqual(
            retry["error"]["code"],
            "approval_not_pending",
        )

    def test_ai_target_and_client_controlled_fields_are_validation_errors(self) -> None:
        ai_body = self.create_body()
        ai_body["target_kind"] = "ai"
        status_code, _, body = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=ai_body,
            headers=self.local_headers(),
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

        extra_body = self.create_body()
        extra_body["request_id"] = "client-controlled"
        status_code, _, body = self.request(
            "/api/v1/execution-approvals",
            method="POST",
            body=extra_body,
            headers=self.local_headers(),
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_adapter_error_detail_is_not_exposed(self) -> None:
        proposal = self.create_pending()
        self.tool.error = "private stack trace must not escape"
        path = (
            "/api/v1/execution-approvals/"
            f"{proposal['approval_id']}/approve"
        )

        status_code, _, body = self.request(
            path,
            method="POST",
            body={"plan_digest": proposal["plan_digest"]},
            headers=self.local_headers(),
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(
            body["data"]["result"]["status"],
            "failed",
        )
        self.assertEqual(
            body["data"]["result"]["error_code"],
            "execution_failed",
        )
        self.assertNotIn(
            "private stack trace",
            json.dumps(body),
        )


if __name__ == "__main__":
    unittest.main()
