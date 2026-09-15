import unittest

from app.contracts.ai import (
    AI_ADAPTER_CONTRACT_VERSION,
    AIRequest,
    AIResult,
)
from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.execution_authorization import ExecutionAuthorization
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_runtime import AIRuntime, AIExecutionRejectedError
from app.services.execution_audit import ExecutionAuditTrail, InMemoryAuditSink
from app.services.execution_guard import execution_plan_digest


class RecordingAIAdapter:
    contract_version = AI_ADAPTER_CONTRACT_VERSION

    def __init__(
        self,
        adapter_id: str = "chatgpt.default",
        *,
        error: Exception | None = None,
        invalid_result: bool = False,
    ) -> None:
        self.adapter_id = adapter_id
        self.error = error
        self.invalid_result = invalid_result
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.invalid_result:
            return object()
        return AIResult(content="provider secret reply")


class AIRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = RecordingAIAdapter()
        self.sink = InMemoryAuditSink()
        self.audit = ExecutionAuditTrail(sink=self.sink)
        self.registry = AdapterRegistry((self.adapter,))
        self.runtime = AIRuntime(
            registry=self.registry,
            audit=self.audit,
        )

    @staticmethod
    def request(request_id: str = "request-1") -> CommandRequest:
        return CommandRequest(
            request_id=request_id,
            command="chat.message",
            arguments={
                "message": "hello",
                "conversation_id": None,
                "project_id": None,
            },
        )

    @staticmethod
    def plan(
        *,
        request_id: str = "request-1",
        adapter_id: str = "chatgpt.default",
        parameters: dict[str, object] | None = None,
        owner_approval_required: bool = False,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            adapter_id=adapter_id,
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="ai.generate_text",
                    parameters=(
                        parameters
                        if parameters is not None
                        else {
                            "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                            "model_id": "configured-model",
                        }
                    ),
                ),
            ),
            owner_approval_required=owner_approval_required,
        )

    @staticmethod
    def authorization(
        plan: ExecutionPlan,
        *,
        request_id: str | None = None,
        digest: str | None = None,
        target_kind: str = "ai",
    ) -> ExecutionAuthorization:
        return ExecutionAuthorization(
            request_id=request_id or plan.request_id,
            status="authorized",
            target_kind=target_kind,  # type: ignore[arg-type]
            source_plan_digest=digest or execution_plan_digest(plan),
            execution_plan=plan,
            reason_code="approval_not_required",
        )

    def test_authorized_binding_invokes_registered_adapter_once(self) -> None:
        request = self.request()
        plan = self.plan()
        proxy = self.runtime.bind(
            request,
            self.authorization(plan),
        )

        result = proxy.generate(AIRequest(content="provider secret prompt"))

        self.assertEqual(result.content, "provider secret reply")
        self.assertEqual(len(self.adapter.requests), 1)
        self.assertEqual(
            [event.status for event in self.sink.events],
            ["started", "succeeded"],
        )
        self.assertTrue(
            all(event.target_kind == "ai" for event in self.sink.events)
        )
        audit_text = repr(self.sink.events)
        self.assertNotIn("provider secret prompt", audit_text)
        self.assertNotIn("provider secret reply", audit_text)

    def test_binding_is_consumed_before_first_attempt(self) -> None:
        request = self.request()
        plan = self.plan()
        proxy = self.runtime.bind(
            request,
            self.authorization(plan),
        )

        proxy.generate(AIRequest(content="first"))
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "ai_authorization_replayed",
        ):
            proxy.generate(AIRequest(content="second"))

        self.assertEqual(len(self.adapter.requests), 1)

    def test_provider_failure_is_not_retried_and_is_audited_safely(self) -> None:
        private_error = RuntimeError("provider private detail")
        adapter = RecordingAIAdapter(error=private_error)
        sink = InMemoryAuditSink()
        runtime = AIRuntime(
            registry=AdapterRegistry((adapter,)),
            audit=ExecutionAuditTrail(sink=sink),
        )
        request = self.request()
        plan = self.plan()
        proxy = runtime.bind(
            request,
            self.authorization(plan),
        )

        with self.assertRaisesRegex(RuntimeError, "provider private detail"):
            proxy.generate(AIRequest(content="prompt private detail"))

        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(
            [event.status for event in sink.events],
            ["started", "failed"],
        )
        audit_text = repr(sink.events)
        self.assertNotIn("provider private detail", audit_text)
        self.assertNotIn("prompt private detail", audit_text)
        with self.assertRaises(AIExecutionRejectedError):
            proxy.generate(AIRequest(content="retry"))
        self.assertEqual(len(adapter.requests), 1)

    def test_plan_mutation_after_bind_fails_digest_revalidation(self) -> None:
        parameters: dict[str, object] = {
            "capability_id": AI_CAPABILITY_TEXT_GENERATION,
            "model_id": "configured-model",
        }
        request = self.request()
        plan = self.plan(parameters=parameters)
        proxy = self.runtime.bind(
            request,
            self.authorization(plan),
        )
        parameters["model_id"] = "changed-model"

        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "authorization_plan_mismatch",
        ):
            proxy.generate(AIRequest(content="must not execute"))

        self.assertEqual(self.adapter.requests, [])
        self.assertEqual(self.sink.events, ())

    def test_non_authorized_or_wrong_target_never_binds(self) -> None:
        request = self.request()
        plan = self.plan()
        digest = execution_plan_digest(plan)
        blocked = ExecutionAuthorization(
            request_id=request.request_id,
            status="blocked",
            target_kind="ai",
            source_plan_digest=digest,
            execution_plan=None,
            reason_code="owner_approval_required",
        )
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "ai_execution_not_authorized",
        ):
            self.runtime.bind(request, blocked)

        wrong_target = self.authorization(plan, target_kind="tool")
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "authorization_target_mismatch",
        ):
            self.runtime.bind(request, wrong_target)

        self.assertEqual(self.adapter.requests, [])
        self.assertEqual(self.sink.events, ())

    def test_request_or_digest_mismatch_never_binds(self) -> None:
        plan = self.plan()
        authorization = self.authorization(plan)

        # ExecutionAuthorization itself enforces authorization.request_id ==
        # execution_plan.request_id. Exercise the AIRuntime defensive check with
        # a different caller request instead of constructing an invalid contract.
        mismatched_request = self.request(request_id="request-2")
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "request_plan_mismatch",
        ):
            self.runtime.bind(
                mismatched_request,
                authorization,
            )

        request = self.request()
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "authorization_plan_mismatch",
        ):
            self.runtime.bind(
                request,
                self.authorization(plan, digest="a" * 64),
            )

        self.assertEqual(self.adapter.requests, [])

    def test_wrong_plan_shape_never_binds(self) -> None:
        request = self.request()

        # D36 contract construction already forbids an authorized plan that
        # remains owner-approval-gated. Keep that invariant covered here
        # without fabricating an impossible ExecutionAuthorization instance.
        approval_gated = self.plan(owner_approval_required=True)
        with self.assertRaisesRegex(
            ValueError,
            "authorized execution plans must not remain approval-gated",
        ):
            self.authorization(approval_gated)

        cases = (
            ExecutionPlan(
                request_id="request-1",
                adapter_id="chatgpt.default",
                steps=(
                    ExecutionStep(
                        1,
                        "wrong.operation",
                        {
                            "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                            "model_id": "configured-model",
                        },
                    ),
                ),
                owner_approval_required=False,
            ),
            self.plan(
                parameters={
                    "capability_id": AI_CAPABILITY_TEXT_GENERATION,
                    "model_id": "configured-model",
                    "extra": "denied",
                }
            ),
        )
        for plan in cases:
            with self.subTest(plan=plan):
                with self.assertRaisesRegex(
                    AIExecutionRejectedError,
                    "authorization_policy_violation",
                ):
                    self.runtime.bind(
                        request,
                        self.authorization(plan),
                    )

        self.assertEqual(self.adapter.requests, [])

    def test_missing_registered_adapter_fails_closed(self) -> None:
        request = self.request()
        plan = self.plan(adapter_id="missing.ai")
        runtime = AIRuntime(registry=AdapterRegistry(()))

        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "ai_adapter_unavailable",
        ):
            runtime.bind(
                request,
                self.authorization(plan),
            )

    def test_invalid_ai_result_is_one_failed_attempt(self) -> None:
        adapter = RecordingAIAdapter(invalid_result=True)
        sink = InMemoryAuditSink()
        runtime = AIRuntime(
            registry=AdapterRegistry((adapter,)),
            audit=ExecutionAuditTrail(sink=sink),
        )
        request = self.request()
        plan = self.plan()

        proxy = runtime.bind(request, self.authorization(plan))
        with self.assertRaisesRegex(
            AIExecutionRejectedError,
            "invalid_ai_result",
        ):
            proxy.generate(AIRequest(content="prompt"))

        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(
            [event.status for event in sink.events],
            ["started", "failed"],
        )


if __name__ == "__main__":
    unittest.main()
