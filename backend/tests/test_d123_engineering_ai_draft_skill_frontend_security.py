"""D123 fixed Engineering AI Draft Skill frontend security acceptance."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"
CLIENT = ROOT / "frontend" / "lib" / "api-client.ts"
TYPES = ROOT / "frontend" / "types" / "chat.ts"
CHAT = ROOT / "frontend" / "components" / "chat" / "chat.tsx"

ENGINEERING_API = ROOT / "backend" / "app" / "api" / "v1" / "engineering.py"
SKILL_BRIDGE = ROOT / "backend" / "app" / "services" / "skill_invocation_bridge.py"
EXECUTION_PLANNER = ROOT / "backend" / "app" / "services" / "execution_planner.py"
EXECUTION_GUARD = ROOT / "backend" / "app" / "services" / "execution_guard.py"

AI_DRAFT_SKILL_PATH = "/engineering/skills/engineering.ai_draft/invoke"
INVESTIGATION_SKILL_PATH = (
    "/engineering/skills/"
    "engineering.investigation_change_plan/invoke"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def _d123_handler(source: str) -> str:
    return _extract(
        source,
        "  async function invokeAIDraftEngineeringSkill()",
        "  function discardAIDraft()",
    )


def _direct_d110_handler(source: str) -> str:
    return _extract(
        source,
        "  async function requestAIDraft(",
        "  async function invokeAIDraftEngineeringSkill()",
    )


def _d117_handler(source: str) -> str:
    return _extract(
        source,
        "  async function invokeBoundedEngineeringSkill()",
        "  async function requestAIDraft(",
    )


def _catalog_section(source: str) -> str:
    heading = source.index("Skill catalog (read-only)")
    start = source.rfind("<section", 0, heading)
    end = source.index("</section>", heading) + len("</section>")
    return source[start:end]


def test_d123_security_skill_identity_and_route_are_exact_and_fixed() -> None:
    source = _read(PANEL)
    handler = _d123_handler(source)

    assert source.count(AI_DRAFT_SKILL_PATH) == 1
    assert handler.count(AI_DRAFT_SKILL_PATH) == 1
    assert f'"{AI_DRAFT_SKILL_PATH}"' in handler

    assert "skill_id:" not in handler
    assert "skillId" not in handler
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
    assert "setSelectedSkill" not in source
    assert "setActiveSkill" not in source
    assert "skill.skill_id" not in handler
    assert "skillCatalog" not in handler


def test_d123_security_request_keeps_workspace_conversation_and_target_bounded() -> None:
    handler = _d123_handler(_read(PANEL))

    assert "workspaceApiRequest<EngineeringAIDraftResponse>" in handler
    assert "workspaceId," in handler
    assert '"X-OAI-Local-Request": "1"' in handler
    assert 'method: "POST"' in handler

    assert "const requestedPath = draftPath.trim();" in handler
    assert "const requestedInstruction = draftInstruction.trim();" in handler
    assert "conversation_id: conversationId" in handler
    assert "relative_path: requestedPath" in handler
    assert "instruction: requestedInstruction" in handler

    for forbidden in (
        "workspace_id:",
        "repository_root",
        "provider_id",
        "adapter_id",
        "model_id",
        "tool_id",
        "module_id",
        "connector_id",
        "credential",
        "approval_id",
        "proposal_digest",
        "operation:",
    ):
        assert forbidden not in handler.lower()


def test_d123_security_invocation_is_explicit_duplicate_guarded_and_not_effect_driven() -> None:
    source = _read(PANEL)
    handler = _d123_handler(source)

    assert source.count("invokeAIDraftEngineeringSkill") == 2
    assert "onClick={invokeAIDraftEngineeringSkill}" in source
    assert '"Draft via Engineering Skill"' in source

    assert "aiDraftSkillPendingContextsRef.current.has(" in handler
    assert "aiDraftSkillPendingContextsRef.current.add(" in handler
    assert "aiDraftSkillPendingContextsRef.current.delete(" in handler

    assert "retry" not in handler.lower()
    assert "fallback" not in handler.lower()
    assert ".map(invokeAIDraftEngineeringSkill" not in source
    assert ".then(invokeAIDraftEngineeringSkill" not in source

    effect_sections = source.split("useEffect(")[1:]
    assert all(
        "invokeAIDraftEngineeringSkill" not in part.split(");", 1)[0]
        for part in effect_sections
    )


def test_d123_security_response_must_match_conversation_and_target_before_adoption() -> None:
    handler = _d123_handler(_read(PANEL))

    conversation_check = handler.index("result.conversation_id !== conversationId")
    path_check = handler.index("result.relative_path !== requestedPath")
    adopt_draft = handler.index("setAIDraft(result);")
    adopt_content = handler.index("setAIDraftContent(result.draft_content);")

    assert conversation_check < adopt_draft
    assert path_check < adopt_draft
    assert conversation_check < adopt_content
    assert path_check < adopt_content

    assert '"HTTP",' in handler
    assert "409," in handler


def test_d123_security_output_reuses_non_authoritative_d110_draft_only() -> None:
    source = _read(PANEL)
    handler = _d123_handler(source).lower()

    assert "setaidraft(result);" in handler
    assert "setaidraftcontent(result.draft_content);" in handler
    assert "local ai draft (non-authoritative)" in source.lower()
    assert "discard draft" in source.lower()
    assert "create proposal from draft" in source.lower()

    for forbidden in (
        "createengineeringproposal",
        "/engineering/proposals",
        "/approve",
        "/deny",
        "/apply",
        "applyengineeringproposal",
        "approveengineeringproposal",
        "denyengineeringproposal",
        "executionapproval",
        "tool",
        "module",
        "connector",
        "credential",
        "shell",
        "subprocess",
        "git push",
        "git commit",
    ):
        assert forbidden not in handler


def test_d123_security_direct_d110_control_remains_distinct() -> None:
    panel = _read(PANEL)
    direct = _direct_d110_handler(panel)
    client = _read(CLIENT)

    assert "createEngineeringAIDraft(workspaceId" in direct
    assert AI_DRAFT_SKILL_PATH not in direct
    assert "Draft with Local AI" in panel
    assert "Draft via Engineering Skill" in panel

    helper = _extract(
        client,
        "export function createEngineeringAIDraft(",
        "export function createEngineeringProposal(",
    )
    assert '"/engineering/ai-drafts"' in helper
    assert AI_DRAFT_SKILL_PATH not in helper
    assert "response.conversation_id !== payload.conversation_id" in helper
    assert "response.relative_path !== payload.relative_path" in helper


def test_d123_security_d117_fixed_investigation_control_remains_independent() -> None:
    source = _read(PANEL)
    handler = _d117_handler(source)

    assert source.count(INVESTIGATION_SKILL_PATH) == 1
    assert handler.count(INVESTIGATION_SKILL_PATH) == 1
    assert "workspaceApiRequest<EngineeringInvestigationResponse>" in handler
    assert AI_DRAFT_SKILL_PATH not in handler
    assert "invokeAIDraftEngineeringSkill" not in handler
    assert "skillCatalog" not in handler
    assert "skill_id:" not in handler


def test_d123_security_d119_catalog_remains_metadata_only_and_non_invoking() -> None:
    source = _read(PANEL)
    section = _catalog_section(source)

    assert "skillCatalog.skills.map((skill)" in section
    assert "Metadata only" in section
    assert "Trusted server metadata only." in section
    assert "Visibility does not grant execution authority." in section

    assert AI_DRAFT_SKILL_PATH not in section
    assert INVESTIGATION_SKILL_PATH not in section
    assert "invokeAIDraftEngineeringSkill" not in section
    assert "invokeBoundedEngineeringSkill" not in section

    assert "<select" not in section
    assert 'type="radio"' not in section
    for label in (">Invoke<", ">Run<", ">Execute<", ">Select<"):
        assert label.lower() not in section.lower()


def test_d123_security_adds_no_browser_persisted_skill_authority() -> None:
    source = _read(PANEL)

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "indexedDB" not in source
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source


def test_d123_security_chat_does_not_auto_invoke_ai_draft_skill() -> None:
    chat = _read(CHAT)

    assert AI_DRAFT_SKILL_PATH not in chat
    assert "invokeAIDraftEngineeringSkill" not in chat
    assert "engineering.ai_draft" not in chat


def test_d123_security_shared_types_add_no_skill_execution_authority() -> None:
    types = _read(TYPES)
    draft_start = types.index("export interface EngineeringAIDraftRequest")
    draft_end = types.index("export interface EngineeringOwnerProposalRequest", draft_start)
    section = types[draft_start:draft_end].lower()

    for forbidden in (
        "skill_id",
        "workspace_id",
        "repository_root",
        "provider_id",
        "model_id",
        "tool_id",
        "module_id",
        "connector_id",
        "credential",
        "approval_id",
        "proposal_digest",
        "apply:",
    ):
        assert forbidden not in section


def test_d123_security_backend_skill_boundaries_remain_bounded() -> None:
    api = _read(ENGINEERING_API)
    bridge = _read(SKILL_BRIDGE)
    planner = _read(EXECUTION_PLANNER).lower()
    guard = _read(EXECUTION_GUARD).lower()

    assert '"/skills/engineering.ai_draft/invoke"' in api
    assert '"/skills/{skill_id}/invoke"' in api
    assert api.index('"/skills/engineering.ai_draft/invoke"') < api.index(
        '"/skills/{skill_id}/invoke"'
    )

    assert "ENGINEERING_AI_DRAFT_SKILL_ID" in bridge
    assert "EngineeringInvestigationWorkflowService" in bridge
    assert "ExecutionTargetKind" not in bridge

    assert '"skill"' not in planner
    assert "'skill'" not in planner
    assert '"skill"' not in guard
    assert "'skill'" not in guard