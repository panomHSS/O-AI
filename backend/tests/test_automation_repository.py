import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository


class AutomationRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        AutomationDefinitionRecord.__table__.create(self.engine)
        AutomationRunRecord.__table__.create(self.engine)
        self.session = Session(self.engine)
        self.repository = AutomationRepository(self.session)
        self.now = datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def definition(self, *, automation_id=None, status="pending"):
        return AutomationDefinitionRecord(
            id=automation_id or str(uuid4()),
            contract_version="1",
            kind="local_reminder",
            message="Check daily report",
            schedule_kind="daily",
            run_at_iso=None,
            daily_local_time="09:00",
            timezone="Asia/Bangkok",
            max_runs=7,
            definition_digest="a" * 64,
            status=status,
            approval_expires_at=self.now + timedelta(minutes=10),
            approved_at=None,
            terminal_at=None,
            next_due_at_utc=None,
            created_at=self.now,
            updated_at=self.now,
        )

    def run_record(self, automation_id, *, run_id=None, due=None):
        return AutomationRunRecord(
            id=run_id or str(uuid4()),
            automation_id=automation_id,
            definition_digest="a" * 64,
            due_at_utc=due or self.now + timedelta(hours=1),
            status="claimed",
            claimed_at=self.now,
            delivered_at=None,
            created_at=self.now,
            updated_at=self.now,
        )

    def test_definition_round_trip_and_status_count(self):
        definition = self.definition()
        self.repository.add_definition(definition)
        self.session.commit()

        loaded = self.repository.get_definition(definition.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.message, "Check daily report")
        self.assertEqual(
            self.repository.count_definitions_with_status("pending"),
            1,
        )
        self.assertEqual(
            [item.id for item in self.repository.list_definitions()],
            [definition.id],
        )

    def test_run_row_does_not_duplicate_reminder_message(self):
        definition = self.definition()
        self.repository.add_definition(definition)
        run = self.run_record(definition.id)
        self.repository.add_run(run)
        self.session.commit()

        loaded = self.repository.get_run(run.id)
        self.assertIsNotNone(loaded)
        self.assertFalse(hasattr(loaded, "message"))
        self.assertEqual(
            self.repository.count_runs_for_automation(definition.id),
            1,
        )

    def test_unique_automation_due_slot_fails_closed(self):
        definition = self.definition()
        self.repository.add_definition(definition)
        due = self.now + timedelta(hours=1)
        self.repository.add_run(
            self.run_record(definition.id, due=due)
        )
        self.session.commit()

        with self.assertRaises(IntegrityError):
            self.repository.add_run(
                self.run_record(definition.id, due=due)
            )
        self.session.rollback()
        self.assertEqual(
            self.repository.count_runs_for_automation(definition.id),
            1,
        )

    def test_repository_list_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            self.repository.list_definitions(limit=101)
        with self.assertRaises(ValueError):
            self.repository.list_runs(limit=0)


if __name__ == "__main__":
    unittest.main()
