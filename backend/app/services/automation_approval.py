"""D79 durable automation proposal/approval lifecycle."""

from __future__ import annotations

import hmac
import re
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from app.contracts.automation import (
    DailyAutomationSchedule,
    LocalReminderAutomationDefinition,
    OnceAutomationSchedule,
)
from app.contracts.automation_approval import (
    AUTOMATION_ACTIVE_MAX,
    AUTOMATION_APPROVAL_TTL,
    AUTOMATION_LIST_MAX,
    AUTOMATION_ONCE_MAX_HORIZON,
    AUTOMATION_ONCE_MIN_LEAD,
    AUTOMATION_PENDING_MAX,
    AutomationCancelOutcome,
    AutomationDecisionOutcome,
    AutomationDefinitionView,
    AutomationPreview,
    AutomationProposalOutcome,
    AutomationRunView,
)
from app.models.automation_definition import AutomationDefinitionRecord
from app.models.automation_run import AutomationRunRecord
from app.repositories.automations import AutomationRepository
from app.services.automation_digest import automation_definition_digest
from app.services.automation_schedule import (
    AutomationScheduleError,
    initial_due_at_utc,
)


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class AutomationLifecycleError(RuntimeError):
    reason_code = "automation_lifecycle_error"


class AutomationDisabledError(AutomationLifecycleError):
    reason_code = "automation_disabled"


class AutomationProposalInvalidError(AutomationLifecycleError):
    reason_code = "automation_proposal_invalid"


class AutomationPendingCapacityError(AutomationLifecycleError):
    reason_code = "automation_pending_capacity_reached"


class AutomationActiveCapacityError(AutomationLifecycleError):
    reason_code = "automation_active_capacity_reached"


class AutomationNotFoundError(AutomationLifecycleError):
    reason_code = "automation_not_found"


class AutomationExpiredError(AutomationLifecycleError):
    reason_code = "automation_proposal_expired"


class AutomationDigestMismatchError(AutomationLifecycleError):
    reason_code = "automation_definition_digest_mismatch"


class AutomationNotPendingError(AutomationLifecycleError):
    reason_code = "automation_not_pending"


class AutomationNotActiveError(AutomationLifecycleError):
    reason_code = "automation_not_active"


class AutomationStorageInvariantError(AutomationLifecycleError):
    reason_code = "automation_storage_invariant"


class AutomationApprovalService:
    """Own durable D79 grants without scheduler or capability execution."""

    def __init__(
        self,
        repository: AutomationRepository,
        *,
        enabled: bool,
        owner_timezone: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(repository, AutomationRepository):
            raise TypeError("repository must be an AutomationRepository.")
        if type(enabled) is not bool:
            raise TypeError("enabled must be an exact bool.")
        if (
            not isinstance(owner_timezone, str)
            or not owner_timezone
            or owner_timezone != owner_timezone.strip()
        ):
            raise ValueError("owner_timezone must be a non-empty trimmed string.")
        self._repository = repository
        self._enabled = enabled
        self._owner_timezone = owner_timezone
        self._clock = clock or (lambda: datetime.now(timezone.utc))

        # Fail fast on invalid deployment-owned timezone without caller input.
        LocalReminderAutomationDefinition(
            message="timezone-validation",
            schedule=DailyAutomationSchedule(local_time="00:00"),
            timezone=owner_timezone,
            max_runs=1,
        )

    def propose(
        self,
        *,
        message: str,
        schedule: OnceAutomationSchedule | DailyAutomationSchedule,
        max_runs: int,
    ) -> AutomationProposalOutcome:
        self._require_enabled()
        now = self._now()
        definition = self._definition(
            message=message,
            schedule=schedule,
            max_runs=max_runs,
        )
        self._validate_time_window(definition, now)

        if (
            self._repository.count_pending_after(now)
            >= AUTOMATION_PENDING_MAX
        ):
            raise AutomationPendingCapacityError(
                AutomationPendingCapacityError.reason_code
            )

        digest = automation_definition_digest(definition)
        expires_at = now + AUTOMATION_APPROVAL_TTL
        record = AutomationDefinitionRecord(
            id=str(uuid4()),
            contract_version=definition.contract_version,
            kind=definition.kind,
            message=definition.message,
            schedule_kind=definition.schedule.kind,
            run_at_iso=(
                definition.schedule.run_at.isoformat()
                if isinstance(definition.schedule, OnceAutomationSchedule)
                else None
            ),
            daily_local_time=(
                definition.schedule.local_time
                if isinstance(definition.schedule, DailyAutomationSchedule)
                else None
            ),
            timezone=definition.timezone,
            max_runs=definition.max_runs,
            definition_digest=digest,
            status="pending",
            approval_expires_at=expires_at,
            approved_at=None,
            terminal_at=None,
            next_due_at_utc=None,
            created_at=now,
            updated_at=now,
        )
        try:
            self._repository.add_definition(record)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        return AutomationProposalOutcome(
            status="pending",
            reason_code="automation_pending_owner_approval",
            automation_id=record.id,
            definition_digest=digest,
            preview=self._preview(record),
            expires_at=expires_at,
        )

    def approve(
        self,
        automation_id: str,
        definition_digest: str,
    ) -> AutomationDecisionOutcome:
        self._require_enabled()
        now = self._now()
        record = self._pending_record(
            automation_id,
            definition_digest,
            now,
        )
        if self._repository.count_approved() >= AUTOMATION_ACTIVE_MAX:
            raise AutomationActiveCapacityError(
                AutomationActiveCapacityError.reason_code
            )

        try:
            next_due_at_utc = initial_due_at_utc(
                record,
                approved_at=now,
            )
        except AutomationScheduleError as error:
            raise AutomationStorageInvariantError(
                AutomationStorageInvariantError.reason_code
            ) from error
        if not self._repository.approve_if_pending(
            record.id,
            definition_digest,
            approved_at=now,
            next_due_at_utc=next_due_at_utc,
        ):
            self._repository.rollback()
            raise AutomationNotPendingError(
                AutomationNotPendingError.reason_code
            )
        self._repository.commit()
        refreshed = self._required_record(record.id)

        return AutomationDecisionOutcome(
            status="approved",
            reason_code="automation_approved",
            automation_id=refreshed.id,
            definition_digest=refreshed.definition_digest,
            preview=self._preview(refreshed),
            expires_at=self._db_datetime(
                refreshed.approval_expires_at
            ),
        )

    def deny(
        self,
        automation_id: str,
        definition_digest: str,
    ) -> AutomationDecisionOutcome:
        now = self._now()
        record = self._pending_record(
            automation_id,
            definition_digest,
            now,
        )
        if not self._repository.deny_if_pending(
            record.id,
            definition_digest,
            terminal_at=now,
        ):
            self._repository.rollback()
            raise AutomationNotPendingError(
                AutomationNotPendingError.reason_code
            )
        self._repository.commit()
        refreshed = self._required_record(record.id)

        return AutomationDecisionOutcome(
            status="denied",
            reason_code="automation_denied",
            automation_id=refreshed.id,
            definition_digest=refreshed.definition_digest,
            preview=self._preview(refreshed),
            expires_at=self._db_datetime(
                refreshed.approval_expires_at
            ),
        )

    def cancel(self, automation_id: str) -> AutomationCancelOutcome:
        now = self._now()
        record = self._required_record(automation_id)
        if record.status != "approved":
            raise AutomationNotActiveError(
                AutomationNotActiveError.reason_code
            )
        if not self._repository.cancel_if_approved(
            record.id,
            terminal_at=now,
        ):
            self._repository.rollback()
            raise AutomationNotActiveError(
                AutomationNotActiveError.reason_code
            )
        self._repository.commit()
        refreshed = self._required_record(record.id)
        return AutomationCancelOutcome(
            status="cancelled",
            reason_code="automation_cancelled",
            automation_id=refreshed.id,
            definition_digest=refreshed.definition_digest,
        )

    def list_automations(self) -> tuple[AutomationDefinitionView, ...]:
        return tuple(
            AutomationDefinitionView(
                automation_id=record.id,
                definition_digest=record.definition_digest,
                status=record.status,
                preview=self._preview(record),
                expires_at=self._db_datetime(
                    record.approval_expires_at
                ),
                approved_at=(
                    self._db_datetime(record.approved_at)
                    if record.approved_at is not None
                    else None
                ),
                terminal_at=(
                    self._db_datetime(record.terminal_at)
                    if record.terminal_at is not None
                    else None
                ),
            )
            for record in self._repository.list_definitions(
                limit=AUTOMATION_LIST_MAX
            )
        )

    def list_runs(self) -> tuple[AutomationRunView, ...]:
        result: list[AutomationRunView] = []
        for run in self._repository.list_runs(limit=AUTOMATION_LIST_MAX):
            definition = self._repository.get_definition(
                run.automation_id
            )
            if definition is None:
                raise AutomationStorageInvariantError(
                    AutomationStorageInvariantError.reason_code
                )
            result.append(
                AutomationRunView(
                    automation_id=run.automation_id,
                    run_id=run.id,
                    scheduled_for=self._db_datetime(run.due_at_utc),
                    status=run.status,
                    message=definition.message,
                )
            )
        return tuple(result)

    def _pending_record(
        self,
        automation_id: str,
        definition_digest: str,
        now: datetime,
    ) -> AutomationDefinitionRecord:
        self._validate_digest(definition_digest)
        record = self._required_record(automation_id)
        if record.status != "pending":
            raise AutomationNotPendingError(
                AutomationNotPendingError.reason_code
            )
        if (
            self._db_datetime(record.approval_expires_at)
            <= now
        ):
            raise AutomationExpiredError(
                AutomationExpiredError.reason_code
            )
        if not hmac.compare_digest(
            record.definition_digest,
            definition_digest,
        ):
            raise AutomationDigestMismatchError(
                AutomationDigestMismatchError.reason_code
            )
        return record

    def _required_record(
        self,
        automation_id: str,
    ) -> AutomationDefinitionRecord:
        if (
            not isinstance(automation_id, str)
            or not automation_id
            or automation_id != automation_id.strip()
            or len(automation_id) > 128
        ):
            raise AutomationNotFoundError(
                AutomationNotFoundError.reason_code
            )
        record = self._repository.get_definition(automation_id)
        if record is None:
            raise AutomationNotFoundError(
                AutomationNotFoundError.reason_code
            )
        return record

    def _definition(
        self,
        *,
        message: str,
        schedule: OnceAutomationSchedule | DailyAutomationSchedule,
        max_runs: int,
    ) -> LocalReminderAutomationDefinition:
        try:
            return LocalReminderAutomationDefinition(
                message=message,
                schedule=schedule,
                timezone=self._owner_timezone,
                max_runs=max_runs,
            )
        except (TypeError, ValueError) as error:
            raise AutomationProposalInvalidError(
                AutomationProposalInvalidError.reason_code
            ) from error

    @staticmethod
    def _validate_time_window(
        definition: LocalReminderAutomationDefinition,
        now: datetime,
    ) -> None:
        if not isinstance(definition.schedule, OnceAutomationSchedule):
            return
        run_at = definition.schedule.run_at.astimezone(timezone.utc)
        if (
            run_at < now + AUTOMATION_ONCE_MIN_LEAD
            or run_at > now + AUTOMATION_ONCE_MAX_HORIZON
        ):
            raise AutomationProposalInvalidError(
                AutomationProposalInvalidError.reason_code
            )

    @staticmethod
    def _preview(
        record: AutomationDefinitionRecord,
    ) -> AutomationPreview:
        return AutomationPreview(
            contract_version=record.contract_version,
            kind=record.kind,
            message=record.message,
            schedule_kind=record.schedule_kind,
            run_at=record.run_at_iso,
            daily_local_time=record.daily_local_time,
            timezone=record.timezone,
            max_runs=record.max_runs,
        )

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise AutomationDisabledError(
                AutomationDisabledError.reason_code
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

    @staticmethod
    def _validate_digest(value: object) -> None:
        if (
            not isinstance(value, str)
            or _DIGEST_RE.fullmatch(value) is None
        ):
            raise AutomationDigestMismatchError(
                AutomationDigestMismatchError.reason_code
            )


__all__ = [
    "AutomationActiveCapacityError",
    "AutomationApprovalService",
    "AutomationDigestMismatchError",
    "AutomationDisabledError",
    "AutomationExpiredError",
    "AutomationLifecycleError",
    "AutomationNotActiveError",
    "AutomationNotFoundError",
    "AutomationNotPendingError",
    "AutomationPendingCapacityError",
    "AutomationProposalInvalidError",
    "AutomationStorageInvariantError",
]
