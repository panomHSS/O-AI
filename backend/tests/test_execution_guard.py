import unittest

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.command import (
    CommandRequest,
    ExecutionPlan,
    ExecutionStep,
    Result,
)
from app.contracts.execution_authorization import OwnerApprovalEvidence
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.tool_module import TOOL_MODULE_ADAPTER_CONTRACT_VERSION
from app.services.adapter_registry import AdapterRegistry
from app.services.execution_guard import (
    ExecutionGuard,
    execution_plan_digest,
)


class StubAIAdapter:
    adapter_id = "ai.stub"
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.generate_calls = 0

    def generate(self, request: AIRequest) -> AIResult:
        self.generate_calls += 1
        return AIResult(content="not used")


class StubToolAdapter:
    adapter_id = "tool.stub"
    tool_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.execute_calls = 0

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        self.execute_calls += 1
        return Result(request.request_id, "succeeded")


class StubModuleAdapter:
    adapter_id = "module.stub"
    module_name = "stub"
    contract_version = TOOL_MODULE_ADAPTER_CONTRACT_VERSION

    def __init__(self) -> None:
        self.execute_calls = 0

    def execute(self, request: CommandRequest, plan: ExecutionPlan) -> Result:
        self.execute_calls += 1
        return Result(request.request_id, "succeeded")


class ExecutionGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ai = StubAIAdapter()
        self.tool = StubToolAdapter()
        self.module = StubModuleAdapter()
        self.guard = ExecutionGuard(
            registry=AdapterRegistry((self.ai, self.tool, self.module))
        )

    @staticmethod
    def planning(
        plan: ExecutionPlan,
        target_kind: str,
    ) -> ExecutionPlanningOutcome:
        return ExecutionPlanningOutcome(
            request_id=plan.request_id,
            status="planned",
            target_kind=target_kind,  # type: ignore[arg-type]
            plan=plan,
            reason_code="test_planned",
        )

    @staticmethod
    def tool_plan(
        *,
        request_id: str = "req-tool",
        value: object = "hello",
        approval_required: bool = True,
        adapter_id: str = "tool.stub",
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter_id,
            steps=(ExecutionStep(1, "echo", {"value": value}),),
            owner_approval_required=approval_required,
        )

    def test_ai_text_generation_authorizes_without_approval_evidence(self) -> None:
        request = CommandRequest(
            "req-ai",
            "chat.message",
            {
                "message": "hello",
                "conversation_id": None,
                "project_id": None,
            },
        )
        plan = ExecutionPlan(
            "req-ai",
            "ai.stub",
            (
                ExecutionStep(
                    1,
                    "ai.generate_text",
                    {
                        "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                        "model_id": "model-a",
                    },
                ),
            ),
            False,
        )

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "ai"),
        )

        self.assertEqual(authorization.status, "authorized")
        self.assertEqual(
            authorization.reason_code,
            "approval_not_required",
        )
        self.assertIs(authorization.execution_plan, plan)
        self.assertEqual(self.ai.generate_calls, 0)

    def test_tool_without_evidence_is_blocked(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan()

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
        )

        self.assertEqual(authorization.status, "blocked")
        self.assertEqual(
            authorization.reason_code,
            "owner_approval_required",
        )
        self.assertIsNone(authorization.execution_plan)
        self.assertEqual(self.tool.execute_calls, 0)

    def test_tool_approved_materializes_new_execution_ready_plan(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan()
        approval = OwnerApprovalEvidence(
            request_id="req-tool",
            plan_digest=execution_plan_digest(plan),
            decision="approved",
        )

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
            approval,
        )

        self.assertEqual(authorization.status, "authorized")
        self.assertEqual(
            authorization.reason_code,
            "owner_approval_verified",
        )
        self.assertTrue(plan.owner_approval_required)
        self.assertIsNotNone(authorization.execution_plan)
        self.assertFalse(
            authorization.execution_plan.owner_approval_required  # type: ignore[union-attr]
        )
        self.assertEqual(
            authorization.execution_plan.steps,  # type: ignore[union-attr]
            plan.steps,
        )
        self.assertEqual(self.tool.execute_calls, 0)

    def test_tool_denied_remains_blocked(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan()
        approval = OwnerApprovalEvidence(
            "req-tool",
            execution_plan_digest(plan),
            "denied",
        )

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
            approval,
        )

        self.assertEqual(authorization.status, "blocked")
        self.assertEqual(
            authorization.reason_code,
            "owner_approval_denied",
        )

    def test_module_requires_matching_approval(self) -> None:
        request = CommandRequest("req-module", "module.execute")
        plan = ExecutionPlan(
            "req-module",
            "module.stub",
            (ExecutionStep(1, "inspect", {"scope": "safe"}),),
            True,
        )
        blocked = self.guard.authorize(
            request,
            self.planning(plan, "module"),
        )
        approved = self.guard.authorize(
            request,
            self.planning(plan, "module"),
            OwnerApprovalEvidence(
                "req-module",
                execution_plan_digest(plan),
                "approved",
            ),
        )

        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(approved.status, "authorized")
        self.assertEqual(self.module.execute_calls, 0)

    def test_tool_or_module_cannot_bypass_approval_flag(self) -> None:
        tool_plan = self.tool_plan(approval_required=False)
        tool_auth = self.guard.authorize(
            CommandRequest("req-tool", "tool.execute"),
            self.planning(tool_plan, "tool"),
        )
        module_plan = ExecutionPlan(
            "req-module",
            "module.stub",
            (ExecutionStep(1, "inspect", {}),),
            False,
        )
        module_auth = self.guard.authorize(
            CommandRequest("req-module", "module.execute"),
            self.planning(module_plan, "module"),
        )

        self.assertEqual(tool_auth.status, "rejected")
        self.assertEqual(
            tool_auth.reason_code,
            "authorization_policy_violation",
        )
        self.assertEqual(module_auth.status, "rejected")
        self.assertEqual(
            module_auth.reason_code,
            "authorization_policy_violation",
        )

    def test_approval_for_plan_a_cannot_authorize_mutated_plan_b(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan_a = self.tool_plan(value="A")
        plan_b = self.tool_plan(value="B")
        self.assertNotEqual(
            execution_plan_digest(plan_a),
            execution_plan_digest(plan_b),
        )
        approval = OwnerApprovalEvidence(
            "req-tool",
            execution_plan_digest(plan_a),
            "approved",
        )

        authorization = self.guard.authorize(
            request,
            self.planning(plan_b, "tool"),
            approval,
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(
            authorization.reason_code,
            "approval_plan_mismatch",
        )

    def test_wrong_request_in_approval_is_rejected(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan()
        approval = OwnerApprovalEvidence(
            "other-request",
            execution_plan_digest(plan),
            "approved",
        )

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
            approval,
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(
            authorization.reason_code,
            "approval_plan_mismatch",
        )

    def test_wrong_adapter_kind_is_rejected(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan(adapter_id="module.stub")

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(
            authorization.reason_code,
            "adapter_kind_mismatch",
        )

    def test_non_planned_outcome_is_rejected(self) -> None:
        planning = ExecutionPlanningOutcome(
            request_id="req-tool",
            status="unavailable",
            target_kind=None,
            plan=None,
            reason_code="tool_adapter_unavailable",
        )

        authorization = self.guard.authorize(
            CommandRequest("req-tool", "tool.execute"),
            planning,
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(
            authorization.reason_code,
            "planning_not_executable",
        )

    def test_unsupported_parameter_object_fails_closed(self) -> None:
        request = CommandRequest("req-tool", "tool.execute")
        plan = self.tool_plan(value=object())

        authorization = self.guard.authorize(
            request,
            self.planning(plan, "tool"),
        )

        self.assertEqual(authorization.status, "rejected")
        self.assertEqual(
            authorization.reason_code,
            "invalid_plan_digest",
        )
        self.assertEqual(self.tool.execute_calls, 0)

    def test_digest_is_deterministic_for_mapping_order(self) -> None:
        first = ExecutionPlan(
            "req-tool",
            "tool.stub",
            (
                ExecutionStep(
                    1,
                    "echo",
                    {"nested": {"b": 2, "a": 1}},
                ),
            ),
            True,
        )
        second = ExecutionPlan(
            "req-tool",
            "tool.stub",
            (
                ExecutionStep(
                    1,
                    "echo",
                    {"nested": {"a": 1, "b": 2}},
                ),
            ),
            True,
        )

        self.assertEqual(
            execution_plan_digest(first),
            execution_plan_digest(second),
        )


if __name__ == "__main__":
    unittest.main()
