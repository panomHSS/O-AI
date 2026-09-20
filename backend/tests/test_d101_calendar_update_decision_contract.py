from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.calendar_update_decision import CalendarUpdateDecisionBinding
from app.contracts.workspace import WorkspaceId


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("12121212-1212-1212-1212-121212121212")


def test_d101_update_decision_binding_is_exact_workspace_correlation() -> None:
    binding = CalendarUpdateDecisionBinding(
        approval_id="approval-1",
        write_digest="digest-1",
        workspace_id=WorkspaceId.PERSONAL,
        conversation_id=CONVERSATION_ID,
        expires_at=NOW,
    )

    assert binding.approval_id == "approval-1"
    assert binding.write_digest == "digest-1"
    assert binding.workspace_id is WorkspaceId.PERSONAL
    assert binding.conversation_id == CONVERSATION_ID


@pytest.mark.parametrize("value", ["", " padded ", "x" * 257])
def test_d101_update_decision_binding_rejects_invalid_correlation(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        CalendarUpdateDecisionBinding(
            approval_id=value,
            write_digest="digest-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW,
        )
