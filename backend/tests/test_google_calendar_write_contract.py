"""D72 Calendar Write Contract v1 regression tests."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import inspect
import unittest

import app.contracts.google_calendar_write as write_contract
from app.adapters.google_calendar_module import GoogleCalendarModuleAdapter
from app.contracts.google_calendar import (
    GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
    GOOGLE_CALENDAR_OPERATION,
)
from app.contracts.google_calendar_write import (
    GOOGLE_CALENDAR_CREATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_DELETE_EVENT_OPERATION,
    GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION,
    GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION,
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.plugins.google_calendar import GoogleCalendarPlugin


class GoogleCalendarWriteContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=1)

    def test_operation_identity_is_exact_and_stable(self) -> None:
        self.assertEqual(GOOGLE_CALENDAR_WRITE_CONTRACT_VERSION, "1")
        self.assertEqual(GOOGLE_CALENDAR_CREATE_EVENT_OPERATION, "create_event")
        self.assertEqual(GOOGLE_CALENDAR_UPDATE_EVENT_OPERATION, "update_event")
        self.assertEqual(GOOGLE_CALENDAR_DELETE_EVENT_OPERATION, "delete_event")

    def test_create_contract_is_valid_and_immutable(self) -> None:
        draft = GoogleCalendarEventDraft(
            summary="Factory review",
            start=self.start,
            end=self.end,
            description="Review operating plan",
            location="Meeting room",
        )
        request = GoogleCalendarCreateEventRequest(event=draft)

        self.assertEqual(request.contract_version, "1")
        self.assertEqual(request.operation, "create_event")
        self.assertEqual(request.event.calendar_id, "primary")
        with self.assertRaises(FrozenInstanceError):
            draft.summary = "changed"  # type: ignore[misc]

    def test_create_rejects_invalid_summary_or_time(self) -> None:
        cases = (
            {"summary": "", "start": self.start, "end": self.end},
            {"summary": " padded ", "start": self.start, "end": self.end},
            {"summary": "x" * 1025, "start": self.start, "end": self.end},
            {
                "summary": "naive",
                "start": self.start.replace(tzinfo=None),
                "end": self.end,
            },
            {"summary": "reverse", "start": self.end, "end": self.start},
            {
                "summary": "too long",
                "start": self.start,
                "end": self.start + timedelta(days=32, seconds=1),
            },
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    GoogleCalendarEventDraft(**kwargs)

    def test_create_rejects_non_primary_calendar_and_oversized_optional_text(self) -> None:
        with self.assertRaises(ValueError):
            GoogleCalendarEventDraft(
                summary="Other calendar",
                start=self.start,
                end=self.end,
                calendar_id="secondary",  # type: ignore[arg-type]
            )
        with self.assertRaises(ValueError):
            GoogleCalendarEventDraft(
                summary="Description",
                start=self.start,
                end=self.end,
                description="x" * 8193,
            )
        with self.assertRaises(ValueError):
            GoogleCalendarEventDraft(
                summary="Location",
                start=self.start,
                end=self.end,
                location="x" * 1025,
            )

    def test_exact_event_target_is_required_and_bounded(self) -> None:
        target = GoogleCalendarEventTarget(event_id="opaque-event-id")
        self.assertEqual(target.event_id, "opaque-event-id")
        self.assertEqual(target.calendar_id, "primary")

        for event_id in ("", " ", " padded", "event\nid", "event\rid", "event\x00id"):
            with self.subTest(event_id=repr(event_id)):
                with self.assertRaises(ValueError):
                    GoogleCalendarEventTarget(event_id=event_id)

        with self.assertRaises(ValueError):
            GoogleCalendarEventTarget(event_id="x" * 1025)

    def test_update_contract_allows_only_bounded_nonempty_patch(self) -> None:
        target = GoogleCalendarEventTarget(event_id="event-123")
        changes = GoogleCalendarEventPatch(
            summary="Updated review",
            start=self.start + timedelta(hours=1),
            end=self.end + timedelta(hours=1),
            description="",
        )
        request = GoogleCalendarUpdateEventRequest(
            target=target,
            changes=changes,
        )
        self.assertEqual(request.contract_version, "1")
        self.assertEqual(request.operation, "update_event")

        with self.assertRaises(ValueError):
            GoogleCalendarEventPatch()
        with self.assertRaises(ValueError):
            GoogleCalendarEventPatch(start=self.start)
        with self.assertRaises(ValueError):
            GoogleCalendarEventPatch(end=self.end)
        with self.assertRaises(ValueError):
            GoogleCalendarEventPatch(summary="")
        with self.assertRaises(ValueError):
            GoogleCalendarEventPatch(
                start=self.start,
                end=self.start + timedelta(days=32, seconds=1),
            )

    def test_delete_contract_requires_exact_target(self) -> None:
        request = GoogleCalendarDeleteEventRequest(
            target=GoogleCalendarEventTarget(event_id="event-456")
        )
        self.assertEqual(request.contract_version, "1")
        self.assertEqual(request.operation, "delete_event")
        self.assertEqual(request.target.event_id, "event-456")

    def test_unknown_provider_specific_fields_are_not_contract_fields(self) -> None:
        with self.assertRaises(TypeError):
            GoogleCalendarEventDraft(
                summary="No provider payload",
                start=self.start,
                end=self.end,
                attendees=("x@example.com",),  # type: ignore[call-arg]
            )
        with self.assertRaises(TypeError):
            GoogleCalendarEventPatch(
                conference_data={"createRequest": {}},  # type: ignore[call-arg]
            )

    def test_contract_module_has_no_execution_or_connector_dependencies(self) -> None:
        tree = ast.parse(inspect.getsource(write_contract))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        allowed = {"__future__", "dataclasses", "datetime", "typing", "unicodedata"}
        self.assertTrue(imported_modules <= allowed, imported_modules)

    def test_existing_calendar_runtime_remains_read_only(self) -> None:
        self.assertEqual(GOOGLE_CALENDAR_OPERATION, "list_upcoming_events")
        self.assertEqual(
            GOOGLE_CALENDAR_CREDENTIAL_SCOPE,
            "https://www.googleapis.com/auth/calendar.events.readonly",
        )

        plugin_source = inspect.getsource(GoogleCalendarPlugin)
        adapter_source = inspect.getsource(GoogleCalendarModuleAdapter)
        for write_operation in ("create_event", "update_event", "delete_event"):
            self.assertNotIn(write_operation, plugin_source)
            self.assertNotIn(write_operation, adapter_source)
        self.assertIn("list_upcoming_events", plugin_source)


if __name__ == "__main__":
    unittest.main()
