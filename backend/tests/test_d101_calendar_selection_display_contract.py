from __future__ import annotations

from uuid import UUID

import pytest

from app.contracts.chat_plugin_action import (
    CalendarSelectionDisplayEvent,
    ChatPluginActionCompletion,
)
from app.schemas.execution_approvals import ExecutionChatCompletionResponse


CONVERSATION_ID = UUID("77777777-7777-7777-7777-777777777777")


def _display(**overrides) -> CalendarSelectionDisplayEvent:
    values = {
        "selection_id": "opaque-selection-1",
        "summary": "Planning",
        "status": "confirmed",
        "start": "2026-09-16T09:00:00+07:00",
        "end": "2026-09-16T10:00:00+07:00",
        "all_day": False,
    }
    values.update(overrides)
    return CalendarSelectionDisplayEvent(**values)


def test_d101_calendar_selection_display_contains_no_provider_identity() -> None:
    item = _display()

    assert item.selection_id == "opaque-selection-1"
    assert not hasattr(item, "event_id")
    assert not hasattr(item, "calendar_id")
    assert not hasattr(item, "followup_id")


def test_d101_chat_completion_carries_transient_calendar_selections() -> None:
    completion = ChatPluginActionCompletion(
        conversation_id=CONVERSATION_ID,
        reply="Calendar result",
        calendar_selections=(_display(),),
    )

    assert completion.calendar_selections is not None
    assert completion.calendar_selections[0].selection_id == "opaque-selection-1"


def test_d101_execution_chat_schema_exposes_only_opaque_selection_identity() -> None:
    response = ExecutionChatCompletionResponse.from_completion(
        ChatPluginActionCompletion(
            conversation_id=CONVERSATION_ID,
            reply="Calendar result",
            calendar_selections=(_display(),),
        )
    )

    payload = response.model_dump()
    assert payload["calendar_selections"] == {
        "events": [
            {
                "selection_id": "opaque-selection-1",
                "summary": "Planning",
                "status": "confirmed",
                "start": "2026-09-16T09:00:00+07:00",
                "end": "2026-09-16T10:00:00+07:00",
                "all_day": False,
            }
        ]
    }
    serialized = response.model_dump_json()
    assert "event_id" not in serialized
    assert "calendar_id" not in serialized
    assert "followup_id" not in serialized


@pytest.mark.parametrize("selection_id", ["", " padded ", "x" * 257])
def test_d101_calendar_selection_display_rejects_invalid_opaque_id(
    selection_id: str,
) -> None:
    with pytest.raises(ValueError):
        _display(selection_id=selection_id)


def test_d101_calendar_selections_require_bounded_tuple() -> None:
    with pytest.raises(ValueError):
        ChatPluginActionCompletion(
            conversation_id=CONVERSATION_ID,
            reply="Calendar result",
            calendar_selections=[_display()],
        )
