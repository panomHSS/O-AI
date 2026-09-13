import json
import socket
import unittest
from unittest.mock import MagicMock, patch

from app.adapters.ollama_runtime import OllamaRuntimeClient
from app.contracts.local_ai_runtime import (
    LocalAIRuntimeResponseError,
    LocalAIRuntimeTimeoutError,
)


def response_with(payload: object) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    return response


class OllamaRuntimeClientTests(unittest.TestCase):
    @patch("app.adapters.ollama_runtime.urlopen")
    def test_generate_maps_request_and_response(self, urlopen: MagicMock) -> None:
        urlopen.return_value = response_with({"response": " local response "})
        client = OllamaRuntimeClient(base_url="http://local.example/")

        result = client.generate(
            model="local-model",
            prompt="hello",
            timeout_seconds=9.5,
            context_length=2048,
        )

        self.assertEqual(result, "local response")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://local.example/api/generate")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "model": "local-model",
                "prompt": "hello",
                "stream": False,
                "options": {"num_ctx": 2048},
            },
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 9.5)

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_timeout_is_translated(self, urlopen: MagicMock) -> None:
        urlopen.side_effect = socket.timeout("late")

        with self.assertRaises(LocalAIRuntimeTimeoutError):
            OllamaRuntimeClient(base_url="http://local").generate(
                model="model",
                prompt="hello",
                timeout_seconds=1,
                context_length=256,
            )

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_empty_or_malformed_response_is_rejected(self, urlopen: MagicMock) -> None:
        for payload in ({"response": " "}, ["not-an-object"]):
            with self.subTest(payload=payload):
                urlopen.return_value = response_with(payload)
                with self.assertRaises(LocalAIRuntimeResponseError):
                    OllamaRuntimeClient(base_url="http://local").generate(
                        model="model",
                        prompt="hello",
                        timeout_seconds=1,
                        context_length=256,
                    )

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_model_availability_uses_runtime_tags(self, urlopen: MagicMock) -> None:
        urlopen.return_value = response_with({"models": [{"name": "qwen"}]})
        client = OllamaRuntimeClient(base_url="http://local")

        self.assertTrue(client.is_runtime_available())
        self.assertTrue(client.is_model_available("qwen"))
        self.assertFalse(client.is_model_available("other"))


if __name__ == "__main__":
    unittest.main()
