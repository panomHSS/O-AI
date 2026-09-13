import unittest

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command_decision import CommandDecision
from app.services.ai_router import AIRouter


def decision(
    *,
    disposition: str = "defer_to_existing_chat",
    preference: str = "unspecified",
    intent: str = "chat_message",
) -> CommandDecision:
    return CommandDecision(
        request_id="request-1",
        intent=intent,  # type: ignore[arg-type]
        disposition=disposition,  # type: ignore[arg-type]
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code="test",
    )


class AIRouterTests(unittest.TestCase):
    def test_rejected_decision_is_rejected(self) -> None:
        route = AIRouter().route(decision(disposition="reject", intent="unknown"))
        self.assertEqual(
            (route.status, route.adapter_id, route.selection_source),
            ("rejected", None, None),
        )

    def test_unspecified_and_automatic_use_default_chatgpt_route(self) -> None:
        for preference in ("unspecified", "automatic"):
            with self.subTest(preference=preference):
                route = AIRouter().route(decision(preference=preference))
                self.assertEqual(route.status, "selected")
                self.assertEqual(route.adapter_id, CHATGPT_DEFAULT_ADAPTER_ID)
                self.assertEqual(
                    route.selection_source,
                    "automatic" if preference == "automatic" else "default",
                )

    def test_explicit_local_ai_is_unavailable_without_fallback(self) -> None:
        route = AIRouter().route(decision(preference="local_ai_explicit"))
        self.assertEqual(route.status, "unavailable")
        self.assertEqual(route.adapter_id, LOCAL_AI_ADAPTER_ID)
        self.assertIsNone(route.selection_source)

    def test_available_local_ai_is_selected_without_invocation(self) -> None:
        route = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        ).route(decision(preference="local_ai_explicit"))
        self.assertEqual(route.status, "selected")
        self.assertEqual(route.adapter_id, LOCAL_AI_ADAPTER_ID)
        self.assertEqual(route.selection_source, "explicit")

    def test_configured_default_adapter_is_provider_neutral(self) -> None:
        route = AIRouter(
            default_adapter_id="example.default",
            local_ai_adapter_id="example.local",
            available_adapter_ids=("example.default",),
        ).route(decision())

        self.assertEqual(route.status, "selected")
        self.assertEqual(route.adapter_id, "example.default")
        self.assertEqual(route.selection_source, "default")

    def test_malformed_or_unsupported_decision_fails_closed(self) -> None:
        for item in (
            object(),
            decision(disposition="unexpected"),
            decision(preference="unexpected"),
            decision(intent="unknown"),
        ):
            with self.subTest(item=item):
                route = AIRouter().route(item)  # type: ignore[arg-type]
                self.assertEqual(
                    (route.status, route.adapter_id, route.selection_source),
                    ("rejected", None, None),
                )


if __name__ == "__main__":
    unittest.main()
