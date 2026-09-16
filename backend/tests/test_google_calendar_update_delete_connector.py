from __future__ import annotations

import inspect
import json
import socket
import unittest
from datetime import datetime, timedelta, timezone

from pydantic import SecretStr

from app.connectors import google_calendar_write as write_module
from app.connectors.google_calendar_write import (
    GOOGLE_CALENDAR_DELETE_ERROR_PROVIDER_REJECTED,
    GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
    GOOGLE_CALENDAR_UPDATE_ERROR_PROVIDER_REJECTED,
    GoogleCalendarWriteClient,
    GoogleCalendarWriteError,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
)


class FakeResponse:
    def __init__(self, *, status: int, body: bytes) -> None:
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit: int) -> bytes:
        return self.body


class GoogleCalendarUpdateDeleteConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 9, 19, 9, 30, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=1)
        self.target = GoogleCalendarEventTarget(event_id="opaque/id %")

    def test_update_uses_exact_encoded_target_and_allowlisted_patch(self) -> None:
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(
                status=200,
                body=json.dumps({"id": self.target.event_id}).encode("utf-8"),
            )

        changes = GoogleCalendarEventPatch(
            summary="Updated review",
            start=self.start,
            end=self.end,
            description="",
            location="",
        )
        result = GoogleCalendarWriteClient(
            transport=transport
        ).update_event(
            SecretStr("token"),
            target=self.target,
            changes=changes,
        )

        self.assertEqual(result.event_id, self.target.event_id)
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(request.get_method(), "PATCH")
        self.assertTrue(request.full_url.endswith("/events/opaque%2Fid%20%25"))
        self.assertNotIn("?", request.full_url)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            set(payload),
            {"summary", "start", "end", "description", "location"},
        )
        self.assertEqual(payload["description"], "")
        self.assertEqual(payload["location"], "")
        self.assertEqual(
            payload["start"],
            {"dateTime": self.start.isoformat(timespec="microseconds")},
        )
        self.assertEqual(
            payload["end"],
            {"dateTime": self.end.isoformat(timespec="microseconds")},
        )
        self.assertNotIn("attendees", payload)
        self.assertNotIn("recurrence", payload)
        self.assertNotIn("conferenceData", payload)

    def test_update_mismatched_success_event_id_is_indeterminate(self) -> None:
        client = GoogleCalendarWriteClient(
            transport=lambda request, timeout: FakeResponse(
                status=200,
                body=b'{"id":"other-event"}',
            )
        )
        with self.assertRaises(GoogleCalendarWriteError) as caught:
            client.update_event(
                SecretStr("token"),
                target=self.target,
                changes=GoogleCalendarEventPatch(summary="Updated"),
            )
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE,
        )
        self.assertTrue(caught.exception.indeterminate)

    def test_update_400_is_definite_and_408_is_indeterminate(self) -> None:
        for status, expected_code, indeterminate in (
            (400, GOOGLE_CALENDAR_UPDATE_ERROR_PROVIDER_REJECTED, False),
            (408, GOOGLE_CALENDAR_UPDATE_ERROR_INDETERMINATE, True),
        ):
            with self.subTest(status=status):
                client = GoogleCalendarWriteClient(
                    transport=lambda request, timeout, status=status: FakeResponse(
                        status=status,
                        body=b"ignored",
                    )
                )
                with self.assertRaises(GoogleCalendarWriteError) as caught:
                    client.update_event(
                        SecretStr("token"),
                        target=self.target,
                        changes=GoogleCalendarEventPatch(summary="Updated"),
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(caught.exception.indeterminate, indeterminate)

    def test_delete_has_no_body_query_or_unencoded_path_segments(self) -> None:
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(status=204, body=b"")

        result = GoogleCalendarWriteClient(
            transport=transport
        ).delete_event(
            SecretStr("token"),
            target=self.target,
        )

        self.assertEqual(result.event_id, self.target.event_id)
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(request.get_method(), "DELETE")
        self.assertTrue(request.full_url.endswith("/events/opaque%2Fid%20%25"))
        self.assertNotIn("?", request.full_url)
        self.assertIsNone(request.data)

    def test_delete_400_is_definite_failure(self) -> None:
        client = GoogleCalendarWriteClient(
            transport=lambda request, timeout: FakeResponse(
                status=400,
                body=b"ignored",
            )
        )
        with self.assertRaises(GoogleCalendarWriteError) as caught:
            client.delete_event(SecretStr("token"), target=self.target)
        self.assertEqual(
            caught.exception.code,
            GOOGLE_CALENDAR_DELETE_ERROR_PROVIDER_REJECTED,
        )
        self.assertFalse(caught.exception.indeterminate)

    def test_delete_timeout_is_indeterminate_and_single_attempt(self) -> None:
        calls = 0

        def transport(request, timeout):
            nonlocal calls
            calls += 1
            raise socket.timeout()

        client = GoogleCalendarWriteClient(transport=transport)
        with self.assertRaises(GoogleCalendarWriteError) as caught:
            client.delete_event(SecretStr("token"), target=self.target)
        self.assertEqual(calls, 1)
        self.assertTrue(caught.exception.indeterminate)

    def test_transport_hardening_remains_fixed(self) -> None:
        source = inspect.getsource(write_module)
        self.assertIn("urllib.request.ProxyHandler({})", source)
        self.assertIn("_NoRedirectHandler()", source)
        self.assertNotIn("retry", source.lower())
        self.assertNotIn("sendUpdates", source)
        self.assertNotIn("sendNotifications", source)


if __name__ == "__main__":
    unittest.main()
