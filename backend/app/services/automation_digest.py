"""Canonical D79 automation-definition digest."""

from __future__ import annotations

import hashlib
import json

from app.contracts.automation import (
    DailyAutomationSchedule,
    LocalReminderAutomationDefinition,
    OnceAutomationSchedule,
)


def automation_definition_payload(
    definition: LocalReminderAutomationDefinition,
) -> dict[str, object]:
    """Return the exact canonical authority projection."""
    if not isinstance(definition, LocalReminderAutomationDefinition):
        raise TypeError(
            "definition must be a LocalReminderAutomationDefinition."
        )

    schedule: dict[str, object]
    if isinstance(definition.schedule, OnceAutomationSchedule):
        schedule = {
            "kind": "once",
            "run_at": definition.schedule.run_at.isoformat(),
        }
    elif isinstance(definition.schedule, DailyAutomationSchedule):
        schedule = {
            "kind": "daily",
            "local_time": definition.schedule.local_time,
        }
    else:  # pragma: no cover - guarded by the frozen contract
        raise TypeError("unsupported automation schedule.")

    return {
        "contract_version": definition.contract_version,
        "kind": definition.kind,
        "max_runs": definition.max_runs,
        "message": definition.message,
        "schedule": schedule,
        "timezone": definition.timezone,
    }


def automation_definition_digest(
    definition: LocalReminderAutomationDefinition,
) -> str:
    """Return lowercase SHA-256 over canonical UTF-8 JSON."""
    payload = automation_definition_payload(definition)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "automation_definition_digest",
    "automation_definition_payload",
]
