from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(
        encoding="utf-8-sig"
    ).replace("\r\n", "\n")


def test_d111_frontend_exposes_exact_three_logical_modes_only() -> None:
    source = read("types/chat.ts")
    assert (
        'export type AIMode = "auto" | "local_ai" | "cloud_ai";'
        in source
    )

    start = source.index("export interface AIBrainModeCapability")
    end = source.index("export interface ContextUsage", start)
    section = source[start:end]

    assert "mode: AIMode;" in section
    assert 'status: "ready" | "unavailable" | "blocked";' in section
    assert 'provider_class: "local_ai" | "cloud_ai" | null;' in section

    for forbidden in (
        "adapter_id",
        "model_id",
        "base_url",
        "api_key",
        "credential",
        "endpoint",
    ):
        assert forbidden not in section


def test_d111_capability_helper_is_workspace_bound_read_only() -> None:
    source = read("lib/api-client.ts")
    start = source.index("export function getAIBrainCapabilities")
    end = source.index("export function sendChatMessage", start)
    section = source[start:end]

    assert '"/chat/ai-capabilities"' in section
    assert 'method: "GET"' in section
    assert "workspaceApiRequest<AIBrainCapabilitiesResponse>" in section
    assert "assertResponseWorkspace(workspaceId, response)" in section

    for forbidden in (
        'method: "POST"',
        "body:",
        "provider",
        "model",
        "credential",
        "api_key",
        "base_url",
    ):
        assert forbidden not in section


def test_d111_send_chat_transmits_only_logical_ai_mode() -> None:
    source = read("lib/api-client.ts")
    start = source.index("export function sendChatMessage")
    end = source.index("export function approveExecutionApproval", start)
    section = source[start:end]

    assert "aiMode?: AIMode" in section
    assert "ai_mode: aiMode" in section

    for forbidden in (
        "provider_id",
        "adapter_id",
        "model_id",
        "base_url",
        "api_key",
        "credential",
        "fallback_target",
    ):
        assert forbidden not in section


def test_d111_chat_ui_has_mode_selector_and_server_capability_status() -> None:
    source = read("components/chat/chat.tsx")

    assert "Chat AI mode" in source
    assert '"Auto"' in source
    assert '"Local AI"' in source
    assert '"Cloud AI"' in source
    assert "getAIBrainCapabilities(workspaceId)" in source
    assert "setAIMode(event.target.value as AIMode)" in source
    assert "selectedAIModeCapability?.status" in source
    assert "aiMode," in source
    assert "Engineering drafting remains Local AI only" in source

    assert "oai.aiMode" not in source
    assert "sessionStorage" not in source


def test_d111_engineering_panel_remains_separate_local_ai_only_d110_ui() -> None:
    panel = read("components/chat/engineering-owner-panel.tsx")
    chat = read("components/chat/chat.tsx")

    assert "Draft with Local AI" in panel
    assert "Local AI draft (non-authoritative)" in panel
    assert "createEngineeringAIDraft" in panel
    assert "aiMode" not in panel

    assert "<EngineeringOwnerPanel" in chat
    assert "workspaceId={workspaceId}" in chat
    assert "conversationId={conversationId}" in chat
