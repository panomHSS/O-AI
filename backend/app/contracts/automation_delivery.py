"""D89 read-only local reminder delivery projection contracts v1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias


AUTOMATION_DELIVERY_LIST_DEFAULT = 20
AUTOMATION_DELIVERY_LIST_MAX = 50

AutomationDeliveryStatus: TypeAlias = Literal[
    "delivered",
    "missed",
    "indeterminate",
]


@dataclass(frozen=True, slots=True)
class AutomationDeliveryView:
    """Owner-visible projection of one terminal D79 local-reminder run."""

    automation_id: str
    run_id: str
    scheduled_for: datetime
    status: AutomationDeliveryStatus
    message: str

    def __post_init__(self) -> None:
        for value, code in (
            (self.automation_id, "automation_delivery_automation_id_invalid"),
            (self.run_id, "automation_delivery_run_id_invalid"),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value) > 128
            ):
                raise ValueError(code)

        if (
            not isinstance(self.scheduled_for, datetime)
            or self.scheduled_for.tzinfo is None
            or self.scheduled_for.utcoffset() is None
        ):
            raise ValueError("automation_delivery_scheduled_for_invalid")

        if self.status not in {
            "delivered",
            "missed",
            "indeterminate",
        }:
            raise ValueError("automation_delivery_status_invalid")

        if (
            not isinstance(self.message, str)
            or not self.message
            or self.message != self.message.strip()
            or len(self.message) > 1000
        ):
            raise ValueError("automation_delivery_message_invalid")


@dataclass(frozen=True, slots=True)
class AutomationSettingsView:
    """Safe deployment projection for owner-facing D89 UX."""

    enabled: bool
    owner_timezone: str

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("automation_settings_enabled_invalid")
        if (
            not isinstance(self.owner_timezone, str)
            or not self.owner_timezone
            or self.owner_timezone != self.owner_timezone.strip()
            or len(self.owner_timezone) > 128
        ):
            raise ValueError("automation_settings_timezone_invalid")


__all__ = [
    "AUTOMATION_DELIVERY_LIST_DEFAULT",
    "AUTOMATION_DELIVERY_LIST_MAX",
    "AutomationDeliveryStatus",
    "AutomationDeliveryView",
    "AutomationSettingsView",
]
