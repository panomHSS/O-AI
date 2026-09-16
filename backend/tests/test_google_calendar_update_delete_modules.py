from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from pydantic import SecretStr

from app.adapters.google_calendar_delete_module import GoogleCalendarDeleteModuleAdapter
from app.adapters.google_calendar_update_module import GoogleCalendarUpdateModuleAdapter
from app.connectors.google_calendar_write import (
    GoogleCalendarDeleteResult,
    GoogleCalendarUpdateResult,
)
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF
from app.contracts.google_calendar_update_delete_execution import (
    GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
    GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
    calendar_delete_execution_parameters,
    calendar_update_execution_parameters,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.services.calendar_write_approval import calendar_write_digest
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
    CredentialProfileCatalog,
)


class FakeClient:
    def __init__(self) -> None:
        self.update_calls = 0
        self.delete_calls = 0

    def update_event(self, credential, *, target, changes):
        self.update_calls += 1
        return GoogleCalendarUpdateResult(event_id=target.event_id)

    def delete_event(self, credential, *, target):
        self.delete_calls += 1
        return GoogleCalendarDeleteResult(event_id=target.event_id)


def make_broker() -> CredentialAccessBroker:
    return CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog(PRODUCTION_CREDENTIAL_PROFILES),
        secret_source=StaticCredentialSecretSource(
            {GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF: SecretStr("token")}
        ),
    )


class GoogleCalendarUpdateDeleteModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        start = datetime(2026, 9, 20, 9, tzinfo=timezone.utc)
        target = GoogleCalendarEventTarget(event_id="event-1")
        self.update_request = GoogleCalendarUpdateEventRequest(
            target=target,
            changes=GoogleCalendarEventPatch(
                summary="Updated",
                start=start,
                end=start + timedelta(hours=1),
                description="",
            ),
        )
        self.delete_request = GoogleCalendarDeleteEventRequest(target=target)

    def test_update_executes_exact_authorized_plan(self) -> None:
        parameters = calendar_update_execution_parameters(
            self.update_request,
            calendar_write_digest(self.update_request),
        )
        client = FakeClient()
        adapter = GoogleCalendarUpdateModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-1", command="module.execute"),
            ExecutionPlan(
                request_id="approval-1",
                adapter_id=GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="update_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output, {"event_id": "event-1"})
        self.assertEqual(client.update_calls, 1)
        self.assertEqual(client.delete_calls, 0)

    def test_update_tampered_write_digest_fails_before_provider(self) -> None:
        parameters = calendar_update_execution_parameters(
            self.update_request,
            calendar_write_digest(self.update_request),
        )
        parameters["write_digest"] = "0" * 64
        client = FakeClient()
        adapter = GoogleCalendarUpdateModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-1", command="module.execute"),
            ExecutionPlan(
                request_id="approval-1",
                adapter_id=GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="update_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(client.update_calls, 0)

    def test_delete_executes_exact_authorized_plan(self) -> None:
        parameters = calendar_delete_execution_parameters(
            self.delete_request,
            calendar_write_digest(self.delete_request),
        )
        client = FakeClient()
        adapter = GoogleCalendarDeleteModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-2", command="module.execute"),
            ExecutionPlan(
                request_id="approval-2",
                adapter_id=GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="delete_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.output, {"event_id": "event-1"})
        self.assertEqual(client.delete_calls, 1)
        self.assertEqual(client.update_calls, 0)

    def test_delete_tampered_event_id_fails_before_provider(self) -> None:
        parameters = calendar_delete_execution_parameters(
            self.delete_request,
            calendar_write_digest(self.delete_request),
        )
        parameters["event_id"] = "event-2"
        client = FakeClient()
        adapter = GoogleCalendarDeleteModuleAdapter(
            credential_broker=make_broker(),
            client=client,
        )
        result = adapter.execute(
            CommandRequest(request_id="approval-2", command="module.execute"),
            ExecutionPlan(
                request_id="approval-2",
                adapter_id=GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
                steps=(
                    ExecutionStep(
                        sequence=1,
                        operation="delete_event",
                        parameters=parameters,
                    ),
                ),
                owner_approval_required=False,
            ),
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(client.delete_calls, 0)


if __name__ == "__main__":
    unittest.main()
