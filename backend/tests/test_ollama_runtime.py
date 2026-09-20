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

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_load_model_uses_exact_preload_request_without_generation(
        self,
        urlopen: MagicMock,
    ) -> None:
        urlopen.return_value = response_with(
            {"response": "", "done": True, "done_reason": "load"}
        )
        client = OllamaRuntimeClient(base_url="http://local.example/")

        result = client.load_model("qwen3.5:9b")

        self.assertIsNone(result)
        self.assertEqual(urlopen.call_count, 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://local.example/api/generate")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "model": "qwen3.5:9b",
                "prompt": "",
                "stream": False,
                "keep_alive": -1,
            },
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 60.0)

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_unload_model_uses_exact_unload_request_without_generation(
        self,
        urlopen: MagicMock,
    ) -> None:
        urlopen.return_value = response_with(
            {"response": "", "done": True, "done_reason": "unload"}
        )
        client = OllamaRuntimeClient(base_url="http://local.example/")

        result = client.unload_model("qwen3.5:9b")

        self.assertIsNone(result)
        self.assertEqual(urlopen.call_count, 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "model": "qwen3.5:9b",
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
        )
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 60.0)

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_model_control_rejects_malformed_or_wrong_reason_response(
        self,
        urlopen: MagicMock,
    ) -> None:
        client = OllamaRuntimeClient(base_url="http://local")
        invalid_payloads = (
            {"response": "generated text", "done": True},
            {"response": "", "done": False},
            {"response": "", "done": True, "done_reason": "unload"},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                urlopen.reset_mock()
                urlopen.return_value = response_with(payload)
                with self.assertRaises(LocalAIRuntimeResponseError):
                    client.load_model("qwen3.5:9b")
                self.assertEqual(urlopen.call_count, 1)

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_model_control_timeout_is_single_attempt_and_translated(
        self,
        urlopen: MagicMock,
    ) -> None:
        urlopen.side_effect = socket.timeout("late")
        client = OllamaRuntimeClient(base_url="http://local")

        with self.assertRaises(LocalAIRuntimeTimeoutError):
            client.load_model("qwen3.5:9b")

        self.assertEqual(urlopen.call_count, 1)

    @patch("app.adapters.ollama_runtime.urlopen")
    def test_model_control_rejects_invalid_model_id_before_http(
        self,
        urlopen: MagicMock,
    ) -> None:
        client = OllamaRuntimeClient(base_url="http://local")

        for model_id in ("", " qwen3.5:9b", "qwen3.5:9b "):
            with self.subTest(model_id=model_id):
                with self.assertRaises(ValueError):
                    client.load_model(model_id)

        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
