import inspect
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.contracts.automation_delivery import (
    AUTOMATION_DELIVERY_LIST_DEFAULT,
    AUTOMATION_DELIVERY_LIST_MAX,
)
from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository
from app.services.automation_delivery import (
    AutomationDeliveryService,
    AutomationDeliveryStorageInvariantError,
)


class AutomationDeliveryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        db_path = Path(self.temp.name) / "automation-delivery.db"
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
        self.open_sessions = []
        self.now = datetime(
            2026, 9, 18, 13, 0, tzinfo=timezone.utc
        )

    def tearDown(self):
        for session in reversed(self.open_sessions):
            session.close()
        self.open_sessions.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def add_definition(
        self,
        automation_id: str,
        *,
        message: str,
        digest: str,
    ) -> None:
        record = AutomationDefinitionRecord(
            id=automation_id,
            contract_version="1",
            kind="local_reminder",
            message=message,
            schedule_kind="daily",
            run_at_iso=None,
            daily_local_time="20:00",
            timezone="Asia/Bangkok",
            max_runs=7,
            definition_digest=digest,
            status="approved",
            approval_expires_at=self.now,
            approved_at=self.now - timedelta(minutes=1),
            terminal_at=None,
            next_due_at_utc=self.now + timedelta(days=1),
            created_at=self.now - timedelta(minutes=2),
            updated_at=self.now - timedelta(minutes=1),
        )
        with self.Session() as session:
            repository = AutomationRepository(session)
            repository.add_definition(record)
            repository.commit()

    def add_run(
        self,
        run_id: str,
        automation_id: str,
        *,
        digest: str,
        status: str,
        due_offset_minutes: int,
    ) -> None:
        due = self.now + timedelta(minutes=due_offset_minutes)
        record = AutomationRunRecord(
            id=run_id,
            automation_id=automation_id,
            definition_digest=digest,
            due_at_utc=due,
            status=status,
            claimed_at=(
                due if status in {"claimed", "delivered", "indeterminate"}
                else None
            ),
            delivered_at=(due if status == "delivered" else None),
            created_at=due,
            updated_at=due,
        )
        with self.Session() as session:
            repository = AutomationRepository(session)
            repository.add_run(record)
            repository.commit()

    def service(self, *, enabled: bool = True):
        session = self.Session()
        self.open_sessions.append(session)
        return AutomationDeliveryService(
            AutomationRepository(session),
            enabled=enabled,
            owner_timezone="Asia/Bangkok",
        )

    def test_settings_are_safe_deployment_projection(self):
        view = self.service(enabled=False).settings()
        self.assertFalse(view.enabled)
        self.assertEqual(view.owner_timezone, "Asia/Bangkok")
        self.assertEqual(
            set(view.__dataclass_fields__),
            {"enabled", "owner_timezone"},
        )

    def test_terminal_deliveries_are_newest_first_and_claimed_is_hidden(self):
        self.add_definition(
            "automation-1",
            message="Exact approved reminder",
            digest="a" * 64,
        )
        self.add_run(
            "run-delivered",
            "automation-1",
            digest="a" * 64,
            status="delivered",
            due_offset_minutes=-3,
        )
        self.add_run(
            "run-claimed",
            "automation-1",
            digest="a" * 64,
            status="claimed",
            due_offset_minutes=-2,
        )
        self.add_run(
            "run-missed",
            "automation-1",
            digest="a" * 64,
            status="missed",
            due_offset_minutes=-1,
        )
        self.add_run(
            "run-indeterminate",
            "automation-1",
            digest="a" * 64,
            status="indeterminate",
            due_offset_minutes=0,
        )

        items = self.service().list_deliveries()
        self.assertEqual(
            [item.run_id for item in items],
            [
                "run-indeterminate",
                "run-missed",
                "run-delivered",
            ],
        )
        self.assertEqual(
            {item.status for item in items},
            {"delivered", "missed", "indeterminate"},
        )
        self.assertTrue(
            all(
                item.message == "Exact approved reminder"
                for item in items
            )
        )

    def test_delivery_limit_is_bounded_and_applied(self):
        self.assertEqual(AUTOMATION_DELIVERY_LIST_DEFAULT, 20)
        self.assertEqual(AUTOMATION_DELIVERY_LIST_MAX, 50)
        self.add_definition(
            "automation-1",
            message="Reminder",
            digest="a" * 64,
        )
        for index in range(3):
            self.add_run(
                f"run-{index}",
                "automation-1",
                digest="a" * 64,
                status="delivered",
                due_offset_minutes=index,
            )

        items = self.service().list_deliveries(limit=2)
        self.assertEqual(
            [item.run_id for item in items],
            ["run-2", "run-1"],
        )
        for invalid in (0, 51, True, 1.5, "2"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.service().list_deliveries(limit=invalid)

    def test_digest_mismatch_fails_closed(self):
        self.add_definition(
            "automation-1",
            message="Reminder",
            digest="a" * 64,
        )
        self.add_run(
            "run-1",
            "automation-1",
            digest="b" * 64,
            status="delivered",
            due_offset_minutes=0,
        )

        with self.assertRaises(AutomationDeliveryStorageInvariantError):
            self.service().list_deliveries()

    def test_delivery_service_has_no_mutation_or_execution_dependency(self):
        source = inspect.getsource(AutomationDeliveryService)
        for forbidden in (
            ".commit(",
            ".rollback(",
            "add_run(",
            "transition_claimed_run(",
            "advance_if_due(",
            "AutomationRunService",
            "AIRuntime",
            "ToolRuntime",
            "ModuleRuntime",
            "CredentialAccessBroker",
            "GmailPlugin",
            "GoogleCalendarPlugin",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
