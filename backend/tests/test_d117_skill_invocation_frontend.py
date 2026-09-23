"""D117 owner-facing fixed Skill frontend control acceptance."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"

SKILL_ID = "engineering.investigation_change_plan"
SKILL_PATH = (
    "/engineering/skills/"
    "engineering.investigation_change_plan/invoke"
)


def _source() -> str:
    return PANEL.read_text(encoding="utf-8")


def _handler(source: str) -> str:
    start = source.index("  async function invokeBoundedEngineeringSkill()")
    end = source.index(
        "  async function requestAIDraft(",
        start,
    )
    return source[start:end]


def test_d117_uses_exact_fixed_skill_and_existing_workspace_transport() -> None:
    source = _source()
    handler = _handler(source)

    assert source.count(SKILL_PATH) == 1
    assert f'"{SKILL_PATH}"' in handler
    assert "workspaceApiRequest<EngineeringInvestigationResponse>" in handler
    assert '"X-OAI-Local-Request": "1"' in handler
    assert "workspaceId," in handler
    assert "conversation_id: conversationId" in handler
    assert "instruction: investigationInstruction.trim()" in handler
    assert "focus_paths: focusPaths" in handler

    assert "skill_id:" not in handler
    assert "workspace_id:" not in handler
    assert "provider_id" not in handler
    assert "model_id" not in handler
    assert "adapter_id" not in handler
    assert "credential" not in handler


def test_d117_invocation_is_explicit_and_duplicate_pending_is_guarded() -> None:
    source = _source()
    handler = _handler(source)

    assert source.count("invokeBoundedEngineeringSkill") == 2
    assert "onClick={invokeBoundedEngineeringSkill}" in source
    assert "type=\"button\"" in source

    assert "skillInvocationPendingContextsRef.current.has(" in handler
    assert "skillInvocationPendingContextsRef.current.add(" in handler
    assert "skillInvocationPendingContextsRef.current.delete(" in handler
    assert "isInvokingSkill ||" in source
    assert "Invoking bounded Skill…" in source

    assert "retry" not in handler.lower()
    assert "fallback" not in handler.lower()
    assert ".map(invokeBoundedEngineeringSkill" not in source
    assert "useEffect(() => invokeBoundedEngineeringSkill" not in source


def test_d117_skill_result_is_context_bound_and_non_authoritative() -> None:
    source = _source()
    handler = _handler(source)

    assert "result.workspace_id !== workspaceId" in handler
    assert "result.conversation_id !== conversationId" in handler
    assert 'setInvestigationSource("skill")' in handler
    assert "setInvestigationContextKey(requestContextKey)" in handler

    assert (
        "investigationContextKey === currentInvestigationContextKey"
        in source
    )
    assert (
        "Bounded Skill · engineering.investigation_change_plan · "
        "read-only · non-authoritative"
        in source
    )
    assert (
        "No proposal is created and no repository change is applied."
        in source
    )


def test_d117_skill_control_adds_no_proposal_apply_or_runtime_authority() -> None:
    handler = _handler(_source()).lower()

    forbidden = (
        "createengineeringproposal",
        "/engineering/proposals",
        "/approve",
        "/deny",
        "/apply",
        "tool",
        "module",
        "connector",
        "credential",
        "executiontarget",
        "shell",
        "process",
        "git ",
    )
    for fragment in forbidden:
        assert fragment not in handler


def test_d117_direct_d113_investigation_remains_separate() -> None:
    source = _source()

    assert "createEngineeringInvestigation(workspaceId" in source
    assert "requestInvestigation" in source
    assert "Investigate with Local AI" in source
    assert "Invoke Engineering Skill" in source
