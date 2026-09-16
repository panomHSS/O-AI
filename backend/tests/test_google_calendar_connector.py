import json
import socket
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from pydantic import SecretStr

from app.connectors.google_calendar import (
    GOOGLE_CALENDAR_ERROR_AUTHENTICATION,
    GOOGLE_CALENDAR_ERROR_HTTP,
    GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL,
    GOOGLE_CALENDAR_ERROR_INVALID_JSON,
    GOOGLE_CALENDAR_ERROR_INVALID_REQUEST,
    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
    GOOGLE_CALENDAR_ERROR_NETWORK,
    GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE,
    GOOGLE_CALENDAR_ERROR_TIMEOUT,
    GOOGLE_CALENDAR_EVENTS_URL,
    GOOGLE_CALENDAR_FIELDS,
    GOOGLE_CALENDAR_MAX_RESPONSE_BYTES,
    GoogleCalendarClient,
    GoogleCalendarConnectorError,
    _NoRedirectHandler,
    _open_without_redirects,
)


def valid_payload():
    return {
        "items": [
            {
                "summary": "Planning",
                "status": "confirmed",
                "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
                "end": {"dateTime": "2026-09-16T10:00:00+07:00"},
            },
            {
                "summary": "Holiday",
                "status": "confirmed",
                "start": {"date": "2026-09-17"},
                "end": {"date": "2026-09-18"},
            },
        ]
    }


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
    def __init__(self, *, payload=None, body=None, status=200, error=None) -> None:
        self.calls = 0
        self.requests = []
        self.timeouts = []
        self.error = error
        source = valid_payload() if payload is None else payload
        self.body = body if body is not None else json.dumps(source).encode("utf-8")
        self.status = status

    def __call__(self, request, timeout):
        self.calls += 1
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.body, status=self.status)


class GoogleCalendarConnectorTests(unittest.TestCase):
    TOKEN = "secret-calendar-token-never-log"
    TIME_MIN = datetime.fromisoformat("2026-09-16T00:00:00+07:00")
    TIME_MAX = datetime.fromisoformat("2026-09-17T00:00:00+07:00")

    def client(self, transport):
        return GoogleCalendarClient(transport=transport)

    def read(self, client, credential=None, *, time_min=None, time_max=None):
        return client.list_upcoming_events(
            SecretStr(self.TOKEN) if credential is None else credential,
            time_min=self.TIME_MIN if time_min is None else time_min,
            time_max=self.TIME_MAX if time_max is None else time_max,
        )

    def test_request_is_one_fixed_primary_calendar_get_for_exact_window(self):
        transport = RecordingTransport()
        self.read(self.client(transport))
        self.assertEqual(transport.calls, 1)
        request = transport.requests[0]
        parsed = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            GOOGLE_CALENDAR_EVENTS_URL,
        )
        self.assertEqual(request.get_method(), "GET")
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["timeMin"], ["2026-09-15T17:00:00Z"])
        self.assertEqual(query["timeMax"], ["2026-09-16T17:00:00Z"])
        self.assertEqual(query["maxResults"], ["10"])
        self.assertEqual(query["singleEvents"], ["true"])
        self.assertEqual(query["orderBy"], ["startTime"])
        self.assertEqual(query["showDeleted"], ["false"])
        self.assertEqual(query["fields"], [GOOGLE_CALENDAR_FIELDS])
        self.assertEqual(transport.timeouts, [5.0])

    def test_access_token_is_header_only_and_not_in_url(self):
        transport = RecordingTransport()
        self.read(self.client(transport))
        request = transport.requests[0]
        self.assertNotIn(self.TOKEN, request.full_url)
        headers = {key.casefold(): value for key, value in request.header_items()}
        self.assertEqual(headers["authorization"], f"Bearer {self.TOKEN}")
        self.assertNotIn("cookie", headers)
        self.assertNotIn("proxy-authorization", headers)

    def test_default_transport_disables_proxy_and_redirects(self):
        request = urllib.request.Request(GOOGLE_CALENDAR_EVENTS_URL, method="GET")
        opener = Mock()
        sentinel = object()
        opener.open.return_value = sentinel
        with patch(
            "app.connectors.google_calendar.urllib.request.build_opener",
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

    def test_response_is_normalized_and_truncation_is_boolean_only(self):
        payload = valid_payload()
        payload["nextPageToken"] = "opaque-token-never-expose"
        result = self.read(self.client(RecordingTransport(payload=payload)))
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].summary, "Planning")
        self.assertEqual(result.events[1].summary, "Holiday")
        self.assertFalse(hasattr(result, "next_page_token"))

    def test_empty_or_missing_items_is_valid(self):
        for payload in ({"items": []}, {}):
            with self.subTest(payload=payload):
                result = self.read(self.client(RecordingTransport(payload=payload)))
                self.assertEqual(result.events, ())
                self.assertFalse(result.truncated)

    def test_invalid_window_fails_before_network(self):
        transport = RecordingTransport()
        cases = (
            (datetime(2026, 9, 16), self.TIME_MAX),
            (self.TIME_MAX, self.TIME_MIN),
            (self.TIME_MIN, self.TIME_MIN + timedelta(days=33)),
        )
        for time_min, time_max in cases:
            with self.subTest(time_min=time_min, time_max=time_max):
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(
                        self.client(transport),
                        time_min=time_min,
                        time_max=time_max,
                    )
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_REQUEST)
        self.assertEqual(transport.calls, 0)

    def test_invalid_credential_fails_before_network(self):
        transport = RecordingTransport()
        for credential in ("plain", SecretStr("")):
            with self.subTest(type=type(credential).__name__):
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(self.client(transport), credential=credential)
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL)
        self.assertEqual(transport.calls, 0)

    def test_header_injection_or_excessive_token_fails_before_network(self):
        transport = RecordingTransport()
        for token in (SecretStr("bad\r\nInjected: yes"), SecretStr("x" * 8193)):
            with self.subTest(length=len(token.get_secret_value())):
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(self.client(transport), credential=token)
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL)
        self.assertEqual(transport.calls, 0)

    def test_transport_failures_are_safe_and_never_retry(self):
        cases = (
            (RecordingTransport(status=401), GOOGLE_CALENDAR_ERROR_AUTHENTICATION),
            (RecordingTransport(status=500), GOOGLE_CALENDAR_ERROR_HTTP),
            (RecordingTransport(error=socket.timeout(self.TOKEN)), GOOGLE_CALENDAR_ERROR_TIMEOUT),
            (RecordingTransport(error=urllib.error.URLError(self.TOKEN)), GOOGLE_CALENDAR_ERROR_NETWORK),
        )
        for transport, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(self.client(transport))
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(transport.calls, 1)
                self.assertNotIn(self.TOKEN, str(caught.exception))

    def test_http_error_401_is_authentication_failure(self):
        error = urllib.error.HTTPError(
            GOOGLE_CALENDAR_EVENTS_URL, 401, self.TOKEN, hdrs=None, fp=None
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.read(self.client(RecordingTransport(error=error)))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_AUTHENTICATION)
        self.assertNotIn(self.TOKEN, str(caught.exception))

    def test_response_size_and_json_are_bounded(self):
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.read(
                self.client(
                    RecordingTransport(
                        body=b"x" * (GOOGLE_CALENDAR_MAX_RESPONSE_BYTES + 1)
                    )
                )
            )
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.read(self.client(RecordingTransport(body=b"{not-json")))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_JSON)

    def test_invalid_event_shapes_and_excessive_results_fail_closed(self):
        bad_events = (
            {
                "summary": "",
                "status": "confirmed",
                "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
                "end": {"dateTime": "2026-09-16T10:00:00+07:00"},
            },
            {
                "summary": "x",
                "status": "unknown",
                "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
                "end": {"dateTime": "2026-09-16T10:00:00+07:00"},
            },
        )
        for event in bad_events:
            with self.subTest(event=event):
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(self.client(RecordingTransport(payload={"items": [event]})))
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)
        event = valid_payload()["items"][0]
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.read(self.client(RecordingTransport(payload={"items": [event] * 11})))
        self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)

    def test_invalid_next_page_token_fails_closed(self):
        for token in ("", 123, "x" * 4097):
            with self.subTest(token=type(token).__name__):
                payload = valid_payload()
                payload["nextPageToken"] = token
                with self.assertRaises(GoogleCalendarConnectorError) as caught:
                    self.read(self.client(RecordingTransport(payload=payload)))
                self.assertEqual(caught.exception.code, GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE)


if __name__ == "__main__":
    unittest.main()
