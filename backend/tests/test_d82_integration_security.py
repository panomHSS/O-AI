import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.adapters.projected_plugin_module import (
    ProjectedPluginModuleAdapter,
    SafeConnectorModuleInvocationError,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep, Result
from app.contracts.connector_error_semantics import (
    GMAIL_READ_ERROR_SUBJECT,
    GMAIL_READ_SAFE_ERROR_CODES,
    GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
)
from app.services.chat_plugin_action import ChatPluginActionCompletionService


class _CaptureProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def capture_gmail(self, conversation_id, messages) -> None:
        self.calls.append(("gmail", messages))

    def capture_calendar(self, conversation_id, events) -> None:
        self.calls.append(("calendar", events))


class D82IntegrationSecurityTests(unittest.TestCase):
    @staticmethod
    def _make_failed_outcome(code: str):
        return SimpleNamespace(
            decision="approved",
            execution=SimpleNamespace(
                status="completed",
                result=Result(
                    request_id="d82-b03",
                    status="failed",
                    error=code,
                ),
            ),
        )

    @staticmethod
    def _completion_service(probe: _CaptureProbe):
        return ChatPluginActionCompletionService(
            conversation_service=object(),
            binding_store=object(),
            cross_connector_context_store=probe,
        )

    def test_failed_gmail_results_create_no_d78_context(self) -> None:
        probe = _CaptureProbe()
        service = self._completion_service(probe)
        binding = SimpleNamespace(
            conversation_id=uuid4(),
            gmail_query=object(),
            calendar_window=None,
        )

        for code in GMAIL_READ_SAFE_ERROR_CODES:
            with self.subTest(code=code):
                service._capture_cross_connector_context(
                    binding,
                    self._make_failed_outcome(code),
                )

        self.assertEqual(probe.calls, [])

    def test_failed_calendar_results_create_no_d78_context(self) -> None:
        probe = _CaptureProbe()
        service = self._completion_service(probe)
        binding = SimpleNamespace(
            conversation_id=uuid4(),
            gmail_query=None,
            calendar_window="today",
        )

        for code in GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES:
            with self.subTest(code=code):
                service._capture_cross_connector_context(
                    binding,
                    self._make_failed_outcome(code),
                )

        self.assertEqual(probe.calls, [])

    def test_unknown_connector_failure_creates_no_d78_context(self) -> None:
        probe = _CaptureProbe()
        service = self._completion_service(probe)
        binding = SimpleNamespace(
            conversation_id=uuid4(),
            gmail_query=object(),
            calendar_window=None,
        )

        service._capture_cross_connector_context(
            binding,
            self._make_failed_outcome("plugin_execution_failed"),
        )

        self.assertEqual(probe.calls, [])

    def test_safe_connector_failure_is_single_shot_at_adapter_boundary(self) -> None:
        calls = 0
        code = "gmail_rate_limited"

        def invoker(*args: object):
            nonlocal calls
            calls += 1
            raise SafeConnectorModuleInvocationError(
                plugin_id=GMAIL_READ_ERROR_SUBJECT[0],
                plugin_version=GMAIL_READ_ERROR_SUBJECT[1],
                capability_name=GMAIL_READ_ERROR_SUBJECT[2],
                code=code,
            )

        adapter = ProjectedPluginModuleAdapter(
            plugin_id=GMAIL_READ_ERROR_SUBJECT[0],
            plugin_version=GMAIL_READ_ERROR_SUBJECT[1],
            projected_capability_names=(GMAIL_READ_ERROR_SUBJECT[2],),
            capability_name=GMAIL_READ_ERROR_SUBJECT[2],
            adapter_id="module.plugin.gmail",
            module_name="plugin.gmail",
            operation="read_messages",
            invoker=invoker,
        )
        request = CommandRequest(
            request_id="d82-b03-single-shot",
            command="d82.connector.failure",
        )
        plan = ExecutionPlan(
            request_id=request.request_id,
            adapter_id="module.plugin.gmail",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="read_messages",
                    parameters={"content": "{}"},
                ),
            ),
            owner_approval_required=False,
        )

        result = adapter.execute(request, plan)

        self.assertEqual(calls, 1)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, code)


if __name__ == "__main__":
    unittest.main()
