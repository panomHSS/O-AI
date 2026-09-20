"""Ollama implementation of the provider-neutral Local AI runtime client."""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.contracts.local_ai_runtime import (
    LocalAIModelControlProvider,
    LocalAIRuntimeResponseError,
    LocalAIRuntimeTimeoutError,
    LocalAIRuntimeUnavailableError,
)


class OllamaRuntimeClient(LocalAIModelControlProvider):
    """Small HTTP client for a configured Ollama deployment."""

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def is_runtime_available(self) -> bool:
        try:
            self._request_json("/api/tags", timeout_seconds=2.0)
        except (
            LocalAIRuntimeUnavailableError,
            LocalAIRuntimeTimeoutError,
            LocalAIRuntimeResponseError,
        ):
            return False
        return True

    def is_model_available(self, model: str) -> bool:
        payload = self._request_json("/api/tags", timeout_seconds=2.0)
        models = payload.get("models")
        if not isinstance(models, list):
            raise LocalAIRuntimeResponseError("Local AI runtime returned invalid model data.")
        return any(
            isinstance(item, dict) and item.get("name") == model
            for item in models
        )

    def list_models(self) -> tuple[str, ...]:
        """Return installed Ollama model names without loading or generating."""
        payload = self._request_json("/api/tags", timeout_seconds=2.0)
        models = payload.get("models")
        if not isinstance(models, list):
            raise LocalAIRuntimeResponseError(
                "Local AI runtime returned invalid model data."
            )

        names: list[str] = []
        for item in models:
            if not isinstance(item, dict):
                raise LocalAIRuntimeResponseError(
                    "Local AI runtime returned invalid model data."
                )
            name = item.get("name")
            if not isinstance(name, str) or not name or name != name.strip():
                raise LocalAIRuntimeResponseError(
                    "Local AI runtime returned invalid model data."
                )
            names.append(name)

        return tuple(sorted(set(names)))

    def is_model_loaded(self, model: str) -> bool:
        payload = self._request_json("/api/ps", timeout_seconds=2.0)
        models = payload.get("models")
        if not isinstance(models, list):
            raise LocalAIRuntimeResponseError("Local AI runtime returned invalid process data.")
        return any(
            isinstance(item, dict) and item.get("name") == model
            for item in models
        )

    def load_model(self, model_id: str) -> None:
        """Preload exactly one model and keep it resident; never generate text."""
        self._validate_control_model_id(model_id)
        payload = self._request_json(
            "/api/generate",
            timeout_seconds=60.0,
            body={
                "model": model_id,
                "prompt": "",
                "stream": False,
                "keep_alive": -1,
            },
        )
        self._validate_control_response(
            payload,
            expected_done_reason="load",
        )

    def unload_model(self, model_id: str) -> None:
        """Unload exactly one model immediately; never generate text."""
        self._validate_control_model_id(model_id)
        payload = self._request_json(
            "/api/generate",
            timeout_seconds=60.0,
            body={
                "model": model_id,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
        )
        self._validate_control_response(
            payload,
            expected_done_reason="unload",
        )

    @staticmethod
    def _validate_control_model_id(model_id: object) -> str:
        if (
            not isinstance(model_id, str)
            or not model_id
            or model_id != model_id.strip()
        ):
            raise ValueError("model_id must be a non-empty trimmed string.")
        return model_id

    @staticmethod
    def _validate_control_response(
        payload: dict[str, Any],
        *,
        expected_done_reason: str,
    ) -> None:
        if payload.get("done") is not True or payload.get("response") != "":
            raise LocalAIRuntimeResponseError(
                "Local AI runtime returned an invalid model control response."
            )
        done_reason = payload.get("done_reason")
        if done_reason is not None and done_reason != expected_done_reason:
            raise LocalAIRuntimeResponseError(
                "Local AI runtime returned an invalid model control response."
            )

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        timeout_seconds: float,
        context_length: int,
    ) -> str:
        payload = self._request_json(
            "/api/generate",
            timeout_seconds=timeout_seconds,
            body={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": context_length},
            },
        )
        response = payload.get("response")
        if not isinstance(response, str) or not response.strip():
            raise LocalAIRuntimeResponseError(
                "Local AI runtime returned an empty or malformed response."
            )
        return response.strip()

    def _request_json(
        self,
        path: str,
        *,
        timeout_seconds: float,
        body: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        request = Request(
            f"{self._base_url}{path}",
            data=(json.dumps(body).encode("utf-8") if body is not None else None),
            headers={"Content-Type": "application/json"} if body is not None else {},
            method="POST" if body is not None else "GET",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as error:
            raise LocalAIRuntimeTimeoutError("Local AI runtime timed out.") from error
        except (URLError, OSError) as error:
            raise LocalAIRuntimeUnavailableError("Local AI runtime is unavailable.") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LocalAIRuntimeResponseError(
                "Local AI runtime returned malformed JSON."
            ) from error

        if not isinstance(payload, dict):
            raise LocalAIRuntimeResponseError("Local AI runtime returned malformed JSON.")
        return payload
