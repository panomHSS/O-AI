import json
import unittest

from app.adapters.google_calendar_module import GoogleCalendarModuleAdapter
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.plugins.response import PluginResult


class RecordingInvoker:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return PluginResult(content='{"events":[],"truncated":false}')


class GoogleCalendarModuleAdapterTests(unittest.TestCase):
    def adapter(self, invoker):
        return GoogleCalendarModuleAdapter(
            plugin_id="google_calendar",
            plugin_version="1.0.0",
            projected_capability_names=("upcoming_events",),
            capability_name="upcoming_events",
            adapter_id="module.plugin.google_calendar",
            module_name="plugin.google_calendar",
            operation="list_upcoming_events",
            invoker=invoker,
        )

    @staticmethod
    def request_plan(parameters, *, owner_approval_required=False):
        request = CommandRequest(request_id="r1", command="calendar")
        plan = ExecutionPlan(
            request_id="r1",
            adapter_id="module.plugin.google_calendar",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="list_upcoming_events",
                    parameters=parameters,
                ),
            ),
            owner_approval_required=owner_approval_required,
        )
        return request, plan

    def test_exact_approved_boundaries_are_forwarded_without_recomputation(self):
        invoker = RecordingInvoker()
        adapter = self.adapter(invoker)
        parameters = {
            "time_min": "2026-09-16T00:00:00+07:00",
            "time_max": "2026-09-17T00:00:00+07:00",
        }
        request, plan = self.request_plan(parameters)

        result = adapter.execute(request, plan)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(len(invoker.calls), 1)
        forwarded = json.loads(invoker.calls[0][-1])
        self.assertEqual(forwarded, parameters)

    def test_owner_approval_gate_is_still_enforced(self):
        invoker = RecordingInvoker()
        request, plan = self.request_plan(
            {
                "time_min": "2026-09-16T00:00:00+07:00",
                "time_max": "2026-09-17T00:00:00+07:00",
            },
            owner_approval_required=True,
        )
        result = self.adapter(invoker).execute(request, plan)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "owner_approval_required")
        self.assertEqual(invoker.calls, [])

    def test_generic_content_and_invalid_or_oversized_windows_fail_closed(self):
        cases = (
            {"content": "upcoming"},
            {"time_min": "2026-09-16", "time_max": "2026-09-17"},
            {
                "time_min": "2026-09-17T00:00:00+07:00",
                "time_max": "2026-09-16T00:00:00+07:00",
            },
            {
                "time_min": "2026-09-01T00:00:00+07:00",
                "time_max": "2026-10-04T00:00:00+07:00",
            },
        )
        for parameters in cases:
            with self.subTest(parameters=parameters):
                invoker = RecordingInvoker()
                request, plan = self.request_plan(parameters)
                result = self.adapter(invoker).execute(request, plan)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error, "invalid_calendar_window")
                self.assertEqual(invoker.calls, [])


if __name__ == "__main__":
    unittest.main()
