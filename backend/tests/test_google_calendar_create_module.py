from __future__ import annotations

import unittest
from datetime import datetime, timezone

from pydantic import SecretStr

from app.adapters.google_calendar_create_module import GoogleCalendarCreateModuleAdapter
from app.connectors.google_calendar_write import GoogleCalendarCreateResult
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF
from app.contracts.google_calendar_create_execution import (
    GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
    calendar_create_execution_parameters,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarEventDraft,
)
from app.services.calendar_write_approval import calendar_write_digest
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    CredentialProfileCatalog,
    PRODUCTION_CREDENTIAL_PROFILES,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def create_event(self, credential, *, event):
        self.calls += 1
        return GoogleCalendarCreateResult(event_id="event-1")


def create_request() -> GoogleCalendarCreateEventRequest:
    return GoogleCalendarCreateEventRequest(
        event=GoogleCalendarEventDraft(
            summary="Review",
            start=datetime(2026, 9, 18, 9, tzinfo=timezone.utc),
            end=datetime(2026, 9, 18, 10, tzinfo=timezone.utc),
        )
    )


def make_broker() -> CredentialAccessBroker:
    return CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog(
            PRODUCTION_CREDENTIAL_PROFILES
        ),
        secret_source=StaticCredentialSecretSource(
            {GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF: SecretStr("token")}
        ),
    )


class GoogleCalendarCreateModuleTests(unittest.TestCase):
    def test_executes_exact_authorized_plan(self) -> None:
        request = create_request()
        parameters = calendar_create_execution_parameters(
            request,
            calendar_write_digest(request),
        )
        client = FakeClient()
        adapter = GoogleCalendarCreateModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-1", command="module.execute"),
            ExecutionPlan(
                request_id="approval-1",
                adapter_id=GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="create_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output, {"event_id": "event-1"})
        self.assertEqual(client.calls, 1)

    def test_tampered_write_digest_fails_before_provider(self) -> None:
        request = create_request()
        parameters = calendar_create_execution_parameters(
            request,
            calendar_write_digest(request),
        )
        parameters["write_digest"] = "0" * 64
        client = FakeClient()
        adapter = GoogleCalendarCreateModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-1", command="module.execute"),
            ExecutionPlan(
                request_id="approval-1",
                adapter_id=GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="create_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
