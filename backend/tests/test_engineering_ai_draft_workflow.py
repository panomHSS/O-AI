from uuid import uuid4

import pytest

from app.contracts.engineering_ai_draft import (
    EngineeringAIDraftRequest,
    EngineeringAIDraftResult,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.engineering_ai_draft import (
    EngineeringAIDraftConversationNotFoundError,
    EngineeringAIDraftWorkflowService,
)


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


class ConversationLookup:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.lookups: list[str] = []

    def get(self, conversation_id: str):
        self.lookups.append(conversation_id)
        return object() if self.exists else None


class DraftService:
    def __init__(self) -> None:
        self.calls = []

    def draft(self, *, workspace_scope, request):
        self.calls.append((workspace_scope, request))
        return EngineeringAIDraftResult(
            conversation_id=request.conversation_id,
            relative_path=request.relative_path,
            draft_operation="create_text",
            source_state="absent",
            source_sha256=None,
            source_size_bytes=None,
            draft_content="candidate\n",
            ai_adapter_id="local_ai.default",
        )


def request():
    return EngineeringAIDraftRequest(
        conversation_id=uuid4(),
        relative_path="new.txt",
        instruction="create a small text file",
    )


def test_d110_workflow_verifies_conversation_before_drafting() -> None:
    conversations = ConversationLookup(exists=False)
    drafts = DraftService()
    workflow = EngineeringAIDraftWorkflowService(
        workspace_scope=PERSONAL,
        conversation_repository=conversations,
        draft_service=drafts,
    )
    value = request()

    with pytest.raises(
        EngineeringAIDraftConversationNotFoundError,
        match="engineering_ai_draft_conversation_not_found",
    ):
        workflow.draft(value)

    assert conversations.lookups == [str(value.conversation_id)]
    assert drafts.calls == []


def test_d110_workflow_forwards_exact_server_workspace_after_lookup() -> None:
    conversations = ConversationLookup(exists=True)
    drafts = DraftService()
    workflow = EngineeringAIDraftWorkflowService(
        workspace_scope=PERSONAL,
        conversation_repository=conversations,
        draft_service=drafts,
    )
    value = request()

    result = workflow.draft(value)

    assert result.conversation_id == value.conversation_id
    assert conversations.lookups == [str(value.conversation_id)]
    assert drafts.calls == [(PERSONAL, value)]
