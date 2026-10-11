"D123 fixed Engineering AI Draft Skill frontend acceptance."

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"

AI_DRAFT_SKILL_PATH = "/engineering/skills/engineering.ai_draft/invoke"
INVESTIGATION_SKILL_PATH = (
    "/engineering/skills/"
    "engineering.investigation_change_plan/invoke"
)


def _source() -> str:
    return PANEL.read_text(encoding="utf-8")


def _d123_handler(source: str) -> str:
    start = source.index("  async function invokeAIDraftEngineeringSkill()")
    end = source.index("  function discardAIDraft()", start)
    return source[start:end]


def _direct_d110_handler(source: str) -> str:
    start = source.index("  async function requestAIDraft(")
    end = source.index("  async function invokeAIDraftEngineeringSkill()", start)
    return source[start:end]


def _catalog_section(source: str) -> str:
    heading = source.index("Skill catalog (read-only)")
    start = source.rfind("<section", 0, heading)
    end = source.index("</section>", heading) + len("</section>")
    return source[start:end]


def test_d123_uses_exact_fixed_skill_and_existing_workspace_transport() -> None:
    source = _source()
    handler = _d123_handler(source)

    assert source.count(AI_DRAFT_SKILL_PATH) == 1
    assert f'"{AI_DRAFT_SKILL_PATH}"' in handler
    assert "workspaceApiRequest<EngineeringAIDraftResponse>" in handler
    assert "workspaceId," in handler
    assert '"X-OAI-Local-Request": "1"' in handler
    assert 'method: "POST"' in handler
    assert "conversation_id: conversationId" in handler
    assert "relative_path: requestedPath" in handler
    assert "instruction: requestedInstruction" in handler

    for forbidden in (
        "workspace_id:",
        "skill_id:",
        "provider_id",
        "model_id",
        "adapter_id",
        "credential",
        "connector_id",
        "tool_id",
        "module_id",
        "approval_id",
        "proposal_digest",
    ):
        assert forbidden not in handler.lower()


def test_d123_invocation_is_explicit_and_duplicate_pending_is_guarded() -> None:
    source = _source()
    handler = _d123_handler(source)

    assert source.count("invokeAIDraftEngineeringSkill") == 2
    assert "onClick={invokeAIDraftEngineeringSkill}" in source
    assert "Draft via Engineering Skill" in source
    assert 'type="button"' in source

    assert "aiDraftSkillPendingContextsRef.current.has(" in handler
    assert "aiDraftSkillPendingContextsRef.current.add(" in handler
    assert "aiDraftSkillPendingContextsRef.current.delete(" in handler
    assert "isInvokingAIDraftSkill" in source

    assert "retry" not in handler.lower()
    assert "fallback" not in handler.lower()
    assert ".map(invokeAIDraftEngineeringSkill" not in source
    assert "useEffect(() => invokeAIDraftEngineeringSkill" not in source


def test_d123_response_is_bound_before_reusing_d110_draft_state() -> None:
    source = _source()
    handler = _d123_handler(source)

    assert "const requestedPath = draftPath.trim();" in handler
    assert "const requestedInstruction = draftInstruction.trim();" in handler
    assert "result.conversation_id !== conversationId" in handler
    assert "result.relative_path !== requestedPath" in handler
    assert "setAIDraft(result);" in handler
    assert "setAIDraftContent(result.draft_content);" in handler

    assert "Local AI draft (non-authoritative)" in source
    assert "setAIDraftContent(event.target.value)" in source
    assert "Discard Draft" in source
    assert "Create Proposal from Draft" in source


def test_d123_keeps_direct_d110_control_distinct() -> None:
    source = _source()
    direct = _direct_d110_handler(source)

    assert "createEngineeringAIDraft(workspaceId" in direct
    assert AI_DRAFT_SKILL_PATH not in direct
    assert "Draft with Local AI" in source
    assert "Draft via Engineering Skill" in source


def test_d123_keeps_d117_and_d119_independent() -> None:
    source = _source()
    catalog = _catalog_section(source)

    assert source.count(INVESTIGATION_SKILL_PATH) == 1
    assert "async function invokeBoundedEngineeringSkill()" in source
    assert "Invoke Engineering Skill" in source

    assert "skillCatalog.skills.map((skill)" in catalog
    assert AI_DRAFT_SKILL_PATH not in catalog
    assert INVESTIGATION_SKILL_PATH not in catalog
    assert "invokeAIDraftEngineeringSkill" not in catalog
    assert "invokeBoundedEngineeringSkill" not in catalog
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
