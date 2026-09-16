import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository
from app.services.automation_run_service import AutomationRunService


class MutableClock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class AutomationRunServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        db_path = Path(self.temp.name) / "automation.db"
        self.engine = create_engine(
            f"sqlite+pysqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        AutomationDefinitionRecord.__table__.create(self.engine)
        AutomationRunRecord.__table__.create(self.engine)
        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        self.now = datetime(
            2026, 9, 17, 2, 0, tzinfo=timezone.utc
        )
        self.clock = MutableClock(self.now)
        self.service = AutomationRunService(
            self.Session,
            clock=self.clock,
        )

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def add_definition(
        self,
        *,
        automation_id="automation-1",
        schedule_kind="daily",
        due=None,
        max_runs=3,
        daily_local_time="09:00",
        run_at_iso=None,
    ):
        due = due or self.now
        record = AutomationDefinitionRecord(
            id=automation_id,
            contract_version="1",
            kind="local_reminder",
            message="private reminder text",
            schedule_kind=schedule_kind,
            run_at_iso=run_at_iso,
            daily_local_time=(
                daily_local_time
                if schedule_kind == "daily"
                else None
            ),
            timezone="Asia/Bangkok",
            max_runs=max_runs,
            definition_digest="a" * 64,
            status="approved",
            approval_expires_at=self.now,
            approved_at=self.now - timedelta(minutes=1),
            terminal_at=None,
            next_due_at_utc=due,
            created_at=self.now - timedelta(minutes=1),
            updated_at=self.now - timedelta(minutes=1),
        )
        with self.Session() as session:
            repo = AutomationRepository(session)
            repo.add_definition(record)
            repo.commit()
        return record

    def runs(self):
        with self.Session() as session:
            return [
                (run.status, run.id, run.due_at_utc)
                for run in AutomationRepository(session).list_runs()
            ]

    def definition(self, automation_id="automation-1"):
        with self.Session() as session:
            record = AutomationRepository(session).get_definition(
                automation_id
            )
            return (
                record.status,
                record.next_due_at_utc,
                record.terminal_at,
            )

    def test_due_slot_claims_then_delivers_and_advances_daily(self):
        self.add_definition()
        self.service.tick()

        runs = self.runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0][0], "delivered")
        status, next_due, _ = self.definition()
        self.assertEqual(status, "approved")
        self.assertEqual(
            next_due.replace(tzinfo=timezone.utc),
            self.now + timedelta(days=1),
        )

        self.service.tick()
        self.assertEqual(len(self.runs()), 1)

    def test_once_completes_after_delivery(self):
        due = self.now
        self.add_definition(
            schedule_kind="once",
            due=due,
            max_runs=1,
            run_at_iso=due.isoformat(),
        )
        self.service.tick()

        self.assertEqual(self.runs()[0][0], "delivered")
        status, next_due, terminal_at = self.definition()
        self.assertEqual(status, "completed")
        self.assertIsNone(next_due)
        self.assertIsNotNone(terminal_at)

    def test_old_due_is_missed_and_skips_backlog(self):
        old_due = self.now - timedelta(days=3)
        self.add_definition(due=old_due)
        self.service.tick()

        self.assertEqual(self.runs()[0][0], "missed")
        status, next_due, _ = self.definition()
        self.assertEqual(status, "approved")
        normalized = next_due.replace(tzinfo=timezone.utc)
        self.assertGreater(normalized, self.now)
        self.assertEqual(
            normalized,
            self.now + timedelta(days=1),
        )

    def test_claimed_crash_becomes_indeterminate_and_never_retries(self):
        due = self.now - timedelta(minutes=6)
        definition = self.add_definition(due=due)
        with self.Session() as session:
            repo = AutomationRepository(session)
            repo.add_run(
                AutomationRunRecord(
                    id="claimed-run",
                    automation_id=definition.id,
                    definition_digest=definition.definition_digest,
                    due_at_utc=due,
                    status="claimed",
                    claimed_at=self.now - timedelta(minutes=6),
                    delivered_at=None,
                    created_at=self.now - timedelta(minutes=6),
                    updated_at=self.now - timedelta(minutes=6),
                )
            )
            repo.commit()

        self.service.tick()
        runs = self.runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0][0], "indeterminate")

        _, next_due, _ = self.definition()
        self.assertGreater(
            next_due.replace(tzinfo=timezone.utc),
            self.now,
        )

        self.service.tick()
        self.assertEqual(len(self.runs()), 1)

    def test_due_batch_is_bounded_to_32(self):
        for index in range(40):
            self.add_definition(
                automation_id=f"automation-{index:02d}",
                due=self.now,
                max_runs=1,
            )
        self.service.tick()

        with self.Session() as session:
            repo = AutomationRepository(session)
            self.assertEqual(len(repo.list_runs(limit=100)), 32)

    def test_max_runs_completes_daily_definition(self):
        self.add_definition(max_runs=1)
        self.service.tick()
        status, next_due, _ = self.definition()
        self.assertEqual(status, "completed")
        self.assertIsNone(next_due)


if __name__ == "__main__":
    unittest.main()
