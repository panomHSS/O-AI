import json
import unittest
import urllib.error
import urllib.parse
from unittest.mock import Mock, patch

from pydantic import SecretStr

from app.connectors.google_oauth import (
    GOOGLE_OAUTH_AUTHORIZATION_URL,
    GOOGLE_OAUTH_ERROR_INVALID_GRANT,
    GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH,
    GOOGLE_OAUTH_REVOCATION_URL,
    GOOGLE_OAUTH_TOKEN_URL,
    GoogleOAuthClient,
    GoogleOAuthClientError,
    _NoRedirectHandler,
    _open_without_redirects,
)
from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SCOPE
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig


class FakeResponse:
    def __init__(self, payload, *, status=200):
        self.status = status
        if isinstance(payload, bytes):
            self.body = payload
        else:
            self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit):
        return self.body[:limit]


class RecordingTransport:
    def __init__(self, payload=None, *, status=200, error=None):
        self.payload = payload or {
            "access_token": "access-secret-never-log",
            "expires_in": 3600,
            "refresh_token": "refresh-secret-never-log",
            "scope": GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            "token_type": "Bearer",
        }
        self.status = status
        self.error = error
        self.calls = 0
        self.requests = []

    def __call__(self, request, timeout):
        self.calls += 1
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.payload, status=self.status)


class GoogleOAuthClientTests(unittest.TestCase):
    def config(self):
        return GoogleOAuthRuntimeConfig(
            client_id="client-id",
            client_secret=SecretStr("client-secret-never-log"),
            redirect_uri=(
                "http://localhost:8000/api/v1/oauth/"
                "google-calendar/callback"
            ),
            token_encryption_key=SecretStr(
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
            ),
        )

    def test_authorization_url_is_exact_and_not_incremental(self) -> None:
        client = GoogleOAuthClient(transport=RecordingTransport())
        url = client.build_authorization_url(
            self.config(),
            state="state-value",
        )
        parsed = urllib.parse.urlsplit(url)
        self.assertEqual(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            GOOGLE_OAUTH_AUTHORIZATION_URL,
        )
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["scope"], [GOOGLE_CALENDAR_CREDENTIAL_SCOPE])
        self.assertEqual(query["access_type"], ["offline"])
        self.assertEqual(query["prompt"], ["consent"])
        self.assertEqual(query["state"], ["state-value"])
        self.assertNotIn("include_granted_scopes", query)

    def test_code_exchange_uses_fixed_post_and_keeps_secrets_out_of_url(self) -> None:
        transport = RecordingTransport()
        response = GoogleOAuthClient(
            transport=transport
        ).exchange_authorization_code(
            self.config(),
            code="authorization-code-secret",
        )
        self.assertEqual(transport.calls, 1)
        request = transport.requests[0]
        self.assertEqual(request.full_url, GOOGLE_OAUTH_TOKEN_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertNotIn("authorization-code-secret", request.full_url)
        self.assertNotIn("client-secret-never-log", request.full_url)
        body = urllib.parse.parse_qs(request.data.decode("utf-8"))
        self.assertEqual(body["grant_type"], ["authorization_code"])
        self.assertEqual(
            response.refresh_token.get_secret_value(),
            "refresh-secret-never-log",
        )

    def test_refresh_accepts_missing_scope_as_same_grant(self) -> None:
        transport = RecordingTransport(
            payload={
                "access_token": "access-secret-never-log",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        )
        response = GoogleOAuthClient(
            transport=transport
        ).refresh_access_token(
            self.config(),
            refresh_token=SecretStr("refresh-secret-never-log"),
        )
        self.assertEqual(response.scopes, ())
        self.assertEqual(transport.calls, 1)

    def test_scope_mismatch_fails_closed(self) -> None:
        transport = RecordingTransport(
            payload={
                "access_token": "access-secret-never-log",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar",
                "token_type": "Bearer",
            }
        )
        with self.assertRaises(GoogleOAuthClientError) as caught:
            GoogleOAuthClient(
                transport=transport
            ).exchange_authorization_code(
                self.config(),
                code="authorization-code-secret",
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_ERROR_SCOPE_MISMATCH,
        )

    def test_invalid_grant_is_normalized_without_secret_leak(self) -> None:
        body = json.dumps(
            {
                "error": "invalid_grant",
                "error_description": "refresh-secret-never-log",
            }
        ).encode("utf-8")
        error = urllib.error.HTTPError(
            GOOGLE_OAUTH_TOKEN_URL,
            400,
            "bad",
            hdrs=None,
            fp=None,
        )
        error.read = Mock(return_value=body)
        transport = RecordingTransport(error=error)
        with self.assertRaises(GoogleOAuthClientError) as caught:
            GoogleOAuthClient(
                transport=transport
            ).refresh_access_token(
                self.config(),
                refresh_token=SecretStr("refresh-secret-never-log"),
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_OAUTH_ERROR_INVALID_GRANT,
        )
        self.assertNotIn(
            "refresh-secret-never-log",
            str(caught.exception),
        )

    def test_revocation_uses_fixed_post_body(self) -> None:
        transport = RecordingTransport(payload=b"")
        GoogleOAuthClient(transport=transport).revoke_refresh_token(
            refresh_token=SecretStr("refresh-secret-never-log")
        )
        request = transport.requests[0]
        self.assertEqual(request.full_url, GOOGLE_OAUTH_REVOCATION_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertNotIn("refresh-secret-never-log", request.full_url)
        body = urllib.parse.parse_qs(request.data.decode("utf-8"))
        self.assertEqual(
            body["token"],
            ["refresh-secret-never-log"],
        )

    def test_default_transport_disables_proxy_and_redirects(self) -> None:
        request = urllib.request.Request(
            GOOGLE_OAUTH_TOKEN_URL,
            data=b"x=1",
            method="POST",
        )
        opener = Mock()
        sentinel = object()
        opener.open.return_value = sentinel
        with patch(
            "app.connectors.google_oauth.urllib.request.build_opener",
            return_value=opener,
        ) as build:
            result = _open_without_redirects(request, 5.0)
        self.assertIs(result, sentinel)
        handlers = build.call_args.args
        self.assertIsInstance(handlers[0], urllib.request.ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _NoRedirectHandler)


if __name__ == "__main__":
    unittest.main()
