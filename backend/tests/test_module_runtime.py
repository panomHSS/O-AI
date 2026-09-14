import unittest

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Result,
)
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.module_runtime import ModuleRuntime


class StubAIAdapter:
    adapter_id = "ai.stub"
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.generate_calls = 0

    def generate(self, request: AIRequest) -> AIResult:
        self.generate_calls += 1
        return AIResult(content="unused")


class StubToolAdapter:
    adapter_id = "tool.stub"
    tool_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.execute_calls = 0

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.execute_calls += 1
        return Result(request.request_id, "succeeded")


class RecordingModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        *,
        result: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[CommandRequest, ExecutionPlan]] = []
        self.result = result
        self.error = error

    def execute(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> Result:
        self.calls.append((request, plan))
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result  # type: ignore[return-value]
        return Result(
            request_id=request.request_id,
            status="succeeded",
            output={"module": "ok"},
        )


class ModuleRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ai = StubAIAdapter()
        self.tool = StubToolAdapter()
        self.module = RecordingModuleAdapter()
        self.registry = AdapterRegistry(
            (self.ai, self.tool, self.module)
        )
        self.runtime = ModuleRuntime(registry=self.registry)

    @staticmethod
    def request(
        *,
        request_id: str = "req-module",
        command: str = "module.execute",
    ) -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command=command,
            arguments={},
        )

    @staticmethod
    def plan(
        *,
        request_id: str = "req-module",
        adapter_id: str = "module.stub",
        approval_required: bool = False,
        steps: tuple[ExecutionStep, ...] | None = None,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter_id,
            steps=steps
            if steps is not None
            else (ExecutionStep(1, "inspect", {"scope": "safe"}),),
            owner_approval_required=approval_required,
        )

    @classmethod
    def authorization(
        cls,
        *,
        request_id: str = "req-module",
        target_kind: str = "module",
        plan: ExecutionPlan | None = None,
        status: str = "authorized",
        reason_code: str = "owner_approval_verified",
    ) -> ExecutionAuthorization:
        execution_plan = plan or cls.plan(request_id=request_id)
        return ExecutionAuthorization(
            request_id=request_id,
            status=status,  # type: ignore[arg-type]
            target_kind=target_kind,  # type: ignore[arg-type]
            source_plan_digest="a" * 64,
            execution_plan=execution_plan
            if status == "authorized"
            else None,
            reason_code=reason_code,
        )

    def test_authorized_module_executes_exactly_once(self) -> None:
        request = self.request()
        plan = self.plan()
        authorization = self.authorization(plan=plan)

        result = self.runtime.execute(request, authorization)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output, {"module": "ok"})
        self.assertEqual(self.module.calls, [(request, plan)])
        self.assertEqual(self.tool.execute_calls, 0)
        self.assertEqual(self.ai.generate_calls, 0)

    def test_blocked_and_rejected_authorizations_never_execute(self) -> None:
        blocked = self.authorization(
            status="blocked",
            reason_code="owner_approval_required",
        )
        rejected = self.authorization(
            status="rejected",
            reason_code="approval_plan_mismatch",
        )

        blocked_result = self.runtime.execute(self.request(), blocked)
        rejected_result = self.runtime.execute(self.request(), rejected)

        self.assertEqual(blocked_result.status, "blocked")
        self.assertEqual(
            blocked_result.error,
            "module_authorization_required",
        )
        self.assertEqual(rejected_result.status, "failed")
        self.assertEqual(
            rejected_result.error,
            "module_authorization_rejected",
        )
        self.assertEqual(self.module.calls, [])

    def test_raw_execution_plan_cannot_invoke_runtime(self) -> None:
        result = self.runtime.execute(
            self.request(),
            self.plan(),  # type: ignore[arg-type]
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.error,
            "module_authorization_rejected",
        )
        self.assertEqual(self.module.calls, [])

    def test_wrong_target_kind_never_executes(self) -> None:
        authorization = self.authorization(target_kind="tool")

        result = self.runtime.execute(self.request(), authorization)

        self.assertEqual(
            result.error,
            "module_authorization_rejected",
        )
        self.assertEqual(self.module.calls, [])

    def test_request_authorization_plan_ids_must_match(self) -> None:
        authorization = self.authorization(request_id="req-module")

        result = self.runtime.execute(
            self.request(request_id="different"),
            authorization,
        )

        self.assertEqual(
            result.error,
            "request_authorization_mismatch",
        )
        self.assertEqual(self.module.calls, [])

    def test_wrong_command_never_executes(self) -> None:
        result = self.runtime.execute(
            self.request(command="tool.execute"),
            self.authorization(),
        )

        self.assertEqual(result.error, "module_command_rejected")
        self.assertEqual(self.module.calls, [])

    def test_approval_gated_execution_plan_cannot_form_authorization(self) -> None:
        gated = self.plan(approval_required=True)

        with self.assertRaises(ValueError):
            self.authorization(plan=gated)

        self.assertEqual(self.module.calls, [])

    def test_invalid_one_step_shape_never_executes(self) -> None:
        zero_step = self.plan(steps=())
        authorization = self.authorization(plan=zero_step)

        result = self.runtime.execute(self.request(), authorization)

        self.assertEqual(result.error, "module_plan_invalid")
        self.assertEqual(self.module.calls, [])

    def test_unknown_or_wrong_kind_adapter_never_executes(self) -> None:
        unknown = self.authorization(
            plan=self.plan(adapter_id="module.unknown")
        )
        wrong_kind = self.authorization(
            plan=self.plan(adapter_id="tool.stub")
        )

        unknown_result = self.runtime.execute(
            self.request(),
            unknown,
        )
        wrong_kind_result = self.runtime.execute(
            self.request(),
            wrong_kind,
        )

        self.assertEqual(
            unknown_result.error,
            "module_adapter_unavailable",
        )
        self.assertEqual(
            wrong_kind_result.error,
            "module_adapter_unavailable",
        )
        self.assertEqual(self.tool.execute_calls, 0)
        self.assertEqual(self.module.calls, [])

    def test_valid_failed_module_result_is_returned(self) -> None:
        self.module.result = Result(
            request_id="req-module",
            status="failed",
            error="module_specific_failure",
        )

        result = self.runtime.execute(
            self.request(),
            self.authorization(),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "module_specific_failure")
        self.assertEqual(len(self.module.calls), 1)

    def test_wrong_request_id_result_fails_closed(self) -> None:
        self.module.result = Result(
            request_id="other",
            status="succeeded",
        )

        result = self.runtime.execute(
            self.request(),
            self.authorization(),
        )

        self.assertEqual(result.error, "module_result_invalid")
        self.assertEqual(len(self.module.calls), 1)

    def test_non_result_fails_closed(self) -> None:
        self.module.result = object()

        result = self.runtime.execute(
            self.request(),
            self.authorization(),
        )

        self.assertEqual(result.error, "module_result_invalid")
        self.assertEqual(len(self.module.calls), 1)

    def test_adapter_exception_is_safe_and_not_retried(self) -> None:
        self.module.error = RuntimeError("private module detail")

        result = self.runtime.execute(
            self.request(),
            self.authorization(),
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "module_execution_failed")
        self.assertEqual(len(self.module.calls), 1)

    def test_inputs_remain_unchanged_after_execution(self) -> None:
        request = self.request()
        plan = self.plan()
        authorization = self.authorization(plan=plan)

        before_request = repr(request)
        before_plan = repr(plan)
        before_authorization = repr(authorization)

        self.runtime.execute(request, authorization)

        self.assertEqual(repr(request), before_request)
        self.assertEqual(repr(plan), before_plan)
        self.assertEqual(
            repr(authorization),
            before_authorization,
        )


if __name__ == "__main__":
    unittest.main()
