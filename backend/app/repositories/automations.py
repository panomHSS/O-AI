"""Persistence boundary for D79 durable automation authority."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord


class AutomationRepository:
    """Persist exact definitions and due-slot records without scheduling."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_definition(
        self,
        record: AutomationDefinitionRecord,
    ) -> AutomationDefinitionRecord:
        if not isinstance(record, AutomationDefinitionRecord):
            raise TypeError(
                "record must be an AutomationDefinitionRecord."
            )
        self._session.add(record)
        self._session.flush()
        return record

    def get_definition(
        self,
        automation_id: str,
    ) -> AutomationDefinitionRecord | None:
        return self._session.get(
            AutomationDefinitionRecord,
            automation_id,
        )

    def count_definitions_with_status(self, status: str) -> int:
        statement = (
            select(func.count())
            .select_from(AutomationDefinitionRecord)
            .where(AutomationDefinitionRecord.status == status)
        )
        return int(self._session.scalar(statement) or 0)

    def list_definitions(
        self,
        *,
        limit: int = 100,
    ) -> list[AutomationDefinitionRecord]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("limit must be between 1 and 100.")
        statement = (
            select(AutomationDefinitionRecord)
            .order_by(
                AutomationDefinitionRecord.created_at.asc(),
                AutomationDefinitionRecord.id.asc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def add_run(
        self,
        record: AutomationRunRecord,
    ) -> AutomationRunRecord:
        if not isinstance(record, AutomationRunRecord):
            raise TypeError("record must be an AutomationRunRecord.")
        self._session.add(record)
        self._session.flush()
        return record

    def get_run(
        self,
        run_id: str,
    ) -> AutomationRunRecord | None:
        return self._session.get(AutomationRunRecord, run_id)

    def count_runs_for_automation(self, automation_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(AutomationRunRecord)
            .where(
                AutomationRunRecord.automation_id == automation_id
            )
        )
        return int(self._session.scalar(statement) or 0)

    def list_runs(
        self,
        *,
        limit: int = 100,
    ) -> list[AutomationRunRecord]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("limit must be between 1 and 100.")
        statement = (
            select(AutomationRunRecord)
            .order_by(
                AutomationRunRecord.due_at_utc.asc(),
                AutomationRunRecord.id.asc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def count_pending_after(self, now) -> int:
        statement = (
            select(func.count())
            .select_from(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.status == "pending",
                AutomationDefinitionRecord.approval_expires_at > now,
            )
        )
        return int(self._session.scalar(statement) or 0)

    def count_approved(self) -> int:
        return self.count_definitions_with_status("approved")

    def approve_if_pending(
        self,
        automation_id: str,
        definition_digest: str,
        *,
        approved_at,
        next_due_at_utc,
    ) -> bool:
        result = self._session.execute(
            update(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.id == automation_id,
                AutomationDefinitionRecord.status == "pending",
                AutomationDefinitionRecord.definition_digest
                == definition_digest,
            )
            .values(
                status="approved",
                approved_at=approved_at,
                next_due_at_utc=next_due_at_utc,
                updated_at=approved_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def deny_if_pending(
        self,
        automation_id: str,
        definition_digest: str,
        *,
        terminal_at,
    ) -> bool:
        result = self._session.execute(
            update(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.id == automation_id,
                AutomationDefinitionRecord.status == "pending",
                AutomationDefinitionRecord.definition_digest
                == definition_digest,
            )
            .values(
                status="denied",
                terminal_at=terminal_at,
                updated_at=terminal_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def cancel_if_approved(
        self,
        automation_id: str,
        *,
        terminal_at,
    ) -> bool:
        result = self._session.execute(
            update(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.id == automation_id,
                AutomationDefinitionRecord.status == "approved",
            )
            .values(
                status="cancelled",
                terminal_at=terminal_at,
                updated_at=terminal_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def list_due_approved(self, now, *, limit: int = 32):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 32:
            raise ValueError("due limit must be between 1 and 32.")
        statement = (
            select(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.status == "approved",
                AutomationDefinitionRecord.next_due_at_utc.is_not(None),
                AutomationDefinitionRecord.next_due_at_utc <= now,
            )
            .order_by(
                AutomationDefinitionRecord.next_due_at_utc.asc(),
                AutomationDefinitionRecord.id.asc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def list_stale_claims(self, cutoff, *, limit: int = 32):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 32:
            raise ValueError("stale-claim limit must be between 1 and 32.")
        statement = (
            select(AutomationRunRecord)
            .where(
                AutomationRunRecord.status == "claimed",
                AutomationRunRecord.claimed_at.is_not(None),
                AutomationRunRecord.claimed_at <= cutoff,
            )
            .order_by(
                AutomationRunRecord.claimed_at.asc(),
                AutomationRunRecord.id.asc(),
            )
            .limit(limit)
        )
        return list(self._session.scalars(statement).all())

    def transition_claimed_run(
        self,
        run_id: str,
        *,
        new_status: str,
        changed_at,
    ) -> bool:
        if new_status not in {"delivered", "indeterminate"}:
            raise ValueError("invalid claimed-run transition.")
        values = {
            "status": new_status,
            "updated_at": changed_at,
        }
        if new_status == "delivered":
            values["delivered_at"] = changed_at
        result = self._session.execute(
            update(AutomationRunRecord)
            .where(
                AutomationRunRecord.id == run_id,
                AutomationRunRecord.status == "claimed",
            )
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1

    def advance_if_due(
        self,
        automation_id: str,
        *,
        expected_due_at_utc,
        next_due_at_utc,
        completed: bool,
        changed_at,
    ) -> bool:
        values = {
            "next_due_at_utc": next_due_at_utc,
            "updated_at": changed_at,
        }
        if completed:
            values.update(
                status="completed",
                terminal_at=changed_at,
            )
        result = self._session.execute(
            update(AutomationDefinitionRecord)
            .where(
                AutomationDefinitionRecord.id == automation_id,
                AutomationDefinitionRecord.status == "approved",
                AutomationDefinitionRecord.next_due_at_utc
                == expected_due_at_utc,
            )
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1


    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
