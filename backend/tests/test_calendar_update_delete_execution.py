from __future__ import annotations

import threading
import time
import unittest
from datetime import datetime, timedelta, timezone

from pydantic import SecretStr

from app.adapters.google_calendar_delete_module import GoogleCalendarDeleteModuleAdapter
from app.adapters.google_calendar_update_module import GoogleCalendarUpdateModuleAdapter
from app.connectors.google_calendar_write import (
    GoogleCalendarDeleteResult,
    GoogleCalendarUpdateResult,
    GoogleCalendarWriteError,
)
from app.contracts.capability_permission import ExecutableCapabilityPermission
from app.contracts.google_calendar import GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF
from app.contracts.google_calendar_update_delete_execution import (
    GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
    GOOGLE_CALENDAR_DELETE_CAPABILITY_ID,
    GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
    GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID,
)
from app.contracts.google_calendar_write import (
    GoogleCalendarDeleteEventRequest,
    GoogleCalendarEventPatch,
    GoogleCalendarEventTarget,
    GoogleCalendarUpdateEventRequest,
)
from app.services.adapter_registry import AdapterRegistry
from app.services.calendar_update_delete_execution import (
    CalendarDeleteExecutionOperationError,
    CalendarUpdateDeleteExecutionService,
    CalendarUpdateExecutionOperationError,
    build_calendar_delete_execution_plan,
    build_calendar_update_execution_plan,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalNotApprovedError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.capability_permission_policy import CapabilityPermissionPolicy
from app.services.credential_access_broker import (
    CredentialAccessBroker,
    StaticCredentialSecretSource,
)
from app.services.credential_profile_catalog import (
    PRODUCTION_CREDENTIAL_PROFILES,
    CredentialProfileCatalog,
)
from app.services.execution_guard import ExecutionGuard
from app.services.module_runtime import ModuleRuntime


def update_request() -> GoogleCalendarUpdateEventRequest:
    start = datetime(2026, 9, 21, 9, tzinfo=timezone.utc)
    return GoogleCalendarUpdateEventRequest(
        target=GoogleCalendarEventTarget(event_id="event/update-1"),
        changes=GoogleCalendarEventPatch(
            summary="Updated review",
            start=start,
            end=start + timedelta(hours=1),
            description="",
            location="Room B",
        ),
    )


def delete_request() -> GoogleCalendarDeleteEventRequest:
    return GoogleCalendarDeleteEventRequest(
        target=GoogleCalendarEventTarget(event_id="event/delete-1")
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


class RecordingMutationClient:
    def __init__(
        self,
        store,
        approval_id,
        digest,
        events,
        *,
        delay=0.0,
        indeterminate_operation=None,
    ):
        self.store = store
        self.approval_id = approval_id
        self.digest = digest
        self.events = events
        self.delay = delay
        self.indeterminate_operation = indeterminate_operation
        self.update_calls = 0
        self.delete_calls = 0
        self.lock = threading.Lock()

    def _claimed(self):
        try:
            self.store.get_approved(self.approval_id, self.digest)
        except CalendarWriteApprovalNotApprovedError:
            return
        raise AssertionError("provider attempted before claim")

    def update_event(self, credential, *, target, changes):
        self._claimed()
        with self.lock:
            self.update_calls += 1
        self.events.append("update")
        if self.delay:
            time.sleep(self.delay)
        if self.indeterminate_operation == "update":
            raise GoogleCalendarWriteError(
                "calendar_update_indeterminate",
                indeterminate=True,
            )
        return GoogleCalendarUpdateResult(event_id=target.event_id)

    def delete_event(self, credential, *, target):
        self._claimed()
        with self.lock:
            self.delete_calls += 1
        self.events.append("delete")
        if self.delay:
            time.sleep(self.delay)
        if self.indeterminate_operation == "delete":
            raise GoogleCalendarWriteError(
                "calendar_delete_indeterminate",
                indeterminate=True,
            )
        return GoogleCalendarDeleteResult(event_id=target.event_id)


def approve(request, approval_id):
    store = CalendarWriteApprovalStore(
        approval_id_factory=lambda: approval_id
    )
    approvals = CalendarWriteApprovalService(store=store)
    proposal = approvals.propose(request).proposal
    approved = approvals.approve(
        proposal.approval_id,
        proposal.write_digest,
    ).approved
    return store, proposal, approved


def make_service(store, proposal, client):
    broker = CredentialAccessBroker(
        profile_catalog=CredentialProfileCatalog(PRODUCTION_CREDENTIAL_PROFILES),
        secret_source=RecordingSource(
            store,
            proposal.approval_id,
            proposal.write_digest,
            client.events,
        ),
    )
    update_adapter = GoogleCalendarUpdateModuleAdapter(
        credential_broker=broker,
        client=client,
    )
    delete_adapter = GoogleCalendarDeleteModuleAdapter(
        credential_broker=broker,
        client=client,
    )
    registry = AdapterRegistry((update_adapter, delete_adapter))
    policy = CapabilityPermissionPolicy(
        registry=registry,
        permissions=(
            ExecutableCapabilityPermission(
                capability_id=GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID,
                target_kind="module",
                adapter_id=GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
                operation="update_event",
                effect="external_side_effect",
                data_class="owner_data",
                owner_approval_required=True,
            ),
            ExecutableCapabilityPermission(
                capability_id=GOOGLE_CALENDAR_DELETE_CAPABILITY_ID,
                target_kind="module",
                adapter_id=GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
                operation="delete_event",
                effect="external_side_effect",
                data_class="owner_data",
                owner_approval_required=True,
            ),
        ),
    )
    return CalendarUpdateDeleteExecutionService(
        approval_store=store,
        guard=ExecutionGuard(registry=registry, permission_policy=policy),
        runtime=ModuleRuntime(registry=registry),
    )


class CalendarUpdateDeleteExecutionTests(unittest.TestCase):
    def test_update_plan_is_deterministic_exact_and_domain_separated(self) -> None:
        _, proposal, approved = approve(update_request(), "update-plan")
        one = build_calendar_update_execution_plan(approved)
        two = build_calendar_update_execution_plan(approved)
        self.assertEqual(one, two)
        self.assertNotEqual(one[2], proposal.write_digest)
        parameters = one[1].plan.steps[0].parameters
        self.assertEqual(parameters["event_id"], "event/update-1")
        self.assertEqual(parameters["description"], "")

    def test_delete_plan_is_deterministic_exact_and_domain_separated(self) -> None:
        _, proposal, approved = approve(delete_request(), "delete-plan")
        one = build_calendar_delete_execution_plan(approved)
        two = build_calendar_delete_execution_plan(approved)
        self.assertEqual(one, two)
        self.assertNotEqual(one[2], proposal.write_digest)
        self.assertEqual(
            one[1].plan.steps[0].parameters["event_id"],
            "event/delete-1",
        )

    def test_wrong_operation_is_rejected_before_claim(self) -> None:
        store, proposal, approved = approve(delete_request(), "delete-wrong")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
        )
        service = make_service(store, proposal, client)
        with self.assertRaises(CalendarUpdateExecutionOperationError):
            service.execute_update(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(
            store.get_approved(proposal.approval_id, proposal.write_digest),
            approved,
        )
        self.assertEqual(events, [])

        store2, proposal2, approved2 = approve(update_request(), "update-wrong")
        events2 = []
        client2 = RecordingMutationClient(
            store2,
            proposal2.approval_id,
            proposal2.write_digest,
            events2,
        )
        service2 = make_service(store2, proposal2, client2)
        with self.assertRaises(CalendarDeleteExecutionOperationError):
            service2.execute_delete(
                proposal2.approval_id,
                proposal2.write_digest,
            )
        self.assertEqual(
            store2.get_approved(proposal2.approval_id, proposal2.write_digest),
            approved2,
        )
        self.assertEqual(events2, [])

    def test_update_claim_precedes_credential_and_provider_and_blocks_replay(self) -> None:
        store, proposal, _ = approve(update_request(), "update-claim")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
        )
        service = make_service(store, proposal, client)
        outcome = service.execute_update(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.event_id, "event/update-1")
        self.assertEqual(events, ["credential", "update"])
        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_update(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.update_calls, 1)

    def test_delete_claim_precedes_credential_and_provider_and_blocks_replay(self) -> None:
        store, proposal, _ = approve(delete_request(), "delete-claim")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
        )
        service = make_service(store, proposal, client)
        outcome = service.execute_delete(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(events, ["credential", "delete"])
        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_delete(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.delete_calls, 1)

    def test_update_indeterminate_consumes_claim(self) -> None:
        store, proposal, _ = approve(update_request(), "update-indeterminate")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
            indeterminate_operation="update",
        )
        service = make_service(store, proposal, client)
        outcome = service.execute_update(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.status, "indeterminate")
        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_update(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.update_calls, 1)

    def test_delete_indeterminate_consumes_claim(self) -> None:
        store, proposal, _ = approve(delete_request(), "delete-indeterminate")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
            indeterminate_operation="delete",
        )
        service = make_service(store, proposal, client)
        outcome = service.execute_delete(
            proposal.approval_id,
            proposal.write_digest,
        )
        self.assertEqual(outcome.status, "indeterminate")
        with self.assertRaises(CalendarWriteApprovalNotApprovedError):
            service.execute_delete(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(client.delete_calls, 1)

    def _concurrent_attempt(self, *, operation: str) -> None:
        request = update_request() if operation == "update" else delete_request()
        store, proposal, _ = approve(request, f"{operation}-concurrent")
        events = []
        client = RecordingMutationClient(
            store,
            proposal.approval_id,
            proposal.write_digest,
            events,
            delay=0.05,
        )
        service = make_service(store, proposal, client)
        finished = []

        def run():
            try:
                method = (
                    service.execute_update
                    if operation == "update"
                    else service.execute_delete
                )
                finished.append(
                    method(proposal.approval_id, proposal.write_digest)
                )
            except Exception as error:
                finished.append(error)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(finished), 2)
        if operation == "update":
            self.assertEqual(client.update_calls, 1)
        else:
            self.assertEqual(client.delete_calls, 1)

    def test_update_concurrency_provider_at_most_once(self) -> None:
        self._concurrent_attempt(operation="update")

    def test_delete_concurrency_provider_at_most_once(self) -> None:
        self._concurrent_attempt(operation="delete")


if __name__ == "__main__":
    unittest.main()
