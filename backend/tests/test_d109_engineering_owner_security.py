from __future__ import annotations

import inspect
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.v1 import engineering
from app.schemas.engineering_owner import (
    EngineeringOwnerDecisionRequest,
    EngineeringOwnerProposalRequest,
    EngineeringOwnerReadRequest,
)
from app.services import engineering_owner_workflow


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_d109_local_marker_is_mandatory_for_engineering_api() -> None:
    with pytest.raises(Exception) as error:
        engineering.require_local_engineering_owner_request_marker(None)

    assert getattr(error.value, "status_code", None) == 403
    engineering.require_local_engineering_owner_request_marker("1")


def test_d109_decision_schema_accepts_only_conversation_and_digest() -> None:
    valid = EngineeringOwnerDecisionRequest(
        conversation_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        proposal_digest="a" * 64,
    )
    assert valid.conversation_id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert valid.proposal_digest == "a" * 64

    for injected in (
        {"relative_path": "backend/app.py"},
        {"proposed_content": "evil"},
        {"repository_root": "D:/evil"},
        {"workspace_id": "company"},
        {"expected_sha256": "0" * 64},
        {"plan_digest": "0" * 64},
    ):
        with pytest.raises(ValidationError):
            EngineeringOwnerDecisionRequest(
                conversation_id=UUID(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                ),
                proposal_digest="a" * 64,
                **injected,
            )


def test_d109_proposal_schema_cannot_inject_server_authority() -> None:
    forbidden_payloads = (
        {"repository_root": "D:/evil"},
        {"workspace_id": "company"},
        {"approval_id": "approval-evil"},
        {"proposal_digest": "0" * 64},
        {"expected_sha256": "0" * 64},
        {"plan_digest": "0" * 64},
    )
    for injected in forbidden_payloads:
        with pytest.raises(ValidationError):
            EngineeringOwnerProposalRequest(
                conversation_id=UUID(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                ),
                operation="create_text",
                relative_path="backend/new.py",
                proposed_content="value = 1\n",
                **injected,
            )


def test_d109_read_schema_cannot_supply_workspace_or_root() -> None:
    for injected in (
        {"workspace_id": "company"},
        {"repository_root": "D:/evil"},
    ):
        with pytest.raises(ValidationError):
            EngineeringOwnerReadRequest(
                conversation_id=UUID(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                ),
                operation="read_text",
                relative_path="backend/app.py",
                **injected,
            )


def test_d109_workflow_delegates_apply_only_to_d108_execution_service() -> None:
    source = inspect.getsource(engineering_owner_workflow)

    assert "EngineeringApplyExecutionService" in source
    assert "self._execution_service.apply(" in source

    forbidden = (
        "FilesystemCreateTextToolAdapter",
        "FilesystemReplaceTextToolAdapter",
        "ToolRuntime(",
        "ExecutionGuard(",
        "ExecutionPlanner",
        "CommandExecutionCoordinator",
        "subprocess",
        "os.system",
        "git push",
        "requests.",
        "httpx.",
    )
    for token in forbidden:
        assert token not in source


def test_d109_api_has_no_direct_d48_or_generic_execution_authority() -> None:
    source = inspect.getsource(engineering)

    forbidden = (
        "FilesystemCreateTextToolAdapter",
        "FilesystemReplaceTextToolAdapter",
        "ToolRuntime",
        "ExecutionGuard",
        "ExecutionApprovalService",
        "ExecutionPlanner",
        "CommandExecutionCoordinator",
        "subprocess",
        "os.system",
        "requests.",
        "httpx.",
    )
    for token in forbidden:
        assert token not in source


def test_d109_plaintext_chat_has_no_engineering_decision_bridge() -> None:
    source = _read("backend/app/api/v1/chat.py")

    forbidden = (
        "EngineeringOwnerWorkflowService",
        "EngineeringApplyApprovalService",
        "EngineeringApplyExecutionService",
        "approve_engineering_proposal",
        "deny_engineering_proposal",
        "apply_engineering_proposal",
        "/engineering/approvals/",
    )
    for token in forbidden:
        assert token not in source


def test_d109_shared_process_local_stores_are_cached_dependencies() -> None:
    source = _read("backend/app/api/dependencies.py")

    assert "@lru_cache\ndef get_engineering_apply_approval_store" in source
    assert "@lru_cache\ndef get_engineering_owner_binding_store" in source
    assert "get_engineering_apply_execution_service(" in source
    assert "approval_store=approval_store" in source
    assert "repository_root=get_engineering_repository_root()" in source


def test_d109_frontend_keeps_owner_authority_out_of_browser_storage() -> None:
    panel = _read(
        "frontend/components/chat/engineering-owner-panel.tsx"
    )
    card = _read(
        "frontend/components/chat/engineering-proposal-card.tsx"
    )

    for source in (panel, card):
        assert "localStorage" not in source
        assert "sessionStorage" not in source
        assert "repository_root" not in source
        assert "plan_digest" not in source
        assert "expected_sha256" not in source


def test_d109_frontend_apply_payload_has_no_path_content_or_root() -> None:
    source = _read("frontend/lib/api-client.ts")
    marker = "function engineeringDecisionRequest("
    start = source.index(marker)
    end = source.index(
        "export function approveEngineeringProposal",
        start,
    )
    decision_source = source[start:end]

    assert "conversation_id: conversationId" in decision_source
    assert "proposal_digest: proposalDigest" in decision_source
    assert "relative_path" not in decision_source
    assert "proposed_content" not in decision_source
    assert "repository_root" not in decision_source
    assert "expected_sha256" not in decision_source
    assert "plan_digest" not in decision_source


def test_d109_frontend_exposes_no_terminal_retry_control() -> None:
    card = _read(
        "frontend/components/chat/engineering-proposal-card.tsx"
    )

    assert "No Retry is available." in card
    assert ">Retry<" not in card
    assert '"Retry"' not in card
    assert "'Retry'" not in card


def test_d109_chat_mounts_engineering_by_exact_workspace_conversation_key() -> None:
    source = _read("frontend/components/chat/chat.tsx")

    assert "<EngineeringOwnerPanel" in source
    assert 'key={`${workspaceId}:${conversationId ?? "none"}`}' in source
    assert "conversationId={conversationId}" in source
    assert "workspaceId={workspaceId}" in source
    assert "approveEngineeringProposal" not in source
    assert "applyEngineeringProposal" not in source


def test_d109_engineering_routes_are_exact_and_bounded() -> None:
    paths = {
        route.path
        for route in engineering.router.routes
    }

    assert paths == {
        "/engineering/read",
        "/engineering/proposals",
        "/engineering/ai-drafts",
        "/engineering/conversations/{conversation_id}/active",
        "/engineering/approvals/{approval_id}/approve",
        "/engineering/approvals/{approval_id}/deny",
        "/engineering/approvals/{approval_id}/apply",
    }


def test_d109_closeout_review_contract_version_and_expired_terminal() -> None:
    binding = _read("backend/app/services/engineering_owner_binding.py")
    schema = _read("backend/app/schemas/engineering_owner.py")
    frontend_types = _read("frontend/types/chat.ts")
    card = _read("frontend/components/chat/engineering-proposal-card.tsx")

    assert "contract_version=proposal.contract_version" in binding
    assert "contract_version: str" in schema
    assert "contract_version=review.contract_version" in schema
    assert "contract_version: string;" in frontend_types

    assert 'presentation_state="expired"' in binding
    assert 'reason_code="engineering_apply_expired"' in binding
    assert '"expired",' in schema
    assert '| "expired";' in frontend_types
    assert '"expired",' in card
    assert "No Retry is available." in card


def test_d109_closeout_expiry_remains_presentation_only() -> None:
    binding = _read("backend/app/services/engineering_owner_binding.py")
    workflow = _read("backend/app/services/engineering_owner_workflow.py")

    cleanup_start = binding.index("    def _cleanup(self, now: datetime) -> None:")
    cleanup_end = binding.index(
        "    def _for_conversation_locked(",
        cleanup_start,
    )
    cleanup = binding[cleanup_start:cleanup_end]

    assert 'presentation_state="expired"' in cleanup
    assert "engineering_apply_expired" in cleanup
    assert "self._execution_service.apply(" not in cleanup
    assert "FilesystemCreateTextToolAdapter" not in cleanup
    assert "FilesystemReplaceTextToolAdapter" not in cleanup

    assert "self._execution_service.apply(" in workflow
