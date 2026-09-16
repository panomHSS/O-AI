"""D79 durable due-slot claim, delivery, and misfire boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository
from app.services.automation_schedule import next_due_after


AUTOMATION_DUE_BATCH_MAX = 32
AUTOMATION_MISFIRE_GRACE = timedelta(minutes=5)
AUTOMATION_STALE_CLAIM_AGE = timedelta(minutes=5)


class AutomationRunService:
    """Process local reminder slots without external side effects."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable.")
        self._session_factory = session_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def tick(self) -> None:
        now = self._now()
        self._recover_stale_claims(now)
        due_slots = self._due_slots(now)
        for automation_id, due_at_utc in due_slots:
            self._process_due_slot(
                automation_id=automation_id,
                due_at_utc=due_at_utc,
                now=now,
            )

    def _due_slots(
        self,
        now: datetime,
    ) -> tuple[tuple[str, datetime], ...]:
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            records = repository.list_due_approved(
                now,
                limit=AUTOMATION_DUE_BATCH_MAX,
            )
            return tuple(
                (
                    record.id,
                    self._db_datetime(record.next_due_at_utc),
                )
                for record in records
                if record.next_due_at_utc is not None
            )

    def _recover_stale_claims(self, now: datetime) -> None:
        cutoff = now - AUTOMATION_STALE_CLAIM_AGE
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            stale = repository.list_stale_claims(
                cutoff,
                limit=AUTOMATION_DUE_BATCH_MAX,
            )
            identities = tuple(
                (
                    run.id,
                    run.automation_id,
                    self._db_datetime(run.due_at_utc),
                )
                for run in stale
            )

        for run_id, automation_id, due_at_utc in identities:
            self._mark_indeterminate(
                run_id=run_id,
                automation_id=automation_id,
                due_at_utc=due_at_utc,
                now=now,
            )

    def _process_due_slot(
        self,
        *,
        automation_id: str,
        due_at_utc: datetime,
        now: datetime,
    ) -> None:
        if due_at_utc < now - AUTOMATION_MISFIRE_GRACE:
            self._mark_missed(
                automation_id=automation_id,
                due_at_utc=due_at_utc,
                now=now,
            )
            return

        run_id = self._claim(
            automation_id=automation_id,
            due_at_utc=due_at_utc,
            now=now,
        )
        if run_id is None:
            return

        self._deliver(
            run_id=run_id,
            automation_id=automation_id,
            due_at_utc=due_at_utc,
            now=now,
        )

    def _claim(
        self,
        *,
        automation_id: str,
        due_at_utc: datetime,
        now: datetime,
    ) -> str | None:
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            definition = repository.get_definition(automation_id)
            if not self._matches_due(
                definition,
                due_at_utc=due_at_utc,
            ):
                return None

            run = AutomationRunRecord(
                id=str(uuid4()),
                automation_id=definition.id,
                definition_digest=definition.definition_digest,
                due_at_utc=due_at_utc,
                status="claimed",
                claimed_at=now,
                delivered_at=None,
                created_at=now,
                updated_at=now,
            )
            try:
                repository.add_run(run)
                repository.commit()
            except IntegrityError:
                repository.rollback()
                return None
            return run.id

    def _deliver(
        self,
        *,
        run_id: str,
        automation_id: str,
        due_at_utc: datetime,
        now: datetime,
    ) -> None:
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            definition = repository.get_definition(automation_id)
            if not self._matches_due(
                definition,
                due_at_utc=due_at_utc,
            ):
                return

            next_due, completed = self._advance_target(
                repository,
                definition,
                reference_utc=due_at_utc,
            )
            if not repository.transition_claimed_run(
                run_id,
                new_status="delivered",
                changed_at=now,
            ):
                repository.rollback()
                return
            if not repository.advance_if_due(
                automation_id,
                expected_due_at_utc=due_at_utc,
                next_due_at_utc=next_due,
                completed=completed,
                changed_at=now,
            ):
                repository.rollback()
                return
            repository.commit()

    def _mark_missed(
        self,
        *,
        automation_id: str,
        due_at_utc: datetime,
        now: datetime,
    ) -> None:
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            definition = repository.get_definition(automation_id)
            if not self._matches_due(
                definition,
                due_at_utc=due_at_utc,
            ):
                return

            run = AutomationRunRecord(
                id=str(uuid4()),
                automation_id=definition.id,
                definition_digest=definition.definition_digest,
                due_at_utc=due_at_utc,
                status="missed",
                claimed_at=None,
                delivered_at=None,
                created_at=now,
                updated_at=now,
            )
            try:
                repository.add_run(run)
                next_due, completed = self._advance_target(
                    repository,
                    definition,
                    reference_utc=now,
                )
                if not repository.advance_if_due(
                    automation_id,
                    expected_due_at_utc=due_at_utc,
                    next_due_at_utc=next_due,
                    completed=completed,
                    changed_at=now,
                ):
                    repository.rollback()
                    return
                repository.commit()
            except IntegrityError:
                repository.rollback()

    def _mark_indeterminate(
        self,
        *,
        run_id: str,
        automation_id: str,
        due_at_utc: datetime,
        now: datetime,
    ) -> None:
        with self._session_factory() as session:
            repository = AutomationRepository(session)
            definition = repository.get_definition(automation_id)
            if not self._matches_due(
                definition,
                due_at_utc=due_at_utc,
            ):
                return

            next_due, completed = self._advance_target(
                repository,
                definition,
                reference_utc=now,
            )
            if not repository.transition_claimed_run(
                run_id,
                new_status="indeterminate",
                changed_at=now,
            ):
                repository.rollback()
                return
            if not repository.advance_if_due(
                automation_id,
                expected_due_at_utc=due_at_utc,
                next_due_at_utc=next_due,
                completed=completed,
                changed_at=now,
            ):
                repository.rollback()
                return
            repository.commit()

    @staticmethod
    def _matches_due(
        definition: AutomationDefinitionRecord | None,
        *,
        due_at_utc: datetime,
    ) -> bool:
        if (
            definition is None
            or definition.status != "approved"
            or definition.next_due_at_utc is None
        ):
            return False
        return (
            AutomationRunService._db_datetime(
                definition.next_due_at_utc
            )
            == due_at_utc
        )

    @staticmethod
    def _advance_target(
        repository: AutomationRepository,
        definition: AutomationDefinitionRecord,
        *,
        reference_utc: datetime,
    ) -> tuple[datetime | None, bool]:
        run_count = repository.count_runs_for_automation(definition.id)
        if definition.schedule_kind == "once":
            return None, True
        if run_count >= definition.max_runs:
            return None, True
        return (
            next_due_after(
                definition,
                after_utc=reference_utc,
            ),
            False,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise RuntimeError("automation clock must be timezone-aware.")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _db_datetime(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


__all__ = [
    "AUTOMATION_DUE_BATCH_MAX",
    "AUTOMATION_MISFIRE_GRACE",
    "AUTOMATION_STALE_CLAIM_AGE",
    "AutomationRunService",
]
