"""D109 process-local Engineering owner workflow correlation.

This module stores presentation/correlation state only. It grants no D108 owner
approval, D36 authorization, apply claim, filesystem write, Tool, shell, Git,
network, credential, connector, or AI-provider authority.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from app.contracts.engineering_change_proposal import (
    ENGINEERING_CHANGE_CONTRACT_VERSION,
    EngineeringChangeProposal,
)
from app.contracts.workspace import WorkspaceScope


DEFAULT_ENGINEERING_OWNER_BINDING_CAPACITY = 128

EngineeringOwnerPresentationState = Literal[
    "pending",
    "approved",
    "denied",
    "applied",
    "stale",
    "failed",
    "indeterminate",
    "expired",
]

_NON_TERMINAL = frozenset({"pending", "approved"})
_TERMINAL = frozenset(
    {"denied", "applied", "stale", "failed", "indeterminate", "expired"}
)
_ALLOWED_TRANSITIONS = {
    "pending": frozenset({"approved", "denied"}),
    "approved": frozenset(
        {"applied", "stale", "failed", "indeterminate"}
    ),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringOwnerBindingError(RuntimeError):
    reason_code = "engineering_owner_binding_error"


class EngineeringOwnerActiveWorkflowError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_active_workflow_exists"


class EngineeringOwnerBindingCollisionError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_binding_mismatch"


class EngineeringOwnerBindingNotFoundError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_workflow_not_found"


class EngineeringOwnerBindingStateError(EngineeringOwnerBindingError):
    reason_code = "engineering_owner_state_invalid"


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
    contract_version: str = ENGINEERING_CHANGE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != ENGINEERING_CHANGE_CONTRACT_VERSION:
            raise ValueError("engineering_owner_request_invalid")

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
            contract_version=proposal.contract_version,
        )


@dataclass(frozen=True, slots=True)
class EngineeringOwnerBinding:
    """Non-authoritative correlation for one exact D108 workflow."""

    workspace_scope: WorkspaceScope
    conversation_id: UUID
    approval_id: str
    proposal_digest: str
    review: EngineeringOwnerReview
    expires_at: datetime
    presentation_state: EngineeringOwnerPresentationState = "pending"
    reason_code: str | None = None

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
        if self.presentation_state not in (_NON_TERMINAL | _TERMINAL):
            raise ValueError("engineering_owner_request_invalid")
        if self.reason_code is not None and (
            type(self.reason_code) is not str
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
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

            approval_existing = self._items.get(binding.approval_id)
            if approval_existing is not None:
                if approval_existing == binding:
                    return approval_existing
                raise EngineeringOwnerBindingCollisionError(
                    "Engineering approval is already bound differently."
                )

            conversation_existing = self._for_conversation_locked(
                workspace_scope=binding.workspace_scope,
                conversation_id=binding.conversation_id,
            )
            if conversation_existing is not None:
                if conversation_existing.presentation_state in _NON_TERMINAL:
                    raise EngineeringOwnerActiveWorkflowError(
                        "Conversation already has an active Engineering workflow."
                    )
                self._items.pop(
                    conversation_existing.approval_id,
                    None,
                )

            if len(self._items) >= self._max_items:
                evictable = next(
                    (
                        approval_id
                        for approval_id, item in self._items.items()
                        if item.presentation_state in _TERMINAL
                    ),
                    None,
                )
                if evictable is not None:
                    self._items.pop(evictable, None)

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
        """Return current live presentation state, including terminal state."""
        self._validate_scope_and_conversation(
            workspace_scope,
            conversation_id,
        )
        now = self._now()
        with self._lock:
            self._cleanup(now)
            return self._for_conversation_locked(
                workspace_scope=workspace_scope,
                conversation_id=conversation_id,
            )

    def require(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_id: UUID,
        approval_id: str,
        proposal_digest: str,
        expected_states: frozenset[str],
    ) -> EngineeringOwnerBinding:
        self._validate_scope_and_conversation(
            workspace_scope,
            conversation_id,
        )
        if type(approval_id) is not str or not approval_id:
            raise EngineeringOwnerBindingNotFoundError(
                "Engineering workflow was not found."
            )
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if binding is None:
                raise EngineeringOwnerBindingNotFoundError(
                    "Engineering workflow was not found."
                )
            if (
                binding.workspace_scope != workspace_scope
                or binding.conversation_id != conversation_id
                or binding.proposal_digest != proposal_digest
            ):
                raise EngineeringOwnerBindingCollisionError(
                    "Engineering workflow binding does not match."
                )
            if binding.presentation_state not in expected_states:
                raise EngineeringOwnerBindingStateError(
                    "Engineering workflow is not in the required state."
                )
            return binding

    def transition(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_id: UUID,
        approval_id: str,
        proposal_digest: str,
        expected_state: str,
        new_state: EngineeringOwnerPresentationState,
        reason_code: str,
    ) -> EngineeringOwnerBinding:
        now = self._now()
        with self._lock:
            self._cleanup(now)
            binding = self._items.get(approval_id)
            if binding is None:
                raise EngineeringOwnerBindingNotFoundError(
                    "Engineering workflow was not found."
                )
            if (
                binding.workspace_scope != workspace_scope
                or binding.conversation_id != conversation_id
                or binding.proposal_digest != proposal_digest
            ):
                raise EngineeringOwnerBindingCollisionError(
                    "Engineering workflow binding does not match."
                )
            if binding.presentation_state != expected_state:
                raise EngineeringOwnerBindingStateError(
                    "Engineering workflow state changed."
                )
            allowed = _ALLOWED_TRANSITIONS.get(expected_state, frozenset())
            if new_state not in allowed:
                raise EngineeringOwnerBindingStateError(
                    "Engineering workflow transition is not allowed."
                )
            updated = replace(
                binding,
                presentation_state=new_state,
                reason_code=reason_code,
            )
            self._items[approval_id] = updated
            return updated

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
        for approval_id, binding in tuple(self._items.items()):
            if binding.expires_at > now:
                continue
            if binding.presentation_state in _NON_TERMINAL:
                self._items[approval_id] = replace(
                    binding,
                    presentation_state="expired",
                    reason_code="engineering_apply_expired",
                )

    def _for_conversation_locked(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_id: UUID,
    ) -> EngineeringOwnerBinding | None:
        for item in self._items.values():
            if (
                item.workspace_scope == workspace_scope
                and item.conversation_id == conversation_id
            ):
                return item
        return None

    @staticmethod
    def _validate_scope_and_conversation(
        workspace_scope: WorkspaceScope,
        conversation_id: UUID,
    ) -> None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_owner_workspace_mismatch")
        if not isinstance(conversation_id, UUID):
            raise ValueError("engineering_owner_request_invalid")


__all__ = [
    "DEFAULT_ENGINEERING_OWNER_BINDING_CAPACITY",
    "EngineeringOwnerActiveWorkflowError",
    "EngineeringOwnerBinding",
    "EngineeringOwnerBindingCollisionError",
    "EngineeringOwnerBindingError",
    "EngineeringOwnerBindingNotFoundError",
    "EngineeringOwnerBindingStateError",
    "EngineeringOwnerBindingStore",
    "EngineeringOwnerBindingStoreFullError",
    "EngineeringOwnerPresentationState",
    "EngineeringOwnerReview",
]
