from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_local_ai_control_execution_service
from app.api.v1.local_ai_control import router
from app.services.local_ai_config import LocalAIAdapterConfig
from app.services.local_ai_control_approval import (
    LocalAIControlApprovalService,
    LocalAIControlApprovalStore,
)
from app.services.local_ai_control_execution import (
    LocalAIControlExecutionService,
)
from app.services.local_ai_visibility import LocalAIRuntimeVisibilityService


HEADER = {"X-OAI-Local-Request": "1"}


class Runtime:
    def __init__(self) -> None:
        self.loaded = False
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.generate_calls = 0

    def is_runtime_available(self) -> bool:
        return True

    def is_model_available(self, model: str) -> bool:
        return model == "qwen3.5:9b"

    def list_models(self) -> tuple[str, ...]:
        return ("qwen3.5:9b",)

    def is_model_loaded(self, model: str) -> bool:
        return self.loaded

    def load_model(self, model_id: str) -> None:
        self.load_calls.append(model_id)
        self.loaded = True

    def unload_model(self, model_id: str) -> None:
        self.unload_calls.append(model_id)
        self.loaded = False

    def generate(self, *args: object, **kwargs: object) -> str:
        self.generate_calls += 1
        raise AssertionError("control API must not generate")


class LocalAIControlApiTests(unittest.TestCase):
    def setUp(self) -> None:
        cfg = LocalAIAdapterConfig(
            enabled=True,
            backend_id="ollama",
            model="qwen3.5:9b",
            base_url="http://secret-runtime.invalid:11434",
            timeout_seconds=30.0,
            context_length=4096,
        )
        self.runtime = Runtime()
        self.store = LocalAIControlApprovalStore(
            approval_id_factory=lambda: "api-proposal-1"
        )
        approval = LocalAIControlApprovalService(store=self.store)
        self.service = LocalAIControlExecutionService(
            config=cfg,
            runtime_client=self.runtime,
            visibility_service=LocalAIRuntimeVisibilityService(
                config=cfg,
                runtime_client=self.runtime,
            ),
            approval_service=approval,
            approval_store=self.store,
        )

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[
            get_local_ai_control_execution_service
        ] = lambda: self.service
        self.client = TestClient(app)

    def propose(self) -> dict:
        response = self.client.post(
            "/api/v1/local-ai/control/proposals",
            headers=HEADER,
            json={"operation": "load_configured_model"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def test_local_owner_marker_is_required(self) -> None:
        response = self.client.post(
            "/api/v1/local-ai/control/proposals",
            json={"operation": "load_configured_model"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.record_count, 0)

    def test_proposal_request_accepts_operation_only(self) -> None:
        forbidden_fields = (
            "model",
            "model_id",
            "backend_id",
            "base_url",
            "runtime_endpoint",
            "adapter_id",
            "workspace",
            "route_mode",
            "retry",
        )
        for field in forbidden_fields:
            with self.subTest(field=field):
                response = self.client.post(
                    "/api/v1/local-ai/control/proposals",
                    headers=HEADER,
                    json={
                        "operation": "load_configured_model",
                        field: "forbidden",
                    },
                )
                self.assertEqual(response.status_code, 422)

    def test_proposal_response_is_allowlisted_and_has_no_secret_runtime_data(
        self,
    ) -> None:
        data = self.propose()
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["proposal_id"], "api-proposal-1")
        self.assertEqual(
            data["preview"]["configured_model_id"],
            "qwen3.5:9b",
        )
        serialized = str(data).lower()
        for forbidden in (
            "secret-runtime",
            "base_url",
            "credential",
            "raw_error",
            "environment",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_deny_has_zero_mutation(self) -> None:
        proposal = self.propose()
        response = self.client.post(
            (
                "/api/v1/local-ai/control/proposals/"
                f"{proposal['proposal_id']}/decision"
            ),
            headers=HEADER,
            json={
                "decision": "denied",
                "control_digest": proposal["control_digest"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["decision"], "denied")
        self.assertEqual(data["status"], "not_executed")
        self.assertEqual(self.runtime.load_calls, [])
        self.assertEqual(self.runtime.generate_calls, 0)

    def test_approve_executes_exact_configured_model_once(self) -> None:
        proposal = self.propose()
        path = (
            "/api/v1/local-ai/control/proposals/"
            f"{proposal['proposal_id']}/decision"
        )
        response = self.client.post(
            path,
            headers=HEADER,
            json={
                "decision": "approved",
                "control_digest": proposal["control_digest"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["decision"], "approved")
        self.assertEqual(data["status"], "succeeded")
        self.assertEqual(self.runtime.load_calls, ["qwen3.5:9b"])
        self.assertEqual(self.runtime.generate_calls, 0)

        replay = self.client.post(
            path,
            headers=HEADER,
            json={
                "decision": "approved",
                "control_digest": proposal["control_digest"],
            },
        )
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(self.runtime.load_calls, ["qwen3.5:9b"])

    def test_decision_body_forbids_target_replacement_fields(self) -> None:
        proposal = self.propose()
        path = (
            "/api/v1/local-ai/control/proposals/"
            f"{proposal['proposal_id']}/decision"
        )
        for field in (
            "model",
            "backend_id",
            "base_url",
            "workspace",
            "retry",
        ):
            with self.subTest(field=field):
                response = self.client.post(
                    path,
                    headers=HEADER,
                    json={
                        "decision": "approved",
                        "control_digest": proposal["control_digest"],
                        field: "forbidden",
                    },
                )
                self.assertEqual(response.status_code, 422)

    def test_wrong_digest_fails_closed_and_consumes_ticket(self) -> None:
        proposal = self.propose()
        path = (
            "/api/v1/local-ai/control/proposals/"
            f"{proposal['proposal_id']}/decision"
        )
        wrong = self.client.post(
            path,
            headers=HEADER,
            json={
                "decision": "approved",
                "control_digest": "0" * 64,
            },
        )
        self.assertEqual(wrong.status_code, 409)

        replay = self.client.post(
            path,
            headers=HEADER,
            json={
                "decision": "approved",
                "control_digest": proposal["control_digest"],
            },
        )
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(self.runtime.load_calls, [])

    def test_main_router_registers_exact_d103_paths(self) -> None:
        from app.main import app

        paths = app.openapi()["paths"]
        self.assertIn(
            "/api/v1/local-ai/control/proposals",
            paths,
        )
        self.assertIn(
            "/api/v1/local-ai/control/proposals/{proposal_id}/decision",
            paths,
        )
        self.assertEqual(
            set(paths["/api/v1/local-ai/control/proposals"]),
            {"post"},
        )
        self.assertEqual(
            set(
                paths[
                    "/api/v1/local-ai/control/proposals/{proposal_id}/decision"
                ]
            ),
            {"post"},
        )


if __name__ == "__main__":
    unittest.main()
