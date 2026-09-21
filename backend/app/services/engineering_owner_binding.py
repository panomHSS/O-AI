"""D109 process-local Engineering owner workflow correlation.

This module stores presentation/correlation state only. It grants no D108 owner
approval, D36 authorization, apply claim, filesystem write, Tool, shell, Git,
network, credential, connector, or AI-provider authority.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from app.contracts.engineering_change_proposal import EngineeringChangeProposal
from app.contracts.workspace import WorkspaceScope


DEFAULT_ENGINEERING_OWNER_BINDING_CAPACITY = 128
EngineeringOwnerPresentationState = Literal["pending"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringOwnerBindingError(RuntimeError):
    reason_code = "engineering_owner_binding_error"


class EngineeringOwnerActiveWorkflowError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_active_workflow_exists"


class EngineeringOwnerBindingCollisionError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_binding_mismatch"


class EngineeringOwnerBindingStoreFullError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_store_full"


@dataclass(frozen=True, slots=True)
class EngineeringOwnerReview:
    """Safe owner-visible projection of one exact D107 proposal."""

    operation: str
    relative_path: str
    base_state: str
    before_content: str | None
    before_sha256: str | None
    before_size_bytes: int | None
    after_content: str
    after_sha256: str
    after_size_bytes: int

    @classmethod
    def from_proposal(
        cls,
        proposal: EngineeringChangeProposal,
    ) -> "EngineeringOwnerReview":
        if not isinstance(proposal, EngineeringChangeProposal):
            raise ValueError("engineering_owner_request_invalid")
        return cls(
            operation=proposal.operation.value,
            relative_path=proposal.relative_path,
            base_state=proposal.base_state.value,
            before_content=proposal.base_content,
            before_sha256=proposal.base_sha256,
            before_size_bytes=proposal.base_size_bytes,
            after_content=proposal.proposed_content,
            after_sha256=proposal.proposed_sha256,
            after_size_bytes=proposal.proposed_size_bytes,
        )


@dataclass(frozen=True, slots=True)
class EngineeringOwnerBinding:
    """Non-authoritative correlation for one exact live D108 approval."""

    workspace_scope: WorkspaceScope
    conversation_id: UUID
    approval_id: str
    proposal_digest: str
    review: EngineeringOwnerReview
    expires_at: datetime
    presentation_state: EngineeringOwnerPresentationState = "pending"

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_owner_workspace_mismatch")
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_owner_request_invalid")
        if (
            type(self.approval_id) is not str
            or not self.approval_id
            or self.approval_id != self.approval_id.strip()
        ):
            raise ValueError("engineering_owner_request_invalid")
        if (
            type(self.proposal_digest) is not str
            or len(self.proposal_digest) != 64
            or any(c not in "0123456789abcdef" for c in self.proposal_digest)
        ):
            raise ValueError("engineering_owner_binding_mismatch")
        if not isinstance(self.review, EngineeringOwnerReview):
            raise ValueError("engineering_owner_request_invalid")
        if (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
        ):
            raise ValueError("engineering_owner_request_invalid")
        if self.presentation_state != "pending":
            raise ValueError("engineering_owner_request_invalid")


class EngineeringOwnerBindingStore:
    """Bounded process-local D109 correlation only; never approval authority."""

    def __init__(
        self,
        *,
        max_items: int = DEFAULT_ENGINEERING_OWNER_BINDING_CAPACITY,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        if (
            isinstance(max_items, bool)
            or not isinstance(max_items, int)
            or max_items < 1
        ):
            raise ValueError("max_items must be a positive integer.")
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, EngineeringOwnerBinding] = {}
        self._lock = threading.Lock()

    @property
    def item_count(self) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return len(self._items)

    def bind(
        self,
        binding: EngineeringOwnerBinding,
    ) -> EngineeringOwnerBinding:
        if not isinstance(binding, EngineeringOwnerBinding):
            raise ValueError("engineering_owner_request_invalid")
        now = self._now()
        with self._lock:
            self._cleanup(now)
            existing = self._items.get(binding.approval_id)
            if existing is not None:
                if existing == binding:
                    return existing
                raise EngineeringOwnerBindingCollisionError(
                    "Engineering approval is already bound differently."
                )
            if any(
                item.workspace_scope == binding.workspace_scope
                and item.conversation_id == binding.conversation_id
                for item in self._items.values()
            ):
                raise EngineeringOwnerActiveWorkflowError(
                    "Conversation already has an active Engineering workflow."
                )
            if len(self._items) >= self._max_items:
                raise EngineeringOwnerBindingStoreFullError(
                    "Engineering owner binding capacity is full."
                )
            if binding.expires_at <= now:
                raise EngineeringOwnerBindingCollisionError(
                    "Engineering owner binding is already expired."
                )
            self._items[binding.approval_id] = binding
            return binding

    def active_for_conversation(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_id: UUID,
    ) -> EngineeringOwnerBinding | None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_owner_workspace_mismatch")
        if not isinstance(conversation_id, UUID):
            raise ValueError("engineering_owner_request_invalid")
        now = self._now()
        with self._lock:
            self._cleanup(now)
            for item in self._items.values():
                if (
                    item.workspace_scope == workspace_scope
                    and item.conversation_id == conversation_id
                ):
                    return item
            return None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _now(self) -> datetime:
        now = self._clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("clock must return timezone-aware datetime.")
        return now

    def _cleanup(self, now: datetime) -> None:
        expired = [
            approval_id
            for approval_id, binding in self._items.items()
            if binding.expires_at <= now
        ]
        for approval_id in expired:
            self._items.pop(approval_id, None)


__all__ = [
    "DEFAULT_ENGINEERING_OWNER_BINDING_CAPACITY",
    "EngineeringOwnerActiveWorkflowError",
    "EngineeringOwnerBinding",
    "EngineeringOwnerBindingCollisionError",
    "EngineeringOwnerBindingError",
    "EngineeringOwnerBindingStore",
    "EngineeringOwnerBindingStoreFullError",
    "EngineeringOwnerPresentationState",
    "EngineeringOwnerReview",
]
