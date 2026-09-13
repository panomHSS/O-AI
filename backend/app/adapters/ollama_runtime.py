"""Ollama implementation of the provider-neutral Local AI runtime client."""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.contracts.local_ai_runtime import (
    LocalAIRuntimeResponseError,
    LocalAIRuntimeTimeoutError,
    LocalAIRuntimeUnavailableError,
)


class OllamaRuntimeClient:
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

    def is_model_loaded(self, model: str) -> bool:
        payload = self._request_json("/api/ps", timeout_seconds=2.0)
        models = payload.get("models")
        if not isinstance(models, list):
            raise LocalAIRuntimeResponseError("Local AI runtime returned invalid process data.")
        return any(
            isinstance(item, dict) and item.get("name") == model
            for item in models
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
