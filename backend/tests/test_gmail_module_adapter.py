import json
import unittest

from app.adapters.gmail_module import GmailModuleAdapter
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.plugins.response import PluginResult


class RecordingInvoker:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return PluginResult(content='{"messages":[]}')


class GmailModuleAdapterTests(unittest.TestCase):
    def adapter(self, invoker):
        return GmailModuleAdapter(
            plugin_id="gmail",
            plugin_version="1.0.0",
            projected_capability_names=("read_messages",),
            capability_name="read_messages",
            adapter_id="module.plugin.gmail",
            module_name="plugin.gmail",
            operation="read_messages",
            invoker=invoker,
        )

    @staticmethod
    def request_plan(parameters, *, owner_approval_required=False):
        request = CommandRequest(request_id="r1", command="gmail")
        plan = ExecutionPlan(
            request_id="r1",
            adapter_id="module.plugin.gmail",
            steps=(ExecutionStep(sequence=1, operation="read_messages", parameters=parameters),),
            owner_approval_required=owner_approval_required,
        )
        return request, plan

    def test_exact_approved_query_is_forwarded_canonically(self):
        invoker = RecordingInvoker()
        request, plan = self.request_plan(
            {"mode": "from", "sender": "alice@example.com"}
        )
        result = self.adapter(invoker).execute(request, plan)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(len(invoker.calls), 1)
        self.assertEqual(
            json.loads(invoker.calls[0][-1]),
            {"mode": "from", "sender": "alice@example.com"},
        )

    def test_owner_approval_is_still_required(self):
        invoker = RecordingInvoker()
        request, plan = self.request_plan(
            {"mode": "recent"}, owner_approval_required=True
        )
        result = self.adapter(invoker).execute(request, plan)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "owner_approval_required")
        self.assertEqual(invoker.calls, [])

    def test_unknown_or_raw_query_parameters_fail_closed(self):
        for parameters in (
            {"content": "is:unread"},
            {"mode": "search", "q": "invoice"},
            {"mode": "recent", "maxResults": 100},
            {"mode": "from"},
        ):
            with self.subTest(parameters=parameters):
                invoker = RecordingInvoker()
                request, plan = self.request_plan(parameters)
                result = self.adapter(invoker).execute(request, plan)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error, "invalid_gmail_query")
                self.assertEqual(invoker.calls, [])


if __name__ == "__main__":
    unittest.main()
