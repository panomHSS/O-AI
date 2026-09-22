from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(
        encoding="utf-8-sig"
    ).replace("\r\n", "\n")


def test_d112_chat_waits_for_server_capability_before_mode_selection_or_send() -> None:
    source = read("components/chat/chat.tsx")

    assert 'const unavailable = capability?.status !== "ready";' in source
    assert "!generalChatCapabilities" in source
    assert (
        'selectedAIModeCapability?.status === "ready"'
        in source
    )
    assert "!selectedAIModeReady" in source
    assert "The selected AI mode is not available." in source

    send_button = source[source.index("<form className=\"flex gap-3\"") :]
    assert "!selectedAIModeReady" in send_button


def test_d112_chat_discloses_cloud_context_egress_only_for_cloud_resolution() -> None:
    source = read("components/chat/chat.tsx")

    assert (
        'selectedAIModeCapability?.provider_class === "cloud_ai"'
        in source
    )
    assert "selectedAIModeUsesCloud && selectedAIModeReady" in source
    assert (
        "Cloud AI may send eligible Chat context from this workspace to the"
        in source
    )
    assert "configured cloud provider" in source
    assert "O-AI routing and authority controls" in source


def test_d112_frontend_exposes_bounded_readiness_without_provider_authority() -> None:
    source = read("components/chat/chat.tsx")

    for marker in (
        "cloud_ai_disabled",
        "cloud_ai_credential_missing",
        "cloud_ai_model_missing",
        "workspace_cloud_egress_denied",
    ):
        assert marker in source

    ai_mode_section = source[
        source.index("const AI_MODE_OPTIONS") :
        source.index("<EngineeringOwnerPanel")
    ]
    for forbidden in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "api_key",
        "model_id",
        "base_url",
        "endpoint:",
        "adapter_id",
    ):
        assert forbidden not in ai_mode_section


def test_d112_engineering_ui_remains_local_only_and_independent_of_chat_mode() -> None:
    panel = read("components/chat/engineering-owner-panel.tsx")
    chat = read("components/chat/chat.tsx")

    assert "Draft with Local AI" in panel
    assert "Local AI draft (non-authoritative)" in panel
    assert "aiMode" not in panel

    assert "Engineering drafting remains" in chat
    assert "Local AI only" in chat
    assert "Chat AI mode does not change Engineering routing." in chat