from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.contracts.calendar_delete_decision import CalendarDeleteDecisionBinding
from app.contracts.workspace import WorkspaceId


NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
CONVERSATION_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


def test_d101_delete_decision_binding_is_exact_workspace_correlation() -> None:
    binding = CalendarDeleteDecisionBinding(
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
def test_d101_delete_decision_binding_rejects_invalid_correlation(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        CalendarDeleteDecisionBinding(
            approval_id=value,
            write_digest="digest-1",
            workspace_id=WorkspaceId.PERSONAL,
            conversation_id=CONVERSATION_ID,
            expires_at=NOW,
        )
