from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig")


def test_d110_frontend_types_keep_draft_non_authoritative() -> None:
    source = read("types/chat.ts")
    start = source.index("export interface EngineeringAIDraftRequest")
    end = source.index("export interface EngineeringOwnerProposalRequest", start)
    section = source[start:end]

    assert "conversation_id: string;" in section
    assert "relative_path: string;" in section
    assert "instruction: string;" in section
    assert 'draft_operation: "create_text" | "replace_text";' in section
    assert 'source_state: "absent" | "present";' in section
    assert "draft_content: string;" in section
    assert "ai_adapter_id: string;" in section

    for forbidden in (
        "workspace_id",
        "repository_root",
        "approval_id",
        "proposal_digest",
        "apply:",
        "provider:",
        "model:",
    ):
        assert forbidden not in section


def test_d110_api_helper_is_local_bounded_and_before_d89_read_tail() -> None:
    source = read("lib/api-client.ts")
    start = source.index("export function createEngineeringAIDraft")
    end = source.index("export function createEngineeringProposal", start)
    section = source[start:end]

    assert '"/engineering/ai-drafts"' in section
    assert 'method: "POST"' in section
    assert '"X-OAI-Local-Request": "1"' in section
    assert "body: payload" in section
    assert "configuredChatTimeoutMs()" in section
    assert "response.conversation_id !== payload.conversation_id" in section
    assert "response.relative_path !== payload.relative_path" in section

    assert start < source.index("export function getAutomationDeliveries")

    for forbidden in (
        "approval_id",
        "proposal_digest",
        "repository_root",
        "provider:",
        "model:",
        "operation:",
        "apply:",
    ):
        assert forbidden not in section


def test_d110_panel_exposes_draft_edit_discard_and_separate_proposal_action() -> None:
    source = read("components/chat/engineering-owner-panel.tsx")

    assert "Draft with Local AI" in source
    assert "Local AI draft (non-authoritative)" in source
    assert "Discard Draft" in source
    assert "Create Proposal from Draft" in source
    assert "createEngineeringAIDraft" in source
    assert "createEngineeringProposal" in source
    assert "setAIDraftContent(event.target.value)" in source

    draft_start = source.index("async function createProposalFromDraft")
    draft_end = source.index("async function createProposal(", draft_start)
    transition = source[draft_start:draft_end]

    assert "operation: aiDraft.draft_operation" in transition
    assert "relative_path: aiDraft.relative_path" in transition
    assert "proposed_content: aiDraftContent" in transition

    for forbidden in (
        "source_sha256",
        "source_size_bytes",
        "approval_id",
        "proposal_digest",
        "repository_root",
        "applyEngineeringProposal",
        "approveEngineeringProposal",
        "denyEngineeringProposal",
    ):
        assert forbidden not in transition


def test_d110_browser_draft_has_no_storage_or_chat_authority() -> None:
    panel = read("components/chat/engineering-owner-panel.tsx")
    chat = read("components/chat/chat.tsx")

    assert "localStorage" not in panel
    assert "sessionStorage" not in panel
    assert "sendChatMessage" not in panel
    assert "approveEngineeringProposal" not in panel
    assert "applyEngineeringProposal" not in panel

    assert "<EngineeringOwnerPanel" in chat
    assert 'key={`${workspaceId}:${conversationId ?? "none"}`}' in chat


def test_d110_manual_d109_proposal_workflow_remains_available() -> None:
    panel = read("components/chat/engineering-owner-panel.tsx")

    assert "Create exact proposal" in panel
    assert 'onSubmit={createProposal}' in panel
    assert 'option value="replace_text"' in panel
    assert 'option value="create_text"' in panel
    assert 'placeholder="Exact proposed text"' in panel
