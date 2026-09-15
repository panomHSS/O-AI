import json
import socket
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from pydantic import SecretStr

from app.connectors.google_calendar import (
    GOOGLE_CALENDAR_ERROR_AUTHENTICATION,
    GOOGLE_CALENDAR_ERROR_HTTP,
    GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL,
    GOOGLE_CALENDAR_ERROR_INVALID_JSON,
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


class GoogleCalendarConnectorTests(unittest.TestCase):
    TOKEN = "secret-calendar-token-never-log"

    @staticmethod
    def clock():
        return datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    def client(self, transport):
        return GoogleCalendarClient(
            transport=transport,
            clock=self.clock,
        )

    def test_request_is_one_fixed_primary_calendar_get(self) -> None:
        transport = RecordingTransport()
        self.client(transport).list_upcoming_events(
            SecretStr(self.TOKEN)
        )
        self.assertEqual(transport.calls, 1)
        request = transport.requests[0]
        parsed = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            GOOGLE_CALENDAR_EVENTS_URL,
        )
        self.assertEqual(request.get_method(), "GET")
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["timeMin"], ["2026-09-15T12:00:00Z"])
        self.assertEqual(query["timeMax"], ["2026-09-22T12:00:00Z"])
        self.assertEqual(query["maxResults"], ["10"])
        self.assertEqual(query["singleEvents"], ["true"])
        self.assertEqual(query["orderBy"], ["startTime"])
        self.assertEqual(query["showDeleted"], ["false"])
        self.assertEqual(query["fields"], [GOOGLE_CALENDAR_FIELDS])
        self.assertEqual(transport.timeouts, [5.0])

    def test_access_token_is_header_only_and_not_in_url(self) -> None:
        transport = RecordingTransport()
        self.client(transport).list_upcoming_events(
            SecretStr(self.TOKEN)
        )
        request = transport.requests[0]
        self.assertNotIn(self.TOKEN, request.full_url)
        headers = {
            key.casefold(): value
            for key, value in request.header_items()
        }
        self.assertEqual(
            headers["authorization"],
            f"Bearer {self.TOKEN}",
        )
        self.assertNotIn("cookie", headers)
        self.assertNotIn("proxy-authorization", headers)

    def test_default_transport_disables_proxy_and_redirects(self) -> None:
        request = urllib.request.Request(
            GOOGLE_CALENDAR_EVENTS_URL,
            method="GET",
        )
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

    def test_response_is_normalized_to_whitelist_only(self) -> None:
        transport = RecordingTransport()
        events = self.client(transport).list_upcoming_events(
            SecretStr(self.TOKEN)
        )
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].summary, "Planning")
        self.assertEqual(events[0].status, "confirmed")
        self.assertEqual(events[0].start, "2026-09-16T09:00:00+07:00")
        self.assertEqual(events[0].end, "2026-09-16T10:00:00+07:00")
        self.assertFalse(events[0].all_day)
        self.assertEqual(events[1].summary, "Holiday")
        self.assertTrue(events[1].all_day)
        self.assertEqual(
            set(events[0].as_dict()),
            {"summary", "status", "start", "end", "all_day"},
        )

    def test_empty_calendar_is_valid(self) -> None:
        transport = RecordingTransport(payload={"items": []})
        events = self.client(transport).list_upcoming_events(
            SecretStr(self.TOKEN)
        )
        self.assertEqual(events, ())

    def test_missing_items_is_treated_as_empty(self) -> None:
        transport = RecordingTransport(payload={})
        events = self.client(transport).list_upcoming_events(
            SecretStr(self.TOKEN)
        )
        self.assertEqual(events, ())

    def test_invalid_credential_fails_before_network(self) -> None:
        transport = RecordingTransport()
        for credential in ("plain", SecretStr("")):
            with self.subTest(type=type(credential).__name__):
                with self.assertRaises(
                    GoogleCalendarConnectorError
                ) as caught:
                    self.client(transport).list_upcoming_events(
                        credential  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    caught.exception.code,
                    GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL,
                )
        self.assertEqual(transport.calls, 0)

    def test_header_injection_or_excessive_token_fails_before_network(self) -> None:
        transport = RecordingTransport()
        for token in (
            SecretStr("bad\r\nInjected: yes"),
            SecretStr("x" * 8193),
        ):
            with self.subTest(length=len(token.get_secret_value())):
                with self.assertRaises(
                    GoogleCalendarConnectorError
                ) as caught:
                    self.client(transport).list_upcoming_events(token)
                self.assertEqual(
                    caught.exception.code,
                    GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL,
                )
        self.assertEqual(transport.calls, 0)

    def test_authentication_failure_is_safe_and_no_retry(self) -> None:
        transport = RecordingTransport(status=401)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_AUTHENTICATION,
        )
        self.assertEqual(transport.calls, 1)
        self.assertNotIn(self.TOKEN, str(caught.exception))

    def test_http_failure_is_safe_and_no_retry(self) -> None:
        transport = RecordingTransport(status=500)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_HTTP,
        )
        self.assertEqual(transport.calls, 1)

    def test_http_error_401_is_authentication_failure(self) -> None:
        error = urllib.error.HTTPError(
            GOOGLE_CALENDAR_EVENTS_URL,
            401,
            self.TOKEN,
            hdrs=None,
            fp=None,
        )
        transport = RecordingTransport(error=error)
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_AUTHENTICATION,
        )
        self.assertNotIn(self.TOKEN, str(caught.exception))

    def test_timeout_is_normalized_without_retry(self) -> None:
        transport = RecordingTransport(
            error=socket.timeout(self.TOKEN)
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_TIMEOUT,
        )
        self.assertEqual(transport.calls, 1)

    def test_url_error_is_normalized_without_retry(self) -> None:
        transport = RecordingTransport(
            error=urllib.error.URLError(self.TOKEN)
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_NETWORK,
        )
        self.assertEqual(transport.calls, 1)

    def test_response_size_is_bounded(self) -> None:
        transport = RecordingTransport(
            body=b"x" * (GOOGLE_CALENDAR_MAX_RESPONSE_BYTES + 1)
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE,
        )

    def test_invalid_json_fails_closed(self) -> None:
        transport = RecordingTransport(body=b"{not-json")
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_INVALID_JSON,
        )

    def test_invalid_event_shapes_fail_closed(self) -> None:
        bad_events = (
            {"summary": "", "status": "confirmed",
             "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
             "end": {"dateTime": "2026-09-16T10:00:00+07:00"}},
            {"summary": "x", "status": "unknown",
             "start": {"dateTime": "2026-09-16T09:00:00+07:00"},
             "end": {"dateTime": "2026-09-16T10:00:00+07:00"}},
            {"summary": "x", "status": "confirmed",
             "start": {"dateTime": "2026-09-16T10:00:00+07:00"},
             "end": {"dateTime": "2026-09-16T09:00:00+07:00"}},
            {"summary": "x", "status": "confirmed",
             "start": {"date": "2026-09-16"},
             "end": {"dateTime": "2026-09-17T00:00:00+07:00"}},
        )
        for event in bad_events:
            with self.subTest(event=event):
                transport = RecordingTransport(
                    payload={"items": [event]}
                )
                with self.assertRaises(
                    GoogleCalendarConnectorError
                ) as caught:
                    self.client(transport).list_upcoming_events(
                        SecretStr(self.TOKEN)
                    )
                self.assertEqual(
                    caught.exception.code,
                    GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
                )

    def test_more_than_ten_events_fails_closed(self) -> None:
        event = valid_payload()["items"][0]
        transport = RecordingTransport(
            payload={"items": [event] * 11}
        )
        with self.assertRaises(GoogleCalendarConnectorError) as caught:
            self.client(transport).list_upcoming_events(
                SecretStr(self.TOKEN)
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
        )


if __name__ == "__main__":
    unittest.main()
