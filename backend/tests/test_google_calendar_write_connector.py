from __future__ import annotations

import inspect
import json
import socket
import unittest
from datetime import datetime, timezone

from pydantic import SecretStr

from app.connectors import google_calendar_write as write_module
from app.connectors.google_calendar_write import (
    GOOGLE_CALENDAR_CREATE_EVENT_URL,
    GoogleCalendarWriteClient,
    GoogleCalendarWriteError,
)
from app.contracts.google_calendar_write import GoogleCalendarEventDraft


class FakeResponse:
    status = 200

    def __init__(self, body: bytes = b'{"id":"event-1"}') -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit: int) -> bytes:
        return self.body


class GoogleCalendarWriteConnectorTests(unittest.TestCase):
    def event(self) -> GoogleCalendarEventDraft:
        return GoogleCalendarEventDraft(
            summary="Review",
            start=datetime(2026, 9, 18, 9, tzinfo=timezone.utc),
            end=datetime(2026, 9, 18, 10, tzinfo=timezone.utc),
            description="",
            location="Room A",
        )

    def test_fixed_single_post_and_allowlisted_body(self) -> None:
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            return FakeResponse()

        result = GoogleCalendarWriteClient(
            transport=transport
        ).create_event(
            SecretStr("token"),
            event=self.event(),
        )
        self.assertEqual(result.event_id, "event-1")
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(request.full_url, GOOGLE_CALENDAR_CREATE_EVENT_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 5.0)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            set(payload),
            {"summary", "start", "end", "description", "location"},
        )
        self.assertEqual(payload["description"], "")
        self.assertNotIn("attendees", payload)
        self.assertNotIn("recurrence", payload)
        self.assertNotIn("conferenceData", payload)

    def test_definite_4xx_is_failed_not_indeterminate(self) -> None:
        class RejectedResponse(FakeResponse):
            status = 400

        client = GoogleCalendarWriteClient(
            transport=lambda request, timeout: RejectedResponse(b"ignored")
        )
        with self.assertRaises(GoogleCalendarWriteError) as caught:
            client.create_event(
                SecretStr("token"),
                event=self.event(),
            )
        self.assertEqual(
            caught.exception.code,
            "calendar_create_provider_rejected",
        )
        self.assertFalse(caught.exception.indeterminate)

    def test_malformed_success_is_indeterminate(self) -> None:
        client = GoogleCalendarWriteClient(
            transport=lambda request, timeout: FakeResponse(b"not-json")
        )
        with self.assertRaises(GoogleCalendarWriteError) as caught:
            client.create_event(
                SecretStr("token"),
                event=self.event(),
            )
        self.assertTrue(caught.exception.indeterminate)

    def test_transport_disables_proxy_redirect_and_retry(self) -> None:
        source = inspect.getsource(write_module)
        self.assertIn("urllib.request.ProxyHandler({})", source)
        self.assertIn("_NoRedirectHandler()", source)
        self.assertNotIn("retry", source.lower())

    def test_timeout_is_indeterminate_and_not_retried(self) -> None:
        calls = 0

        def transport(request, timeout):
            nonlocal calls
            calls += 1
            raise socket.timeout()

        with self.assertRaises(GoogleCalendarWriteError) as caught:
            GoogleCalendarWriteClient(
                transport=transport
            ).create_event(
                SecretStr("token"),
                event=self.event(),
            )
        self.assertEqual(calls, 1)
        self.assertTrue(caught.exception.indeterminate)


if __name__ == "__main__":
    unittest.main()
