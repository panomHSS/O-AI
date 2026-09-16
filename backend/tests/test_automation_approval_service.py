import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.contracts.automation import (
    DailyAutomationSchedule,
    OnceAutomationSchedule,
)
from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository
from app.services.automation_approval import (
    AutomationActiveCapacityError,
    AutomationApprovalService,
    AutomationDigestMismatchError,
    AutomationDisabledError,
    AutomationExpiredError,
    AutomationNotActiveError,
    AutomationNotPendingError,
    AutomationPendingCapacityError,
    AutomationProposalInvalidError,
)


class MutableClock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class AutomationApprovalServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        AutomationDefinitionRecord.__table__.create(self.engine)
        AutomationRunRecord.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.repository = AutomationRepository(self.session)
        self.clock = MutableClock(
            datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)
        )
        self.service = AutomationApprovalService(
            self.repository,
            enabled=True,
            owner_timezone="Asia/Bangkok",
            clock=self.clock,
        )

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def propose_daily(self, *, index=0):
        return self.service.propose(
            message=f"Reminder {index}",
            schedule=DailyAutomationSchedule(local_time="09:00"),
            max_runs=7,
        )

    def test_proposal_uses_deployment_timezone_and_deterministic_digest(self):
        first = self.propose_daily()
        self.assertEqual(first.status, "pending")
        self.assertEqual(first.preview.timezone, "Asia/Bangkok")
        self.assertEqual(first.preview.schedule_kind, "daily")
        self.assertEqual(first.preview.daily_local_time, "09:00")
        self.assertEqual(
            first.expires_at,
            self.clock.value + timedelta(minutes=10),
        )
        record = self.repository.get_definition(first.automation_id)
        self.assertEqual(record.definition_digest, first.definition_digest)
        self.assertEqual(record.timezone, "Asia/Bangkok")
        self.assertIsNone(record.next_due_at_utc)

    def test_once_window_is_one_minute_through_365_days(self):
        with self.assertRaises(AutomationProposalInvalidError):
            self.service.propose(
                message="Too soon",
                schedule=OnceAutomationSchedule(
                    run_at=self.clock.value + timedelta(seconds=59)
                ),
                max_runs=1,
            )
        with self.assertRaises(AutomationProposalInvalidError):
            self.service.propose(
                message="Too far",
                schedule=OnceAutomationSchedule(
                    run_at=self.clock.value + timedelta(days=365, seconds=1)
                ),
                max_runs=1,
            )

        for delta in (
            timedelta(minutes=1),
            timedelta(days=365),
        ):
            outcome = self.service.propose(
                message=f"Boundary {delta}",
                schedule=OnceAutomationSchedule(
                    run_at=self.clock.value + delta
                ),
                max_runs=1,
            )
            self.assertEqual(outcome.status, "pending")

    def test_approve_requires_exact_digest_and_does_not_mutate_definition(self):
        proposal = self.propose_daily()
        record = self.repository.get_definition(proposal.automation_id)
        snapshot = (
            record.message,
            record.schedule_kind,
            record.daily_local_time,
            record.timezone,
            record.max_runs,
            record.definition_digest,
        )

        with self.assertRaises(AutomationDigestMismatchError):
            self.service.approve(
                proposal.automation_id,
                "0" * 64,
            )

        outcome = self.service.approve(
            proposal.automation_id,
            proposal.definition_digest,
        )
        self.assertEqual(outcome.status, "approved")

        record = self.repository.get_definition(proposal.automation_id)
        self.assertEqual(
            (
                record.message,
                record.schedule_kind,
                record.daily_local_time,
                record.timezone,
                record.max_runs,
                record.definition_digest,
            ),
            snapshot,
        )
        self.assertEqual(record.status, "approved")
        self.assertIsNotNone(record.approved_at)

        with self.assertRaises(AutomationNotPendingError):
            self.service.approve(
                proposal.automation_id,
                proposal.definition_digest,
            )

    def test_expired_proposal_cannot_be_approved_or_denied(self):
        proposal = self.propose_daily()
        self.clock.value += timedelta(minutes=10)

        with self.assertRaises(AutomationExpiredError):
            self.service.approve(
                proposal.automation_id,
                proposal.definition_digest,
            )
        with self.assertRaises(AutomationExpiredError):
            self.service.deny(
                proposal.automation_id,
                proposal.definition_digest,
            )
        record = self.repository.get_definition(proposal.automation_id)
        self.assertEqual(record.status, "pending")

    def test_denial_is_terminal(self):
        proposal = self.propose_daily()
        outcome = self.service.deny(
            proposal.automation_id,
            proposal.definition_digest,
        )
        self.assertEqual(outcome.status, "denied")
        with self.assertRaises(AutomationNotPendingError):
            self.service.approve(
                proposal.automation_id,
                proposal.definition_digest,
            )
        with self.assertRaises(AutomationNotActiveError):
            self.service.cancel(proposal.automation_id)

    def test_pending_capacity_counts_only_unexpired_pending(self):
        for index in range(64):
            self.propose_daily(index=index)
        with self.assertRaises(AutomationPendingCapacityError):
            self.propose_daily(index=65)

        self.clock.value += timedelta(minutes=10)
        fresh = self.propose_daily(index=66)
        self.assertEqual(fresh.status, "pending")

    def test_active_capacity_is_exactly_32(self):
        for index in range(32):
            proposal = self.propose_daily(index=index)
            self.service.approve(
                proposal.automation_id,
                proposal.definition_digest,
            )
        extra = self.propose_daily(index=100)
        with self.assertRaises(AutomationActiveCapacityError):
            self.service.approve(
                extra.automation_id,
                extra.definition_digest,
            )

    def test_disabled_blocks_create_and_approve_but_allows_list_and_cancel(self):
        proposal = self.propose_daily()
        self.service.approve(
            proposal.automation_id,
            proposal.definition_digest,
        )

        disabled = AutomationApprovalService(
            self.repository,
            enabled=False,
            owner_timezone="Asia/Bangkok",
            clock=self.clock,
        )
        with self.assertRaises(AutomationDisabledError):
            disabled.propose(
                message="blocked",
                schedule=DailyAutomationSchedule(local_time="09:00"),
                max_runs=1,
            )

        pending_service_proposal = self.service.propose(
            message="Pending",
            schedule=DailyAutomationSchedule(local_time="10:00"),
            max_runs=1,
        )
        with self.assertRaises(AutomationDisabledError):
            disabled.approve(
                pending_service_proposal.automation_id,
                pending_service_proposal.definition_digest,
            )

        self.assertGreaterEqual(len(disabled.list_automations()), 2)
        cancelled = disabled.cancel(proposal.automation_id)
        self.assertEqual(cancelled.status, "cancelled")
        with self.assertRaises(AutomationNotActiveError):
            disabled.cancel(proposal.automation_id)

    def test_run_list_reads_message_from_definition_not_run_row(self):
        proposal = self.propose_daily()
        self.service.approve(
            proposal.automation_id,
            proposal.definition_digest,
        )
        due = self.clock.value + timedelta(hours=1)
        run = AutomationRunRecord(
            id="run-1",
            automation_id=proposal.automation_id,
            definition_digest=proposal.definition_digest,
            due_at_utc=due,
            status="claimed",
            claimed_at=self.clock.value,
            delivered_at=None,
            created_at=self.clock.value,
            updated_at=self.clock.value,
        )
        self.repository.add_run(run)
        self.repository.commit()

        items = self.service.list_runs()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].message, "Reminder 0")
        self.assertEqual(items[0].scheduled_for, due)


if __name__ == "__main__":
    unittest.main()
