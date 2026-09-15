import json
import socket
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

from app.connectors.github_public_repository import (
    GITHUB_CONNECTOR_ERROR_HTTP,
    GITHUB_CONNECTOR_ERROR_INVALID_JSON,
    GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE,
    GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
    GITHUB_CONNECTOR_ERROR_NETWORK,
    GITHUB_CONNECTOR_ERROR_RESPONSE_TOO_LARGE,
    GITHUB_CONNECTOR_ERROR_TIMEOUT,
    GITHUB_PUBLIC_REPOSITORY_MAX_RESPONSE_BYTES,
    GitHubPublicRepositoryClient,
    GitHubPublicRepositoryConnectorError,
    _NoRedirectHandler,
    _open_without_redirects,
    validate_repository_reference,
)


def valid_payload(**changes):
    payload = {
        "full_name": "openai/openai-python",
        "description": "The official Python library for the OpenAI API.",
        "default_branch": "main",
        "language": "Python",
        "private": False,
        "archived": False,
        "fork": False,
        "stargazers_count": 100,
        "forks_count": 20,
        "open_issues_count": 5,
        "license": {"spdx_id": "Apache-2.0"},
        "updated_at": "2026-09-15T00:00:00Z",
        "html_url": "https://malicious.example/ignored",
    }
    payload.update(changes)
    return payload


class FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200) -> None:
        self._body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int) -> bytes:
        return self._body[:limit]


class RecordingTransport:
    def __init__(
        self,
        *,
        payload=None,
        body: bytes | None = None,
        status: int = 200,
        error: Exception | None = None,
    ) -> None:
        self.calls = 0
        self.requests = []
        self.timeouts = []
        self.error = error
        if body is not None:
            self.body = body
        else:
            source = valid_payload() if payload is None else payload
            self.body = json.dumps(source).encode("utf-8")
        self.status = status

    def __call__(self, request, timeout):
        self.calls += 1
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.body, status=self.status)


class GitHubPublicRepositoryConnectorTests(unittest.TestCase):
    def test_reference_validation_accepts_bounded_owner_repository(self):
        self.assertEqual(
            validate_repository_reference("openai/openai-python"),
            ("openai", "openai-python"),
        )

    def test_reference_validation_rejects_url_and_unsafe_shapes(self):
        invalid = (
            "",
            " openai/openai-python",
            "openai/openai-python ",
            "https://github.com/openai/openai-python",
            "openai",
            "a/b/c",
            "openai/../secret",
            "openai/repo?x=1",
            "openai/repo#x",
            "openai/repo:443",
            "openai/repo@evil",
            "openai/repo%",
            "openai/repo\\evil",
            "openai/.hidden.",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
                    validate_repository_reference(value)
                self.assertEqual(
                    caught.exception.code,
                    GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE,
                )

    def test_exact_get_request_uses_fixed_https_host_and_path(self):
        transport = RecordingTransport()
        client = GitHubPublicRepositoryClient(transport=transport)
        client.get_repository_metadata("openai/openai-python")
        self.assertEqual(transport.calls, 1)
        request = transport.requests[0]
        self.assertEqual(
            request.full_url,
            "https://api.github.com/repos/openai/openai-python",
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(transport.timeouts, [5.0])

    def test_default_transport_disables_environment_proxy_routing(self):
        request = urllib.request.Request(
            "https://api.github.com/repos/openai/openai-python",
            method="GET",
        )
        opener = Mock()
        sentinel = object()
        opener.open.return_value = sentinel

        with patch(
            "app.connectors.github_public_repository.urllib.request.build_opener",
            return_value=opener,
        ) as build_opener:
            result = _open_without_redirects(request, 5.0)

        self.assertIs(result, sentinel)
        handlers = build_opener.call_args.args
        self.assertEqual(len(handlers), 2)
        self.assertIsInstance(handlers[0], urllib.request.ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _NoRedirectHandler)
        opener.open.assert_called_once_with(request, timeout=5.0)

    def test_request_headers_contain_no_credentials(self):
        transport = RecordingTransport()
        client = GitHubPublicRepositoryClient(transport=transport)
        client.get_repository_metadata("openai/openai-python")
        headers = {
            key.casefold(): value
            for key, value in transport.requests[0].header_items()
        }
        self.assertIn("accept", headers)
        self.assertIn("user-agent", headers)
        self.assertNotIn("authorization", headers)
        self.assertNotIn("cookie", headers)
        self.assertNotIn("proxy-authorization", headers)

    def test_success_normalizes_whitelisted_metadata(self):
        transport = RecordingTransport()
        client = GitHubPublicRepositoryClient(transport=transport)
        result = client.get_repository_metadata("openai/openai-python")
        self.assertEqual(result.full_name, "openai/openai-python")
        self.assertEqual(
            result.html_url,
            "https://github.com/openai/openai-python",
        )
        self.assertEqual(result.visibility, "public")
        self.assertEqual(result.license, "Apache-2.0")
        self.assertEqual(result.stargazers_count, 100)
        self.assertFalse(hasattr(result, "owner"))
        self.assertFalse(hasattr(result, "permissions"))

    def test_external_html_url_is_ignored(self):
        transport = RecordingTransport(
            payload=valid_payload(html_url="https://evil.invalid/redirect-me")
        )
        client = GitHubPublicRepositoryClient(transport=transport)
        result = client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            result.html_url,
            "https://github.com/openai/openai-python",
        )

    def test_full_name_must_match_requested_subject(self):
        transport = RecordingTransport(
            payload=valid_payload(full_name="someone/other")
        )
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            caught.exception.code,
            GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
        )
        self.assertEqual(transport.calls, 1)

    def test_private_repository_response_fails_closed(self):
        transport = RecordingTransport(payload=valid_payload(private=True))
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            caught.exception.code,
            GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
        )

    def test_redirect_status_is_not_followed(self):
        transport = RecordingTransport(status=301)
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_HTTP)
        self.assertEqual(transport.calls, 1)

    def test_http_error_is_normalized_without_body_leak(self):
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/openai/openai-python",
            404,
            "sensitive",
            hdrs=None,
            fp=None,
        )
        transport = RecordingTransport(error=error)
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_HTTP)
        self.assertNotIn("404", str(caught.exception))
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertEqual(transport.calls, 1)

    def test_timeout_is_normalized_without_retry(self):
        transport = RecordingTransport(error=socket.timeout("sensitive"))
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_TIMEOUT)
        self.assertEqual(transport.calls, 1)

    def test_url_error_is_normalized_without_retry(self):
        transport = RecordingTransport(error=urllib.error.URLError("sensitive"))
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_NETWORK)
        self.assertEqual(transport.calls, 1)

    def test_response_size_is_bounded_before_json_parsing(self):
        transport = RecordingTransport(
            body=b"x" * (GITHUB_PUBLIC_REPOSITORY_MAX_RESPONSE_BYTES + 1)
        )
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            caught.exception.code,
            GITHUB_CONNECTOR_ERROR_RESPONSE_TOO_LARGE,
        )

    def test_invalid_json_fails_closed(self):
        transport = RecordingTransport(body=b"{not-json")
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_INVALID_JSON)

    def test_non_object_json_fails_closed(self):
        transport = RecordingTransport(body=b"[]")
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            caught.exception.code,
            GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
        )

    def test_invalid_field_types_fail_closed(self):
        changes = (
            {"archived": "false"},
            {"fork": 0},
            {"stargazers_count": True},
            {"forks_count": -1},
            {"open_issues_count": "5"},
            {"license": "MIT"},
            {"default_branch": None},
        )
        for change in changes:
            with self.subTest(change=change):
                transport = RecordingTransport(payload=valid_payload(**change))
                client = GitHubPublicRepositoryClient(transport=transport)
                with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
                    client.get_repository_metadata("openai/openai-python")
                self.assertEqual(
                    caught.exception.code,
                    GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
                )

    def test_oversized_description_fails_closed(self):
        transport = RecordingTransport(
            payload=valid_payload(description="x" * 4097)
        )
        client = GitHubPublicRepositoryClient(transport=transport)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            client.get_repository_metadata("openai/openai-python")
        self.assertEqual(
            caught.exception.code,
            GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
        )


if __name__ == "__main__":
    unittest.main()
