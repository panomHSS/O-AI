"""D117 fixed Skill frontend security acceptance."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"
CHAT = ROOT / "frontend" / "components" / "chat" / "chat.tsx"
API_CLIENT = ROOT / "frontend" / "lib" / "api-client.ts"
EXECUTION_PLANNER = ROOT / "backend" / "app" / "services" / "execution_planner.py"
EXECUTION_GUARD = ROOT / "backend" / "app" / "services" / "execution_guard.py"
SKILL_BRIDGE = ROOT / "backend" / "app" / "services" / "skill_invocation_bridge.py"

SKILL_ID = "engineering.investigation_change_plan"
SKILL_PATH = (
    "/engineering/skills/"
    "engineering.investigation_change_plan/invoke"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _handler(source: str) -> str:
    start = source.index("  async function invokeBoundedEngineeringSkill()")
    end = source.index("  async function requestAIDraft(", start)
    return source[start:end]


def test_d117_skill_identity_is_fixed_and_not_owner_selectable() -> None:
    source = _read(PANEL)
    handler = _handler(source)

    assert source.count(SKILL_PATH) == 1
    assert handler.count(SKILL_PATH) == 1
    assert "skill_id:" not in handler
    assert "skillId" not in handler
    assert "<select" not in handler
    assert "catalog" not in handler.lower()
    assert "registry" not in handler.lower()
    assert "dynamic" not in handler.lower()


def test_d117_request_keeps_workspace_and_conversation_bounded() -> None:
    source = _read(PANEL)
    handler = _handler(source)

    assert "workspaceApiRequest<EngineeringInvestigationResponse>" in handler
    assert "workspaceId," in handler
    assert '"X-OAI-Local-Request": "1"' in handler
    assert "conversation_id: conversationId" in handler
    assert "instruction: investigationInstruction.trim()" in handler
    assert "focus_paths: focusPaths" in handler

    assert "workspace_id:" not in handler
    assert "skill_id:" not in handler
    assert "provider_id" not in handler
    assert "model_id" not in handler
    assert "adapter_id" not in handler
    assert "credential" not in handler.lower()


def test_d117_invocation_requires_explicit_owner_action_only() -> None:
    source = _read(PANEL)
    handler = _handler(source)

    assert source.count("invokeBoundedEngineeringSkill") == 2
    assert "onClick={invokeBoundedEngineeringSkill}" in source
    assert 'type="button"' in source

    assert "skillInvocationPendingContextsRef.current.has(" in handler
    assert "skillInvocationPendingContextsRef.current.add(" in handler
    assert "skillInvocationPendingContextsRef.current.delete(" in handler
    assert "retry" not in handler.lower()
    assert "fallback" not in handler.lower()

    effect_sections = source.split("useEffect(")[1:]
    assert all("invokeBoundedEngineeringSkill" not in part.split(");", 1)[0]
               for part in effect_sections)


def test_d117_pending_and_result_state_are_context_bound() -> None:
    source = _read(PANEL)
    handler = _handler(source)

    assert "requestContextKey = currentInvestigationContextKey" in handler
    assert "result.workspace_id !== workspaceId" in handler
    assert "result.conversation_id !== conversationId" in handler
    assert "setInvestigationContextKey(requestContextKey)" in handler

    assert "isInvokingSkill ||" in source
    assert (
        "investigationContextKey === currentInvestigationContextKey"
        in source
    )
    assert (
        "skillInvocationError?.contextKey ==="
        in source
    )


def test_d117_skill_output_remains_non_authoritative() -> None:
    source = _read(PANEL)
    handler = _handler(source)

    assert (
        "Bounded Skill · engineering.investigation_change_plan · "
        "read-only · non-authoritative"
        in source
    )
    assert (
        "No proposal is created and no repository change is applied."
        in source
    )

    forbidden = (
        "createengineeringproposal",
        "/engineering/proposals",
        "/approve",
        "/deny",
        "/apply",
        "executionapproval",
        "tool",
        "module",
        "connector",
        "credential",
        "shell",
        "subprocess",
    )
    lowered = handler.lower()
    for fragment in forbidden:
        assert fragment not in lowered


def test_d117_does_not_add_provider_or_model_selection_to_engineering_panel() -> None:
    source = _read(PANEL).lower()

    assert 'name="provider"' not in source
    assert 'name="model"' not in source
    assert "provider_id:" not in source
    assert "model_id:" not in source
    assert "select provider" not in source
    assert "select model" not in source


def test_d117_keeps_existing_transport_workspace_authority() -> None:
    api_client = _read(API_CLIENT)

    assert 'headers.set("X-OAI-Workspace", workspaceId)' in api_client
    assert "parseWorkspaceId(workspaceId)" in api_client
    assert "Workspace selection required." in api_client


def test_d117_does_not_create_a_skill_execution_target_kind() -> None:
    planner = _read(EXECUTION_PLANNER).lower()
    guard = _read(EXECUTION_GUARD).lower()
    bridge = _read(SKILL_BRIDGE)

    assert '"skill"' not in planner
    assert "'skill'" not in planner
    assert '"skill"' not in guard
    assert "'skill'" not in guard

    assert "EngineeringInvestigationWorkflowService" in bridge
    assert "ExecutionTargetKind" not in bridge


def test_d117_does_not_rewire_chat_to_auto_invoke_skill() -> None:
    chat = _read(CHAT)

    assert SKILL_PATH not in chat
    assert "invokeBoundedEngineeringSkill" not in chat
