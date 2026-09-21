from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def section(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_d110_frozen_authority_chain_is_preserved() -> None:
    service = read("backend/app/services/engineering_ai_draft.py")
    api = read("backend/app/api/v1/engineering.py")
    panel = read("frontend/components/chat/engineering-owner-panel.tsx")
    card = read("frontend/components/chat/engineering-proposal-card.tsx")

    assert "AITaskKind.SOFTWARE_ENGINEERING" in service
    assert "LOCAL_AI_ADAPTER_ID" in service
    assert "EngineeringAIDraftWorkflowService" in service
    assert "self._conversations.get(" in service
    assert "self._draft_service.draft(" in service
    assert service.index("self._conversations.get(") < service.index(
        "self._draft_service.draft("
    )

    for forbidden in (
        "EngineeringChangeProposalService",
        "EngineeringApplyExecutionService",
        "EngineeringApplyApprovalService",
        "FilesystemCreateTextToolAdapter",
        "FilesystemReplaceTextToolAdapter",
        "ToolRuntime",
        "ModuleRuntime",
        "subprocess",
        "os.system",
        "git push",
        "git commit",
        "CredentialAccessBroker",
    ):
        assert forbidden not in service

    assert '"/ai-drafts"' in api
    assert "require_local_engineering_owner_request_marker" in api
    assert "get_engineering_ai_draft_workflow_service" in api

    assert "Create Proposal from Draft" in panel
    assert "Local AI draft (non-authoritative)" in panel
    assert "Approve" in card
    assert "Apply exact proposal" in card
    assert "No Retry is available." in card


def test_d110_browser_draft_has_no_owner_decision_authority() -> None:
    panel = read("frontend/components/chat/engineering-owner-panel.tsx")

    for forbidden in (
        "approveEngineeringProposal",
        "denyEngineeringProposal",
        "applyEngineeringProposal",
        "localStorage",
        "sessionStorage",
        "repository_root",
        "plan_digest",
        "expected_sha256",
    ):
        assert forbidden not in panel

    transition = section(
        panel,
        "async function createProposalFromDraft",
        "async function createProposal(",
    )

    assert "createEngineeringProposal" in transition
    assert "operation: aiDraft.draft_operation" in transition
    assert "relative_path: aiDraft.relative_path" in transition
    assert "proposed_content: aiDraftContent" in transition

    for forbidden in (
        "source_sha256",
        "source_size_bytes",
        "approval_id",
        "proposal_digest",
        "workspace_id",
        "repository_root",
        "provider",
        "model",
    ):
        assert forbidden not in transition


def test_d110_ai_draft_request_surface_is_exact() -> None:
    types = read("frontend/types/chat.ts")
    request = section(
        types,
        "export interface EngineeringAIDraftRequest",
        "export interface EngineeringAIDraftResponse",
    )

    assert "conversation_id: string;" in request
    assert "relative_path: string;" in request
    assert "instruction: string;" in request

    for forbidden in (
        "workspace_id",
        "repository_root",
        "operation",
        "provider",
        "model",
        "approval_id",
        "proposal_digest",
        "apply",
        "tool",
        "shell",
    ):
        assert forbidden not in request


def test_d110_frontend_api_helper_is_local_and_non_authoritative() -> None:
    client = read("frontend/lib/api-client.ts")

    helper = section(
        client,
        "export function createEngineeringAIDraft",
        "export function createEngineeringProposal",
    )

    assert '"/engineering/ai-drafts"' in helper
    assert 'method: "POST"' in helper
    assert '"X-OAI-Local-Request": "1"' in helper
    assert "body: payload" in helper
    assert "configuredChatTimeoutMs()" in helper
    assert "response.conversation_id !== payload.conversation_id" in helper
    assert "response.relative_path !== payload.relative_path" in helper

    for forbidden in (
        "approval_id",
        "proposal_digest",
        "repository_root",
        "provider:",
        "model:",
        "apply:",
    ):
        assert forbidden not in helper

    # Preserve D89's read-only tail.
    assert client.index("export function createEngineeringAIDraft") < client.index(
        "export function getAutomationDeliveries"
    )


def test_d110_manual_d109_workflow_remains_available() -> None:
    panel = read("frontend/components/chat/engineering-owner-panel.tsx")
    card = read("frontend/components/chat/engineering-proposal-card.tsx")

    assert "Create exact proposal" in panel
    assert 'onSubmit={createProposal}' in panel
    assert 'placeholder="Exact proposed text"' in panel
    assert 'option value="replace_text"' in panel
    assert 'option value="create_text"' in panel

    assert "approveEngineeringProposal" in card
    assert "denyEngineeringProposal" in card
    assert "applyEngineeringProposal" in card
    assert "Approve does not mutate. Apply is a separate owner action." in card


def test_d110_chat_plaintext_has_no_engineering_draft_or_decision_bridge() -> None:
    chat_api = read("backend/app/api/v1/chat.py")
    chat_ui = read("frontend/components/chat/chat.tsx")

    for forbidden in (
        "EngineeringAIDraftWorkflowService",
        "create_engineering_ai_draft",
        "/engineering/ai-drafts",
        "EngineeringOwnerWorkflowService",
        "approve_engineering_proposal",
        "deny_engineering_proposal",
        "apply_engineering_proposal",
        "/engineering/approvals/",
    ):
        assert forbidden not in chat_api

    assert "<EngineeringOwnerPanel" in chat_ui
    assert 'key={`${workspaceId}:${conversationId ?? "none"}`}' in chat_ui
    assert "approveEngineeringProposal" not in chat_ui
    assert "applyEngineeringProposal" not in chat_ui


def test_d110_no_new_durable_or_database_authority() -> None:
    contract = read("backend/app/contracts/engineering_ai_draft.py")
    service = read("backend/app/services/engineering_ai_draft.py")
    dependencies = read("backend/app/api/dependencies.py")

    for source in (contract, service):
        for forbidden in (
            "sqlalchemy",
            "Session(",
            "alembic",
            "migration",
            "Base.metadata",
        ):
            assert forbidden not in source

    # D110 workflow uses existing workspace-scoped conversation repository only;
    # there is no AI draft store dependency.
    assert "get_engineering_ai_draft_store" not in dependencies
    assert "EngineeringAIDraftStore" not in dependencies


def test_d110_route_set_is_exact_and_bounded() -> None:
    source = read("backend/tests/test_d110_engineering_ai_draft_api_security.py")
    assert '"/engineering/ai-drafts"' in source
    assert '"/engineering/read"' in source
    assert '"/engineering/proposals"' in source
    assert '"/engineering/approvals/{approval_id}/approve"' in source
    assert '"/engineering/approvals/{approval_id}/deny"' in source
    assert '"/engineering/approvals/{approval_id}/apply"' in source


def test_d110_contract_version_and_effective_size_limit_are_frozen() -> None:
    contract = read("backend/app/contracts/engineering_ai_draft.py")
    proposal_contract = read(
        "backend/app/contracts/engineering_change_proposal.py"
    )

    assert 'ENGINEERING_AI_DRAFT_CONTRACT_VERSION = "d110.v1"' in contract
    assert "validate_engineering_change_content(value)" in contract
    assert "engineering_ai_draft_too_large" in contract
    assert "ENGINEERING_TEXT_MAX_BYTES" in proposal_contract
