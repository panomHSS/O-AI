from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8-sig")


def test_d113_frontend_types_are_provider_neutral_and_non_authoritative() -> None:
    source = read("types/chat.ts")
    start = source.index("export interface EngineeringInvestigationRequest")
    end = source.index("export interface EngineeringOwnerReview", start)
    section = source[start:end]

    assert "conversation_id: string;" in section
    assert "instruction: string;" in section
    assert "focus_paths: string[];" in section
    assert "findings: EngineeringInvestigationFinding[];" in section
    assert "change_plan: EngineeringInvestigationChangePlanItem[];" in section
    assert "evidence_refs: string[];" in section

    for forbidden in (
        "provider:",
        "model:",
        "endpoint:",
        "api_key:",
        "credential:",
        "approval_id:",
        "proposal_digest:",
        "apply:",
        "ai_adapter_id:",
    ):
        assert forbidden not in section


def test_d113_api_helper_is_local_workspace_bound_and_separate_from_proposal() -> None:
    source = read("lib/api-client.ts")
    start = source.index("export function createEngineeringInvestigation")
    end = source.index("export function getActiveEngineeringWorkflow", start)
    section = source[start:end]

    assert '"/engineering/investigations"' in section
    assert 'method: "POST"' in section
    assert '"X-OAI-Local-Request": "1"' in section
    assert "body: payload" in section
    assert "configuredChatTimeoutMs()" in section
    assert "assertResponseWorkspace(workspaceId, response)" in section
    assert "response.conversation_id !== payload.conversation_id" in section

    for forbidden in (
        "createEngineeringProposal(",
        "approveEngineeringProposal(",
        "applyEngineeringProposal(",
        "provider:",
        "model:",
    ):
        assert forbidden not in section


def test_d113_panel_displays_read_only_investigation_without_proposal_transition() -> None:
    source = read("components/chat/engineering-owner-panel.tsx")

    assert "AI-assisted investigation & change plan" in source
    assert "Investigate with Local AI" in source
    assert "Engineering investigation (read-only)" in source
    assert "Non-authoritative Change Plan" in source
    assert "No proposal is created and no repository change is applied." in source
    assert "Focus paths considered" in source
    assert "createEngineeringInvestigation" in source

    start = source.index("async function requestInvestigation")
    end = source.index("async function requestAIDraft", start)
    section = source[start:end]

    assert "createEngineeringInvestigation" in section
    assert "focus_paths: focusPaths" in section

    for forbidden in (
        "createEngineeringProposal",
        "approveEngineeringProposal",
        "applyEngineeringProposal",
        "proposal_digest",
        "approval_id",
        "provider",
        "model",
    ):
        assert forbidden not in section


def test_d113_existing_d110_and_manual_d107_controls_remain_separate() -> None:
    source = read("components/chat/engineering-owner-panel.tsx")

    assert "Draft with Local AI" in source
    assert "Create Proposal from Draft" in source
    assert "Create exact proposal" in source
    assert 'onSubmit={requestAIDraft}' in source
    assert 'onSubmit={createProposal}' in source