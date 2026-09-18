"""D89 read-only delivery/settings projection over durable D79 automation state."""

from __future__ import annotations

from datetime import datetime, timezone

from app.contracts.automation_delivery import (
    AUTOMATION_DELIVERY_LIST_DEFAULT,
    AUTOMATION_DELIVERY_LIST_MAX,
    AutomationDeliveryView,
    AutomationSettingsView,
)
from app.repositories.automations import AutomationRepository


class AutomationDeliveryReadError(RuntimeError):
    reason_code = "automation_delivery_read_error"


class AutomationDeliveryStorageInvariantError(AutomationDeliveryReadError):
    reason_code = "automation_delivery_storage_invariant"


class AutomationDeliveryService:
    """Read owner-visible terminal reminder runs without changing authority."""

    def __init__(
        self,
        repository: AutomationRepository,
        *,
        enabled: bool,
        owner_timezone: str,
    ) -> None:
        if not isinstance(repository, AutomationRepository):
            raise TypeError("repository must be an AutomationRepository.")
        if type(enabled) is not bool:
            raise TypeError("enabled must be an exact bool.")
        if (
            not isinstance(owner_timezone, str)
            or not owner_timezone
            or owner_timezone != owner_timezone.strip()
            or len(owner_timezone) > 128
        ):
            raise ValueError("owner_timezone must be a valid trimmed string.")
        self._repository = repository
        self._enabled = enabled
        self._owner_timezone = owner_timezone

    def settings(self) -> AutomationSettingsView:
        return AutomationSettingsView(
            enabled=self._enabled,
            owner_timezone=self._owner_timezone,
        )

    def list_deliveries(
        self,
        *,
        limit: int = AUTOMATION_DELIVERY_LIST_DEFAULT,
    ) -> tuple[AutomationDeliveryView, ...]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= AUTOMATION_DELIVERY_LIST_MAX
        ):
            raise ValueError("automation_delivery_limit_invalid")

        result: list[AutomationDeliveryView] = []
        for run in self._repository.list_terminal_runs_newest(
            limit=limit
        ):
            definition = self._repository.get_definition(
                run.automation_id
            )
            if (
                definition is None
                or definition.definition_digest
                != run.definition_digest
                or definition.kind != "local_reminder"
            ):
                raise AutomationDeliveryStorageInvariantError(
                    AutomationDeliveryStorageInvariantError.reason_code
                )
            try:
                result.append(
                    AutomationDeliveryView(
                        automation_id=run.automation_id,
                        run_id=run.id,
                        scheduled_for=self._db_datetime(
                            run.due_at_utc
                        ),
                        status=run.status,
                        message=definition.message,
                    )
                )
            except (TypeError, ValueError) as error:
                raise AutomationDeliveryStorageInvariantError(
                    AutomationDeliveryStorageInvariantError.reason_code
                ) from error
        return tuple(result)

    @staticmethod
    def _db_datetime(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise AutomationDeliveryStorageInvariantError(
                AutomationDeliveryStorageInvariantError.reason_code
            )
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


__all__ = [
    "AutomationDeliveryReadError",
    "AutomationDeliveryService",
    "AutomationDeliveryStorageInvariantError",
]
