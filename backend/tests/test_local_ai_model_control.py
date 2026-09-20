from __future__ import annotations

import inspect
import unittest

from app.contracts.local_ai_runtime import (
    LocalAIModelControlProvider,
    LocalAIRuntimeTimeoutError,
)
from app.services import local_ai_model_control as control_module
from app.services.local_ai_model_control import (
    LocalAIModelControlOperationInvalidError,
    LocalAIModelControlService,
    LocalAIModelControlUnsupportedError,
)


class StubControlProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.generate_calls = 0

    def load_model(self, model_id: str) -> None:
        self.load_calls.append(model_id)
        if self.fail:
            raise LocalAIRuntimeTimeoutError("bounded timeout")

    def unload_model(self, model_id: str) -> None:
        self.unload_calls.append(model_id)
        if self.fail:
            raise LocalAIRuntimeTimeoutError("bounded timeout")

    def generate(self, *args: object, **kwargs: object) -> str:
        self.generate_calls += 1
        raise AssertionError("control path must not generate")


class ReadOnlyRuntime:
    def is_runtime_available(self) -> bool:
        return True

    def is_model_available(self, model: str) -> bool:
        return True

    def is_model_loaded(self, model: str) -> bool:
        return False


class LocalAIModelControlServiceTests(unittest.TestCase):
    def test_provider_protocol_is_separate_and_runtime_checkable(self) -> None:
        provider = StubControlProvider()
        self.assertIsInstance(provider, LocalAIModelControlProvider)
        self.assertNotIsInstance(ReadOnlyRuntime(), LocalAIModelControlProvider)

    def test_load_dispatches_exact_configured_model_once(self) -> None:
        provider = StubControlProvider()
        service = LocalAIModelControlService(
            provider=provider,
            configured_model_id="qwen3.5:9b",
        )

        result = service.dispatch("load_configured_model")

        self.assertIsNone(result)
        self.assertEqual(provider.load_calls, ["qwen3.5:9b"])
        self.assertEqual(provider.unload_calls, [])
        self.assertEqual(provider.generate_calls, 0)

    def test_unload_dispatches_exact_configured_model_once(self) -> None:
        provider = StubControlProvider()
        service = LocalAIModelControlService(
            provider=provider,
            configured_model_id="qwen3.5:9b",
        )

        service.dispatch("unload_configured_model")

        self.assertEqual(provider.load_calls, [])
        self.assertEqual(provider.unload_calls, ["qwen3.5:9b"])
        self.assertEqual(provider.generate_calls, 0)

    def test_public_dispatch_has_no_model_selector(self) -> None:
        signature = inspect.signature(LocalAIModelControlService.dispatch)
        self.assertEqual(tuple(signature.parameters), ("self", "operation"))

    def test_unsupported_provider_fails_closed(self) -> None:
        with self.assertRaises(LocalAIModelControlUnsupportedError):
            LocalAIModelControlService(
                provider=ReadOnlyRuntime(),
                configured_model_id="qwen3.5:9b",
            )

    def test_unknown_operation_fails_before_mutation(self) -> None:
        provider = StubControlProvider()
        service = LocalAIModelControlService(
            provider=provider,
            configured_model_id="qwen3.5:9b",
        )

        with self.assertRaises(LocalAIModelControlOperationInvalidError):
            service.dispatch("switch_model")  # type: ignore[arg-type]

        self.assertEqual(provider.load_calls, [])
        self.assertEqual(provider.unload_calls, [])
        self.assertEqual(provider.generate_calls, 0)

    def test_provider_failure_is_not_retried(self) -> None:
        provider = StubControlProvider(fail=True)
        service = LocalAIModelControlService(
            provider=provider,
            configured_model_id="qwen3.5:9b",
        )

        with self.assertRaises(LocalAIRuntimeTimeoutError):
            service.dispatch("load_configured_model")

        self.assertEqual(provider.load_calls, ["qwen3.5:9b"])
        self.assertEqual(provider.unload_calls, [])
        self.assertEqual(provider.generate_calls, 0)

    def test_configured_model_id_is_server_owned_constructor_state(self) -> None:
        provider = StubControlProvider()

        with self.assertRaises(ValueError):
            LocalAIModelControlService(
                provider=provider,
                configured_model_id=" qwen3.5:9b",
            )

        service = LocalAIModelControlService(
            provider=provider,
            configured_model_id="qwen3.5:9b",
        )
        self.assertEqual(service.configured_model_id, "qwen3.5:9b")

    def test_service_has_no_chat_cloud_routing_or_persistence_authority(self) -> None:
        source = inspect.getsource(control_module)
        forbidden = (
            "LocalAIAdapter",
            "AIRouter",
            "Cloud",
            "ChatGPT",
            "Conversation",
            "WorkspaceAIPolicy",
            "Session",
            "Repository",
            "requests.",
            "httpx.",
            "urllib.",
            ".generate(",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
