from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_owner_binding import (
    EngineeringOwnerActiveWorkflowError,
    EngineeringOwnerBinding,
    EngineeringOwnerBindingStore,
    EngineeringOwnerReview,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


def _binding(*, approval_id: str = "approval-1") -> EngineeringOwnerBinding:
    return EngineeringOwnerBinding(
        workspace_scope=PERSONAL,
        conversation_id=uuid4(),
        approval_id=approval_id,
        proposal_digest="a" * 64,
        review=EngineeringOwnerReview(
            operation="create_text",
            relative_path="backend/new.py",
            base_state="absent",
            before_content=None,
            before_sha256=None,
            before_size_bytes=None,
            after_content="value = 2\n",
            after_sha256="b" * 64,
            after_size_bytes=10,
        ),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )


def test_d109_binding_round_trip() -> None:
    store = EngineeringOwnerBindingStore()
    binding = _binding()

    assert store.bind(binding) == binding
    assert (
        store.active_for_conversation(
            workspace_scope=PERSONAL,
            conversation_id=binding.conversation_id,
        )
        == binding
    )


def test_d109_one_active_workflow_per_conversation() -> None:
    store = EngineeringOwnerBindingStore()
    first = _binding(approval_id="approval-1")
    second = EngineeringOwnerBinding(
        workspace_scope=first.workspace_scope,
        conversation_id=first.conversation_id,
        approval_id="approval-2",
        proposal_digest="c" * 64,
        review=first.review,
        expires_at=first.expires_at,
    )

    store.bind(first)

    with pytest.raises(EngineeringOwnerActiveWorkflowError):
        store.bind(second)


def test_d109_binding_expires_and_rehydrates_none() -> None:
    now_box = [datetime(2026, 9, 21, tzinfo=timezone.utc)]
    store = EngineeringOwnerBindingStore(clock=lambda: now_box[0])
    binding = EngineeringOwnerBinding(
        workspace_scope=PERSONAL,
        conversation_id=uuid4(),
        approval_id="approval-1",
        proposal_digest="a" * 64,
        review=_binding().review,
        expires_at=now_box[0] + timedelta(seconds=1),
    )
    store.bind(binding)

    now_box[0] = now_box[0] + timedelta(seconds=2)

    assert (
        store.active_for_conversation(
            workspace_scope=PERSONAL,
            conversation_id=binding.conversation_id,
        )
        is None
    )


def test_d109_binding_is_workspace_isolated() -> None:
    store = EngineeringOwnerBindingStore()
    binding = _binding()
    company = WorkspaceScope(WorkspaceId.COMPANY)
    store.bind(binding)

    assert (
        store.active_for_conversation(
            workspace_scope=company,
            conversation_id=binding.conversation_id,
        )
        is None
    )
