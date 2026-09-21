"""D109 backend owner workflow foundation.

Batch 01 exposes bounded D106 reads and structured D107 proposal creation with
D108 pending registration. It deliberately exposes no Approve, Deny, Apply, D36,
D38, D48, shell, Git, network, credential, connector, or AI execution surface.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.contracts.engineering_change_proposal import (
    EngineeringChangeDraft,
    EngineeringChangeOperation,
)
from app.contracts.engineering_read import (
    EngineeringReadOperation,
    EngineeringReadRequest,
)
from app.contracts.workspace import WorkspaceScope
from app.services.engineering_apply_approval import (
    EngineeringApplyApprovalError,
    EngineeringApplyApprovalService,
)
from app.services.engineering_change_proposal import (
    EngineeringChangeProposalError,
    EngineeringChangeProposalService,
)
from app.services.engineering_owner_binding import (
    EngineeringOwnerActiveWorkflowError,
    EngineeringOwnerBinding,
    EngineeringOwnerBindingError,
    EngineeringOwnerBindingStore,
    EngineeringOwnerReview,
)
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)


class _ConversationLookup(Protocol):
    def get(self, conversation_id: str) -> object | None: ...


class EngineeringOwnerWorkflowError(RuntimeError):
    reason_code = "engineering_owner_error"


class EngineeringOwnerConversationNotFoundError(
    EngineeringOwnerWorkflowError
):
    reason_code = "engineering_owner_conversation_not_found"


class EngineeringOwnerRequestError(EngineeringOwnerWorkflowError):
    reason_code = "engineering_owner_request_invalid"


class EngineeringOwnerUpstreamError(EngineeringOwnerWorkflowError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class EngineeringOwnerWorkflowService:
    """Workspace-bound D109 read/propose/rehydrate orchestration."""

    def __init__(
        self,
        *,
        workspace_scope: WorkspaceScope,
        conversation_repository: _ConversationLookup,
        repository_reader: EngineeringRepositoryReader,
        proposal_service: EngineeringChangeProposalService,
        approval_service: EngineeringApplyApprovalService,
        binding_store: EngineeringOwnerBindingStore,
    ) -> None:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise ValueError("engineering_owner_workspace_mismatch")
        if not callable(getattr(conversation_repository, "get", None)):
            raise TypeError("conversation_repository must support get().")
        if not isinstance(repository_reader, EngineeringRepositoryReader):
            raise TypeError(
                "repository_reader must be EngineeringRepositoryReader."
            )
        if not isinstance(
            proposal_service,
            EngineeringChangeProposalService,
        ):
            raise TypeError(
                "proposal_service must be EngineeringChangeProposalService."
            )
        if not isinstance(
            approval_service,
            EngineeringApplyApprovalService,
        ):
            raise TypeError(
                "approval_service must be EngineeringApplyApprovalService."
            )
        if not isinstance(binding_store, EngineeringOwnerBindingStore):
            raise TypeError(
                "binding_store must be EngineeringOwnerBindingStore."
            )
        self._workspace_scope = workspace_scope
        self._conversations = conversation_repository
        self._reader = repository_reader
        self._proposal_service = proposal_service
        self._approval_service = approval_service
        self._bindings = binding_store

    @property
    def workspace_scope(self) -> WorkspaceScope:
        return self._workspace_scope

    def read(
        self,
        *,
        conversation_id: UUID,
        operation: str,
        relative_path: str | None,
    ):
        self._require_conversation(conversation_id)
        try:
            read_operation = EngineeringReadOperation(operation)
            request = EngineeringReadRequest(
                workspace_scope=self._workspace_scope,
                operation=read_operation,
                relative_path=relative_path,
            )
            return self._reader.read(request)
        except (TypeError, ValueError):
            raise EngineeringOwnerRequestError(
                "engineering_owner_request_invalid"
            ) from None
        except EngineeringReadError as exc:
            raise EngineeringOwnerUpstreamError(exc.code) from None

    def propose(
        self,
        *,
        conversation_id: UUID,
        operation: str,
        relative_path: str,
        proposed_content: str,
    ) -> EngineeringOwnerBinding:
        self._require_conversation(conversation_id)
        if (
            self._bindings.active_for_conversation(
                workspace_scope=self._workspace_scope,
                conversation_id=conversation_id,
            )
            is not None
        ):
            raise EngineeringOwnerActiveWorkflowError(
                "Conversation already has an active Engineering workflow."
            )

        try:
            change_operation = EngineeringChangeOperation(operation)
            draft = EngineeringChangeDraft(
                workspace_scope=self._workspace_scope,
                operation=change_operation,
                relative_path=relative_path,
                proposed_content=proposed_content,
            )
            proposal = self._proposal_service.propose(draft)
            pending = self._approval_service.propose(proposal).proposal
        except (TypeError, ValueError):
            raise EngineeringOwnerRequestError(
                "engineering_owner_request_invalid"
            ) from None
        except EngineeringChangeProposalError as exc:
            raise EngineeringOwnerUpstreamError(exc.code) from None
        except EngineeringApplyApprovalError as exc:
            raise EngineeringOwnerUpstreamError(exc.reason_code) from None

        binding = EngineeringOwnerBinding(
            workspace_scope=self._workspace_scope,
            conversation_id=conversation_id,
            approval_id=pending.approval_id,
            proposal_digest=pending.proposal_digest,
            review=EngineeringOwnerReview.from_proposal(pending.proposal),
            expires_at=pending.expires_at,
        )
        return self._bindings.bind(binding)

    def active(
        self,
        *,
        conversation_id: UUID,
    ) -> EngineeringOwnerBinding | None:
        self._require_conversation(conversation_id)
        return self._bindings.active_for_conversation(
            workspace_scope=self._workspace_scope,
            conversation_id=conversation_id,
        )

    def _require_conversation(self, conversation_id: UUID) -> object:
        if not isinstance(conversation_id, UUID):
            raise EngineeringOwnerRequestError(
                "engineering_owner_request_invalid"
            )
        conversation = self._conversations.get(str(conversation_id))
        if conversation is None:
            raise EngineeringOwnerConversationNotFoundError(
                "The requested conversation was not found in this workspace."
            )
        return conversation


__all__ = [
    "EngineeringOwnerConversationNotFoundError",
    "EngineeringOwnerRequestError",
    "EngineeringOwnerUpstreamError",
    "EngineeringOwnerWorkflowError",
    "EngineeringOwnerWorkflowService",
]
