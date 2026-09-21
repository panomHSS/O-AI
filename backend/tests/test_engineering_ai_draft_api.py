from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1 import engineering
from app.contracts.engineering_ai_draft import EngineeringAIDraftResult
from app.schemas.engineering_ai_draft import EngineeringAIDraftCreateRequest
from app.services.engineering_ai_draft import (
    EngineeringAIDraftConversationNotFoundError,
    EngineeringAIDraftError,
)


CID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class Workflow:
    def __init__(self, *, error=None) -> None:
        self.error = error
        self.requests = []

    def draft(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
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


def payload():
    return EngineeringAIDraftCreateRequest(
        conversation_id=CID,
        relative_path="new.txt",
        instruction="write candidate text",
    )


def test_d110_api_schema_rejects_browser_authority_injection() -> None:
    forbidden = (
        {"workspace_id": "company"},
        {"workspace_scope": "company"},
        {"repository_root": "D:/evil"},
        {"operation": "replace_text"},
        {"provider": "chatgpt"},
        {"model": "evil"},
        {"approval_id": "approval"},
        {"proposal_digest": "a" * 64},
        {"apply": True},
        {"tool": "shell"},
        {"shell": "whoami"},
    )
    for injected in forbidden:
        with pytest.raises(ValidationError):
            EngineeringAIDraftCreateRequest(
                conversation_id=CID,
                relative_path="new.txt",
                instruction="safe",
                **injected,
            )


def test_d110_api_returns_only_non_authoritative_draft_projection() -> None:
    workflow = Workflow()
    response = engineering.create_engineering_ai_draft(
        payload(),
        None,
        workflow,  # type: ignore[arg-type]
    )

    assert response.data.contract_version == "d110.v1"
    assert response.data.conversation_id == CID
    assert response.data.relative_path == "new.txt"
    assert response.data.draft_operation == "create_text"
    assert response.data.draft_content == "candidate\n"
    assert workflow.requests[0].instruction == "write candidate text"
    assert not hasattr(response.data, "workspace_id")
    assert not hasattr(response.data, "approval_id")
    assert not hasattr(response.data, "proposal_digest")


def test_d110_api_maps_unknown_conversation_to_safe_404() -> None:
    workflow = Workflow(error=EngineeringAIDraftConversationNotFoundError())
    with pytest.raises(HTTPException) as error:
        engineering.create_engineering_ai_draft(
            payload(),
            None,
            workflow,  # type: ignore[arg-type]
        )
    assert error.value.status_code == 404
    assert error.value.detail == "engineering_ai_draft_conversation_not_found"


def test_d110_api_maps_local_ai_unavailable_to_safe_503() -> None:
    workflow = Workflow(
        error=EngineeringAIDraftError("engineering_ai_draft_unavailable")
    )
    with pytest.raises(HTTPException) as error:
        engineering.create_engineering_ai_draft(
            payload(),
            None,
            workflow,  # type: ignore[arg-type]
        )
    assert error.value.status_code == 503
    assert error.value.detail == "engineering_ai_draft_unavailable"
