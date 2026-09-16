from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.api import dependencies
from app.contracts.execution_authorization import ExecutionAuthorization
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
    CalendarDeleteExecutionAuthorizationError,
    CalendarUpdateDeleteExecutionService,
    CalendarUpdateExecutionAuthorizationError,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalService,
    CalendarWriteApprovalStore,
)
from app.services.capability_permission_policy import (
    PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS,
)
from app.services.execution_guard import ExecutionGuard
from app.services.module_runtime import ModuleRuntime


class RejectingGuard(ExecutionGuard):
    def __init__(self) -> None:
        pass

    def authorize(self, request, planning, approval=None):
        return ExecutionAuthorization(
            request_id=request.request_id,
            status="rejected",
            target_kind="module",
            source_plan_digest=None,
            execution_plan=None,
            reason_code="test_authorization_rejected",
        )


def approved_update():
    start = datetime(2026, 9, 22, 8, tzinfo=timezone.utc)
    request = GoogleCalendarUpdateEventRequest(
        target=GoogleCalendarEventTarget(event_id="event-auth-update"),
        changes=GoogleCalendarEventPatch(
            summary="Authorized only after guard",
            start=start,
            end=start + timedelta(hours=1),
        ),
    )
    store = CalendarWriteApprovalStore(
        approval_id_factory=lambda: "auth-update"
    )
    service = CalendarWriteApprovalService(store=store)
    proposal = service.propose(request).proposal
    approved = service.approve(
        proposal.approval_id,
        proposal.write_digest,
    ).approved
    return store, proposal, approved


def approved_delete():
    request = GoogleCalendarDeleteEventRequest(
        target=GoogleCalendarEventTarget(event_id="event-auth-delete")
    )
    store = CalendarWriteApprovalStore(
        approval_id_factory=lambda: "auth-delete"
    )
    service = CalendarWriteApprovalService(store=store)
    proposal = service.propose(request).proposal
    approved = service.approve(
        proposal.approval_id,
        proposal.write_digest,
    ).approved
    return store, proposal, approved


class CalendarUpdateDeleteWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        for factory_name in (
            "get_google_calendar_update_module_adapter",
            "get_google_calendar_delete_module_adapter",
            "get_calendar_update_delete_private_registry",
            "get_calendar_update_delete_private_permission_policy",
        ):
            factory = getattr(dependencies, factory_name, None)
            clear = getattr(factory, "cache_clear", None)
            if callable(clear):
                clear()

    def tearDown(self) -> None:
        self.setUp()

    def test_private_registry_and_policy_are_exactly_update_delete(self) -> None:
        registry = dependencies.get_calendar_update_delete_private_registry()
        self.assertEqual(
            registry.module_adapter_ids,
            tuple(
                sorted(
                    (
                        GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
                        GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
                    )
                )
            ),
        )
        policy = dependencies.get_calendar_update_delete_private_permission_policy()
        self.assertEqual(
            policy.capability_ids,
            tuple(
                sorted(
                    (
                        GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID,
                        GOOGLE_CALENDAR_DELETE_CAPABILITY_ID,
                    )
                )
            ),
        )
        for permission in policy.permissions:
            self.assertEqual(permission.target_kind, "module")
            self.assertEqual(permission.effect, "external_side_effect")
            self.assertEqual(permission.data_class, "owner_data")
            self.assertTrue(permission.owner_approval_required)

    def test_private_write_capabilities_are_absent_from_global_static_d44(self) -> None:
        global_adapter_ids = {
            permission.adapter_id
            for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        }
        global_capability_ids = {
            permission.capability_id
            for permission in PRODUCTION_EXECUTABLE_CAPABILITY_PERMISSIONS
        }
        for adapter_id in (
            GOOGLE_CALENDAR_UPDATE_ADAPTER_ID,
            GOOGLE_CALENDAR_DELETE_ADAPTER_ID,
        ):
            self.assertNotIn(adapter_id, global_adapter_ids)
        for capability_id in (
            GOOGLE_CALENDAR_UPDATE_CAPABILITY_ID,
            GOOGLE_CALENDAR_DELETE_CAPABILITY_ID,
        ):
            self.assertNotIn(capability_id, global_capability_ids)

    def test_authorization_failure_leaves_update_approval_unclaimed(self) -> None:
        store, proposal, approved = approved_update()
        service = CalendarUpdateDeleteExecutionService(
            approval_store=store,
            guard=RejectingGuard(),
            runtime=ModuleRuntime(registry=AdapterRegistry()),
        )
        with self.assertRaises(CalendarUpdateExecutionAuthorizationError):
            service.execute_update(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(
            store.get_approved(proposal.approval_id, proposal.write_digest),
            approved,
        )

    def test_authorization_failure_leaves_delete_approval_unclaimed(self) -> None:
        store, proposal, approved = approved_delete()
        service = CalendarUpdateDeleteExecutionService(
            approval_store=store,
            guard=RejectingGuard(),
            runtime=ModuleRuntime(registry=AdapterRegistry()),
        )
        with self.assertRaises(CalendarDeleteExecutionAuthorizationError):
            service.execute_delete(
                proposal.approval_id,
                proposal.write_digest,
            )
        self.assertEqual(
            store.get_approved(proposal.approval_id, proposal.write_digest),
            approved,
        )


if __name__ == "__main__":
    unittest.main()
