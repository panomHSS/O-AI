import inspect
import unittest

from app.api import dependencies
from app.api.router import api_router
from app.api.v1.local_ai_visibility import local_ai_runtime_visibility, router
from app.schemas.local_ai_visibility import LocalAIRuntimeVisibilityResponse
from app.services.local_ai_config import LocalAIAdapterConfig


def _config(*, enabled: bool) -> LocalAIAdapterConfig:
    return LocalAIAdapterConfig(
        enabled=enabled,
        backend_id="ollama",
        model="model-a",
        base_url="http://127.0.0.1:11434",
        timeout_seconds=30.0,
        context_length=4096,
    )


class _Factory:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0

    def create(self, *, backend_id: str, base_url: str):
        self.calls += 1
        if self.error is not None:
            raise self.error
        raise AssertionError("runtime construction was not expected")


class _Service:
    def get_visibility(self):
        from app.contracts.local_ai_visibility import LocalAIRuntimeVisibility
        return LocalAIRuntimeVisibility(
            enabled=False,
            backend_id="ollama",
            runtime_status="disabled",
            configured_model_id="model-a",
            configured_model_installed=None,
            configured_model_loaded=None,
            model_discovery_status="not_checked",
            installed_models=(),
            reason_code="local_ai_disabled",
        )


class LocalAIVisibilityAPITests(unittest.TestCase):
    def test_public_schema_is_exact_allowlist(self) -> None:
        self.assertEqual(
            set(LocalAIRuntimeVisibilityResponse.model_fields),
            {
                "contract_version", "enabled", "backend_id", "runtime_status",
                "configured_model_id", "configured_model_installed",
                "configured_model_loaded", "model_discovery_status",
                "installed_models", "reason_code",
            },
        )
        forbidden = {"base_url", "access_token", "secret", "credential", "raw_error"}
        self.assertTrue(forbidden.isdisjoint(LocalAIRuntimeVisibilityResponse.model_fields))

    def test_route_is_exact_get_only_without_request_selector(self) -> None:
        matching = [r for r in router.routes if getattr(r, "path", None) == "/local-ai/runtime"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].methods, {"GET"})
        self.assertEqual(len(router.routes), 1)
        self.assertEqual(tuple(inspect.signature(local_ai_runtime_visibility).parameters), ("service",))

    def test_api_router_registers_exact_public_path_once(self) -> None:
        from app.main import app

        self.assertEqual(
            str(app.url_path_for("local_ai_runtime_visibility")),
            "/api/v1/local-ai/runtime",
        )
        matching = [p for p in app.openapi()["paths"] if "local-ai" in p]
        self.assertEqual(matching, ["/api/v1/local-ai/runtime"])
        self.assertEqual(
            set(app.openapi()["paths"]["/api/v1/local-ai/runtime"]),
            {"get"},
        )

    def test_disabled_visibility_does_not_construct_runtime(self) -> None:
        factory = _Factory()
        service = dependencies.get_local_ai_visibility_service(
            config=_config(enabled=False),
            factory=factory,
        )
        visibility = service.get_visibility()
        self.assertEqual(factory.calls, 0)
        self.assertEqual(visibility.runtime_status, "disabled")

    def test_factory_failure_fails_closed_without_raw_error(self) -> None:
        secret = "internal runtime secret detail"
        factory = _Factory(error=RuntimeError(secret))
        service = dependencies.get_local_ai_visibility_service(
            config=_config(enabled=True),
            factory=factory,
        )
        visibility = service.get_visibility()
        self.assertEqual(factory.calls, 1)
        self.assertEqual(visibility.runtime_status, "unavailable")
        self.assertEqual(visibility.reason_code, "runtime_unavailable")
        self.assertNotIn(secret, repr(visibility))

    def test_route_projects_contract_through_success_envelope(self) -> None:
        response = local_ai_runtime_visibility(_Service())
        rendered = response.model_dump()
        self.assertTrue(rendered["success"])
        self.assertEqual(rendered["data"]["runtime_status"], "disabled")
        self.assertNotIn("base_url", rendered["data"])


if __name__ == "__main__":
    unittest.main()
