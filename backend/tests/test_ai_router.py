import unittest

from app.contracts.ai_route import (
    CHATGPT_DEFAULT_ADAPTER_ID,
    LOCAL_AI_ADAPTER_ID,
)
from app.contracts.command import CommandRequest
from app.contracts.command_decision import CommandDecision
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import (
    WorkspaceAIRouteMode,
    WorkspaceAIRoutingPolicy,
)
from app.services.ai_router import AIRouter
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import CHAT_MESSAGE_COMMAND


def decision(
    *,
    disposition: str = "defer_to_existing_chat",
    preference: str = "unspecified",
    intent: str = "chat_message",
    reason_code: str = "test",
) -> CommandDecision:
    return CommandDecision(
        request_id="request-1",
        intent=intent,  # type: ignore[arg-type]
        disposition=disposition,  # type: ignore[arg-type]
        provider_preference_hint=preference,  # type: ignore[arg-type]
        reason_code=reason_code,
    )


def workspace_policy(
    mode: WorkspaceAIRouteMode,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> WorkspaceAIRoutingPolicy:
    return WorkspaceAIRoutingPolicy(
        workspace_id=workspace_id,
        mode=mode,
    )


class AIRouterTests(unittest.TestCase):
    def test_rejected_decision_is_rejected(self) -> None:
        route = AIRouter().route(
            decision(disposition="reject", intent="unknown")
        )
        self.assertEqual(
            (route.status, route.adapter_id, route.selection_source),
            ("rejected", None, None),
        )

    def test_conflicting_decision_preserves_fail_closed_reason(self) -> None:
        route = AIRouter().route(
            decision(
                disposition="reject",
                reason_code="conflicting_provider_preference",
            )
        )
        self.assertEqual(route.status, "rejected")
        self.assertEqual(
            route.reason_code,
            "conflicting_provider_preference",
        )

    def test_unspecified_and_automatic_use_legacy_default_chatgpt_route(self) -> None:
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

    def test_explicit_cloud_requires_workspace_policy_on_legacy_path(self) -> None:
        route = AIRouter().route(decision(preference="cloud_ai_explicit"))
        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            ("rejected", None, "workspace_ai_policy_required"),
        )

    def test_natural_thai_local_ai_request_fails_closed_without_fallback(
        self,
    ) -> None:
        command = CommandRequest(
            request_id="request-1",
            command=CHAT_MESSAGE_COMMAND,
            arguments={
                "message": "ใช้ Local AI ตอบข้อนี้: อธิบาย recursion",
            },
        )
        decision_result = CommandDecisionEngine().decide(command)
        self.assertEqual(
            decision_result.provider_preference_hint,
            "local_ai_explicit",
        )
        route = AIRouter().route(decision_result)
        self.assertEqual(route.status, "unavailable")
        self.assertEqual(route.adapter_id, LOCAL_AI_ADAPTER_ID)
        self.assertIsNone(route.selection_source)
        self.assertEqual(route.reason_code, "local_ai_unavailable")

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

    def test_company_local_only_default_selects_local_when_available(self) -> None:
        router = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        )
        route = router.route(
            decision(),
            workspace_policy(
                WorkspaceAIRouteMode.LOCAL_ONLY,
                WorkspaceId.COMPANY,
            ),
        )
        self.assertEqual(
            (
                route.status,
                route.adapter_id,
                route.selection_source,
                route.reason_code,
            ),
            (
                "selected",
                LOCAL_AI_ADAPTER_ID,
                "default",
                "workspace_configured_default",
            ),
        )

    def test_company_local_only_explicit_cloud_is_policy_rejected(self) -> None:
        router = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        )
        route = router.route(
            decision(preference="cloud_ai_explicit"),
            workspace_policy(
                WorkspaceAIRouteMode.LOCAL_ONLY,
                WorkspaceId.COMPANY,
            ),
        )
        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            ("rejected", None, "workspace_cloud_egress_denied"),
        )

    def test_cloud_only_explicit_local_is_policy_rejected(self) -> None:
        router = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        )
        route = router.route(
            decision(preference="local_ai_explicit"),
            workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        )
        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            ("rejected", None, "workspace_local_ai_not_permitted"),
        )

    def test_local_preferred_automatic_uses_workspace_default(self) -> None:
        router = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        )
        route = router.route(
            decision(preference="automatic"),
            workspace_policy(WorkspaceAIRouteMode.LOCAL_PREFERRED),
        )
        self.assertEqual(
            (
                route.status,
                route.adapter_id,
                route.selection_source,
            ),
            (
                "selected",
                LOCAL_AI_ADAPTER_ID,
                "automatic",
            ),
        )

    def test_unavailable_local_does_not_fallback_to_cloud(self) -> None:
        router = AIRouter(
            available_adapter_ids=(CHATGPT_DEFAULT_ADAPTER_ID,)
        )
        route = router.route(
            decision(),
            workspace_policy(
                WorkspaceAIRouteMode.LOCAL_ONLY,
                WorkspaceId.COMPANY,
            ),
        )
        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            (
                "unavailable",
                LOCAL_AI_ADAPTER_ID,
                "local_ai_unavailable",
            ),
        )

    def test_unavailable_cloud_does_not_fallback_to_local(self) -> None:
        router = AIRouter(
            available_adapter_ids=(LOCAL_AI_ADAPTER_ID,)
        )
        route = router.route(
            decision(),
            workspace_policy(WorkspaceAIRouteMode.CLOUD_ONLY),
        )
        self.assertEqual(
            (route.status, route.adapter_id, route.reason_code),
            (
                "unavailable",
                CHATGPT_DEFAULT_ADAPTER_ID,
                "cloud_ai_unavailable",
            ),
        )

    def test_explicit_alternate_is_allowed_only_in_preferred_modes(self) -> None:
        router = AIRouter(
            available_adapter_ids=(
                CHATGPT_DEFAULT_ADAPTER_ID,
                LOCAL_AI_ADAPTER_ID,
            )
        )
        personal_local = router.route(
            decision(preference="local_ai_explicit"),
            workspace_policy(WorkspaceAIRouteMode.CLOUD_PREFERRED),
        )
        company_cloud = router.route(
            decision(preference="cloud_ai_explicit"),
            workspace_policy(
                WorkspaceAIRouteMode.LOCAL_PREFERRED,
                WorkspaceId.COMPANY,
            ),
        )
        self.assertEqual(
            (personal_local.status, personal_local.adapter_id),
            ("selected", LOCAL_AI_ADAPTER_ID),
        )
        self.assertEqual(
            (company_cloud.status, company_cloud.adapter_id),
            ("selected", CHATGPT_DEFAULT_ADAPTER_ID),
        )

    def test_configured_legacy_default_adapter_is_provider_neutral(self) -> None:
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
