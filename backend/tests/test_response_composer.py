import unittest

from app.adapters.local_ai import LocalAIResponseError, LocalAIUnavailableError
from app.contracts.ai import AIResult
from app.contracts.ai_route import AIRouteDecision, LOCAL_AI_ADAPTER_ID
from app.contracts.command import Result
from app.contracts.response_composition import NormalizedError
from app.contracts.tool_module_route import ToolModuleRouteDecision
from app.providers.base import ChatConfigurationError, ChatProviderError
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer


class ResponseComposerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = OrchestrationErrorNormalizer()
        self.composer = ResponseComposer(self.normalizer)

    def test_ai_success_composes_response_and_preserves_request_id(self) -> None:
        response = self.composer.compose_ai_success("request-1", AIResult(content="answer"))

        self.assertEqual(response.request_id, "request-1")
        self.assertEqual(response.message, "answer")
        self.assertEqual(
            response.result,
            Result("request-1", "succeeded", output={"content": "answer"}),
        )

    def test_tool_success_composes_response_and_preserves_result(self) -> None:
        response = self.composer.compose_tool_result(
            Result("request-1", "succeeded", output={"value": "echo"})
        )

        self.assertEqual(response.request_id, "request-1")
        self.assertEqual(response.result.output, {"value": "echo"})
        self.assertEqual(response.result.status, "succeeded")

    def test_blocked_is_distinct_from_failed(self) -> None:
        response = self.composer.compose_error(
            NormalizedError("request-1", "OWNER_APPROVAL_REQUIRED", "blocked")
        )

        self.assertEqual(response.result.status, "blocked")
        self.assertEqual(response.result.error, "OWNER_APPROVAL_REQUIRED")

    def test_d24_route_outcomes_are_normalized_safely(self) -> None:
        cases = (
            (
                AIRouteDecision("request-1", "unavailable", LOCAL_AI_ADAPTER_ID, None, "local_ai_unavailable"),
                "LOCAL_AI_UNAVAILABLE",
            ),
            (AIRouteDecision("request-1", "rejected", None, None, "rejected"), "AI_ROUTE_REJECTED"),
        )
        for route, code in cases:
            with self.subTest(route=route):
                normalized = self.normalizer.normalize_ai_route(route)
                self.assertIsNotNone(normalized)
                self.assertEqual(normalized.code, code)  # type: ignore[union-attr]

    def test_d27_route_outcomes_are_normalized_safely(self) -> None:
        cases = (
            ("unavailable", "TOOL_ROUTE_UNAVAILABLE", "failed"),
            ("blocked", "OWNER_APPROVAL_REQUIRED", "blocked"),
            ("rejected", "TOOL_ROUTE_REJECTED", "failed"),
        )
        for status, code, result_status in cases:
            with self.subTest(status=status):
                normalized = self.normalizer.normalize_tool_route(
                    ToolModuleRouteDecision("request-1", status, None, "test")  # type: ignore[arg-type]
                )
                self.assertIsNotNone(normalized)
                self.assertEqual(
                    (normalized.code, normalized.status),  # type: ignore[union-attr]
                    (code, result_status),
                )

    def test_chatgpt_and_local_ai_errors_have_safe_codes(self) -> None:
        cases = (
            (ChatConfigurationError("secret configuration"), "CHATGPT_NOT_CONFIGURED"),
            (ChatProviderError("provider secret"), "CHATGPT_UNAVAILABLE"),
            (LocalAIUnavailableError("private host"), "LOCAL_AI_UNAVAILABLE"),
            (LocalAIResponseError("private response"), "LOCAL_AI_RESPONSE_FAILED"),
        )
        for error, code in cases:
            with self.subTest(error=error):
                normalized = self.normalizer.normalize_exception("request-1", error)
                self.assertEqual(normalized.code, code)
                self.assertNotIn(str(error), self.composer.compose_error(normalized).message)

    def test_failed_tool_result_hides_raw_error_detail(self) -> None:
        response = self.composer.compose_tool_result(
            Result("request-1", "failed", error="token=very-secret adapter failure")
        )

        self.assertEqual(response.result.error, "TOOL_EXECUTION_FAILED")
        self.assertNotIn("very-secret", response.message)
        self.assertNotIn("very-secret", response.result.error or "")

    def test_unknown_exception_and_malformed_outcome_fail_closed(self) -> None:
        error = RuntimeError("untrusted internal detail")
        normalized = self.normalizer.normalize_exception("request-1", error)
        malformed = self.normalizer.normalize_tool_route(object())

        self.assertEqual(normalized.code, "INTERNAL_ERROR")
        self.assertNotIn(str(error), self.composer.compose_error(normalized).message)
        self.assertEqual(malformed.code, "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
