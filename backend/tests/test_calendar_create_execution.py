from __future__ import annotations

import inspect
import threading
import time
import unittest
from datetime import datetime, timezone

from pydantic import SecretStr

from app.adapters.google_calendar_create_module import GoogleCalendarCreateModuleAdapter
from app.connectors.google_calendar_write import (
    GoogleCalendarCreateResult,
    GoogleCalendarWriteError,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF
from app.contracts.google_calendar_create_execution import (
    GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
    GOOGLE_CALENDAR_CREATE_CAPABILITY_ID,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarCreateEventRequest,
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventDraft,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.calendar_create_execution import (
    CalendarCreateExecutionOperationError,
    CalendarCreateExecutionService,
    build_calendar_create_execution_plan,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalNotApprovedError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.capability_permission_policy import (
    CapabilityPermissionPolicy,
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    CredentialProfileCatalog,
    PRODUCTION_CREDENTIAL_PROFILES,
)
from app.services.execution_guard import ExecutionGuard
from app.services.module_runtime import ModuleRuntime


def create_request() -> GoogleCalendarCreateEventRequest:
    return GoogleCalendarCreateEventRequest(
        event=GoogleCalendarEventDraft(
            summary="Review",
            start=datetime(2026, 9, 18, 9, tzinfo=timezone.utc),
            end=datetime(2026, 9, 18, 10, tzinfo=timezone.utc),
        )
    )


class RecordingSource(StaticCredentialSecretSource):
    def __init__(self, store, approval_id, digest, events):
        super().__init__(
            {GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF: SecretStr("token")}
        )
        self.store = store
        self.approval_id = approval_id
        self.digest = digest
        self.events = events

    def resolve(self, secret_ref):
        try:
            self.store.get_approved(self.approval_id, self.digest)
        except CalendarWriteApprovalNotApprovedError:
            pass
        else:
            raise AssertionError("credential resolved before claim")
        self.events.append("credential")
        return super().resolve(secret_ref)


class RecordingClient:
    def __init__(self, store, approval_id, digest, events, delay=0.0):
        self.store = store
        self.approval_id = approval_id
        self.digest = digest
        self.events = events
        self.delay = delay
        self.calls = 0
        self.lock = threading.Lock()

    def create_event(self, credential, *, event):
        try:
            self.store.get_approved(self.approval_id, self.digest)
        except CalendarWriteApprovalNotApprovedError:
            pass
        else:
            raise AssertionError("network attempted before claim")
        with self.lock:
            self.calls += 1
        self.events.append("network")
        if self.delay:
            time.sleep(self.delay)
        return GoogleCalendarCreateResult(event_id="event-1")


class IndeterminateClient(RecordingClient):
    def create_event(self, credential, *, event):
        try:
            self.store.get_approved(
                self.approval_id,
                self.digest,
            )
        except CalendarWriteApprovalNotApprovedError:
            pass
        else:
            raise AssertionError("network attempted before claim")

        with self.lock:
            self.calls += 1
        self.events.append("network")
        raise GoogleCalendarWriteError(
            "calendar_create_indeterminate",
            indeterminate=True,
        )


def make_runtime(store, proposal, client):
    broker = CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog(
            PRODUCTION_CREDENTIAL_PROFILES
        ),
        secret_source=RecordingSource(
            store,
            proposal.approval_id,
            proposal.write_digest,
            client.events,
        ),
    )
    adapter = GoogleCalendarCreateModuleAdapter(
        credential_broker=broker,
        client=client,
    )
    registry = AdapterRegistry((adapter,))
    permission = ExecutableCapabilityPermission(
        capability_id=GOOGLE_CALENDAR_CREATE_CAPABILITY_ID,
        target_kind="module",
        adapter_id=GOOGLE_CALENDAR_CREATE_ADAPTER_ID,
        operation="create_event",
        effect="external_side_effect",
        data_class="owner_data",
        owner_approval_required=True,
    )
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=(permission,),
    )
    return (
        ExecutionGuard(registry=registry, permission_policy=policy),
        ModuleRuntime(registry=registry),
    )


class CalendarCreateExecutionTests(unittest.TestCase):
    def approve(self):
        store = CalendarWriteApprovalStore(
            approval_id_factory=lambda: "approval-1"
        )
        approvals = CalendarWriteApprovalService(store=store)
        proposal = approvals.propose(create_request()).proposal
        approved = approvals.approve(
            proposal.approval_id,
            proposal.write_digest,
        ).approved
        return store, proposal, approved

    def test_plan_is_deterministic_and_domain_separated(self) -> None:
        _, proposal, approved = self.approve()
        one = build_calendar_create_execution_plan(approved)
        two = build_calendar_create_execution_plan(approved)
        self.assertEqual(one, two)
        self.assertNotEqual(one[2], proposal.write_digest)

    def test_claim_precedes_credential_and_network_and_replay(self) -> None:
        store, proposal, _ = self.approve()
        events = []
        client = RecordingClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
        )
        guard, runtime = make_runtime(store, proposal, client)
        service = CalendarCreateExecutionService(
            approval_store=store,
            guard=guard,
            runtime=runtime,
        )
        result = service.execute_create(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(events, ["credential", "network"])
        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_create(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.calls, 1)

    def test_concurrent_execution_attempts_provider_at_most_once(self) -> None:
        store, proposal, _ = self.approve()
        events = []
        client = RecordingClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
            delay=0.05,
        )
        guard, runtime = make_runtime(store, proposal, client)
        service = CalendarCreateExecutionService(
            approval_store=store,
            guard=guard,
            runtime=runtime,
        )
        finished = []

        def run():
            try:
                finished.append(
                    service.execute_create(
                        proposal.approval_id,
                        proposal.write_digest,
                    )
                )
            except Exception as error:
                finished.append(error)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(client.calls, 1)
        self.assertEqual(len(finished), 2)

    def test_indeterminate_consumes_claim_and_replay_does_not_retry(self) -> None:
        store, proposal, _ = self.approve()
        events = []
        client = IndeterminateClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
        )
        guard, runtime = make_runtime(store, proposal, client)
        service = CalendarCreateExecutionService(
            approval_store=store,
            guard=guard,
            runtime=runtime,
        )

        outcome = service.execute_create(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.status, "indeterminate")
        self.assertEqual(client.calls, 1)
        self.assertEqual(events, ["credential", "network"])

        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_create(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.calls, 1)

    def test_update_rejected_before_claim(self) -> None:
        store = CalendarWriteApprovalStore(
            approval_id_factory=lambda: "update-1"
        )
        approvals = CalendarWriteApprovalService(store=store)
        proposal = approvals.propose(
            GoogleCalendarUpdateEventRequest(
                target=GoogleCalendarEventTarget(event_id="event-1"),
                changes=GoogleCalendarEventPatch(summary="Updated"),
            )
        ).proposal
        approved = approvals.approve(
            proposal.approval_id,
            proposal.write_digest,
        ).approved

        with self.assertRaises(CalendarCreateExecutionOperationError):
            build_calendar_create_execution_plan(approved)

        self.assertEqual(
            store.get_approved(
                proposal.approval_id,
                proposal.write_digest,
            ),
            approved,
        )

    def test_delete_rejected_before_claim(self) -> None:
        store = CalendarWriteApprovalStore(
            approval_id_factory=lambda: "delete-1"
        )
        approvals = CalendarWriteApprovalService(store=store)
        proposal = approvals.propose(
            GoogleCalendarDeleteEventRequest(
                target=GoogleCalendarEventTarget(event_id="event-1")
            )
        ).proposal
        approved = approvals.approve(
            proposal.approval_id,
            proposal.write_digest,
        ).approved
        with self.assertRaises(CalendarCreateExecutionOperationError):
            build_calendar_create_execution_plan(approved)
        self.assertEqual(
            store.get_approved(
                proposal.approval_id,
                proposal.write_digest,
            ),
            approved,
        )

    def test_private_adapter_not_in_global_registry_or_policy(self) -> None:
        self.assertTrue(
            all(
                item.adapter_id != GOOGLE_CALENDAR_CREATE_ADAPTER_ID
                for item in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
            )
        )
        from app.api import dependencies
        self.assertNotIn(
            "GoogleCalendarCreateModuleAdapter",
            inspect.getsource(dependencies.get_adapter_registry),
        )


if __name__ == "__main__":
    unittest.main()
