from __future__ import annotations

import inspect
import unittest

from app.contracts.local_ai_runtime import LocalAIRuntimeTimeoutError
from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_control_approval import (
    LocalAIControlApprovalNotPendingError,
    LocalAIControlApprovalService,
    LocalAIControlApprovalStore,
)
from app.services.local_ai_control_execution import (
    LocalAIControlExecutionError,
    LocalAIControlExecutionService,
)
from app.services.local_ai_visibility import LocalAIRuntimeVisibilityService


def config(*, model: str = "qwen3.5:9b") -> LocalAIAdapterConfig:
    return LocalAIAdapterConfig(
        enabled=True,
        backend_id="ollama",
        model=model,
        base_url="http://127.0.0.1:11434",
        timeout_seconds=30.0,
        context_length=4096,
    )


class MutableRuntime:
    def __init__(
        self,
        *,
        model: str = "qwen3.5:9b",
        loaded: bool = False,
        fail_control: bool = False,
        offline_after_control: bool = False,
    ) -> None:
        self.model = model
        self.loaded = loaded
        self.fail_control = fail_control
        self.offline_after_control = offline_after_control
        self.online = True
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        return self.online

    def is_model_available(self, model: str) -> bool:
        return model == self.model

    def list_models(self) -> tuple[str, ...]:
        return (self.model,)

    def is_model_loaded(self, model: str) -> bool:
        if model != self.model:
            return False
        return self.loaded

    def load_model(self, model_id: str) -> None:
        self.load_calls.append(model_id)
        if self.fail_control:
            raise LocalAIRuntimeTimeoutError("ambiguous timeout")
        self.loaded = True
        if self.offline_after_control:
            self.online = False

    def unload_model(self, model_id: str) -> None:
        self.unload_calls.append(model_id)
        if self.fail_control:
            raise LocalAIRuntimeTimeoutError("ambiguous timeout")
        self.loaded = False
        if self.offline_after_control:
            self.online = False

    def generate(self, *args: object, **kwargs: object) -> str:
        self.generate_calls += 1
        raise AssertionError("control path must not generate")


class ReadOnlyRuntime:
    def is_runtime_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("qwen3.5:9b",)

    def is_model_loaded(self, model: str) -> bool:
        return False


class LocalAIControlExecutionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = LocalAIControlApprovalStore(
            approval_id_factory=lambda: "proposal-1"
        )
        self.approval = LocalAIControlApprovalService(store=self.store)

    def service(
        self,
        runtime: object,
        *,
        current_config: LocalAIAdapterConfig | None = None,
    ) -> LocalAIControlExecutionService:
        cfg = current_config or config()
        visibility = LocalAIRuntimeVisibilityService(
            config=cfg,
            runtime_client=runtime,  # type: ignore[arg-type]
        )
        return LocalAIControlExecutionService(
            config=cfg,
            runtime_client=runtime,
            visibility_service=visibility,
            approval_service=self.approval,
            approval_store=self.store,
        )

    def test_proposal_uses_exact_server_owned_model_and_state(self) -> None:
        runtime = MutableRuntime(loaded=False)
        proposal = self.service(runtime).propose(
            "load_configured_model"
        ).proposal
        self.assertEqual(proposal.preview.backend_id, "ollama")
        self.assertEqual(
            proposal.preview.configured_model_id,
            "qwen3.5:9b",
        )
        self.assertFalse(proposal.preview.expected_loaded_state)
        self.assertTrue(proposal.preview.desired_loaded_state)
        self.assertEqual(runtime.load_calls, [])
        self.assertEqual(runtime.generate_calls, 0)

    def test_proposal_fails_closed_for_unsupported_control_provider(self) -> None:
        with self.assertRaises(LocalAIControlExecutionError) as caught:
            self.service(ReadOnlyRuntime()).propose(
                "load_configured_model"
            )
        self.assertEqual(
            caught.exception.reason_code,
            "local_ai_model_control_unsupported",
        )

    def test_deny_is_terminal_with_zero_mutation(self) -> None:
        runtime = MutableRuntime(loaded=False)
        service = self.service(runtime)
        proposal = service.propose("load_configured_model").proposal

        outcome = service.decide(
            proposal.approval_id,
            decision="denied",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.decision, "denied")
        self.assertEqual(outcome.status, "not_executed")
        self.assertEqual(outcome.reason_code, "owner_denied")
        self.assertEqual(runtime.load_calls, [])
        self.assertEqual(runtime.generate_calls, 0)

    def test_approved_load_claims_and_mutates_exactly_once(self) -> None:
        runtime = MutableRuntime(loaded=False)
        service = self.service(runtime)
        proposal = service.propose("load_configured_model").proposal

        outcome = service.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.status, "succeeded")
        self.assertTrue(runtime.loaded)
        self.assertEqual(runtime.load_calls, ["qwen3.5:9b"])
        self.assertEqual(runtime.unload_calls, [])
        self.assertEqual(runtime.generate_calls, 0)

        with self.assertRaises(LocalAIControlApprovalNotPendingError):
            service.decide(
                proposal.approval_id,
                decision="approved",
                control_digest=proposal.control_digest,
            )
        self.assertEqual(runtime.load_calls, ["qwen3.5:9b"])

    def test_approved_unload_mutates_exactly_once(self) -> None:
        runtime = MutableRuntime(loaded=True)
        service = self.service(runtime)
        proposal = service.propose("unload_configured_model").proposal
        outcome = service.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertFalse(runtime.loaded)
        self.assertEqual(runtime.unload_calls, ["qwen3.5:9b"])
        self.assertEqual(runtime.generate_calls, 0)

    def test_state_drift_before_approval_fails_without_mutation(self) -> None:
        runtime = MutableRuntime(loaded=False)
        service = self.service(runtime)
        proposal = service.propose("load_configured_model").proposal
        runtime.loaded = True

        outcome = service.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.status, "failed")
        self.assertEqual(
            outcome.reason_code,
            "local_ai_control_state_conflict",
        )
        self.assertEqual(runtime.load_calls, [])

    def test_config_drift_before_approval_fails_without_mutation(self) -> None:
        runtime = MutableRuntime(model="qwen3.5:9b", loaded=False)
        first = self.service(runtime)
        proposal = first.propose("load_configured_model").proposal

        changed_runtime = MutableRuntime(model="other-model", loaded=False)
        second = self.service(
            changed_runtime,
            current_config=config(model="other-model"),
        )
        outcome = second.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.status, "failed")
        self.assertEqual(
            outcome.reason_code,
            "local_ai_control_configuration_changed",
        )
        self.assertEqual(changed_runtime.load_calls, [])

    def test_provider_timeout_is_indeterminate_and_not_retried(self) -> None:
        runtime = MutableRuntime(loaded=False, fail_control=True)
        service = self.service(runtime)
        proposal = service.propose("load_configured_model").proposal

        outcome = service.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.status, "indeterminate")
        self.assertEqual(runtime.load_calls, ["qwen3.5:9b"])
        self.assertEqual(runtime.generate_calls, 0)

    def test_post_dispatch_observation_failure_is_indeterminate(self) -> None:
        runtime = MutableRuntime(
            loaded=False,
            offline_after_control=True,
        )
        service = self.service(runtime)
        proposal = service.propose("load_configured_model").proposal

        outcome = service.decide(
            proposal.approval_id,
            decision="approved",
            control_digest=proposal.control_digest,
        )

        self.assertEqual(outcome.status, "indeterminate")
        self.assertEqual(runtime.load_calls, ["qwen3.5:9b"])

    def test_service_has_no_chat_cloud_routing_or_persistence_authority(self) -> None:
        from app.services import local_ai_control_execution as module

        source = inspect.getsource(module)
        for marker in (
            "ChatGPT",
            "AIRouter",
            "WorkspaceAIPolicy",
            "ConversationService",
            "ChatService",
            "Repository",
            "Session",
            ".generate(",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
