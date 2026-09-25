"""D119 read-only Skill catalog frontend security acceptance."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"
CLIENT = ROOT / "frontend" / "lib" / "api-client.ts"
TYPES = ROOT / "frontend" / "types" / "chat.ts"
CHAT = ROOT / "frontend" / "components" / "chat" / "chat.tsx"

ENGINEERING_API = ROOT / "backend" / "app" / "api" / "v1" / "engineering.py"
ENGINEERING_DEPS = ROOT / "backend" / "app" / "api" / "dependencies.py"
CATALOG_SCHEMA = ROOT / "backend" / "app" / "schemas" / "skill_catalog.py"
SKILL_BRIDGE = ROOT / "backend" / "app" / "services" / "skill_invocation_bridge.py"
EXECUTION_PLANNER = ROOT / "backend" / "app" / "services" / "execution_planner.py"
EXECUTION_GUARD = ROOT / "backend" / "app" / "services" / "execution_guard.py"

FIXED_SKILL_PATH = (
    "/engineering/skills/"
    "engineering.investigation_change_plan/invoke"
)

PUBLIC_FIELDS = {
    "skill_id",
    "version",
    "display_name",
    "description",
    "task_kind",
    "required_ai_capability_ids",
    "input_kind",
    "context_kind",
    "output_kind",
}

FORBIDDEN_CATALOG_AUTHORITY = (
    "provider_id",
    "adapter_id",
    "model_id",
    "credential",
    "handler",
    "callable",
    "execution_target",
    "invoke_url",
    "http_method",
    "workspace_id",
    "conversation_id",
    "proposal_digest",
    "approval_id",
    "plan_digest",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract(
    source: str,
    start_marker: str,
    end_marker: str,
) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def _catalog_section(source: str) -> str:
    heading = source.index("Skill catalog (read-only)")
    start = source.rfind("<section", 0, heading)
    end = source.index("</section>", heading) + len("</section>")
    return source[start:end]


def _interface_fields(source: str, name: str) -> set[str]:
    match = re.search(
        rf"export interface {re.escape(name)} \{{(?P<body>.*?)\n\}}",
        source,
        flags=re.DOTALL,
    )
    assert match is not None

    fields: set[str] = set()
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        fields.add(stripped.split(":", 1)[0].strip().rstrip("?"))
    return fields


def test_d119_security_catalog_types_expose_metadata_only() -> None:
    source = _read(TYPES)

    assert _interface_fields(source, "EngineeringSkillCatalogItem") == PUBLIC_FIELDS
    assert _interface_fields(source, "EngineeringSkillCatalogResponse") == {"skills"}

    catalog_types = _extract(
        source,
        "export interface EngineeringSkillCatalogItem {",
        "export interface EngineeringOwnerReview {",
    ).lower()

    for fragment in FORBIDDEN_CATALOG_AUTHORITY:
        assert fragment not in catalog_types


def test_d119_security_catalog_transport_has_no_workspace_or_invocation_authority() -> None:
    source = _read(CLIENT)
    helper = _extract(
        source,
        "export function getEngineeringSkillCatalog()",
        "export function readEngineeringRepository(",
    )

    assert "apiRequest<EngineeringSkillCatalogResponse>" in helper
    assert '"/engineering/skills"' in helper
    assert 'method: "GET"' in helper
    assert '"X-OAI-Local-Request": "1"' in helper

    forbidden = (
        "workspaceApiRequest",
        "workspaceId",
        "conversationId",
        "skillId",
        "body:",
        "/invoke",
        'method: "POST"',
        'method: "PUT"',
        'method: "PATCH"',
        'method: "DELETE"',
    )
    for fragment in forbidden:
        assert fragment not in helper


def test_d119_security_catalog_load_is_explicit_and_not_effect_driven() -> None:
    source = _read(PANEL)
    handler = _extract(
        source,
        "  async function loadEngineeringSkillCatalog()",
        "  async function requestInvestigation(",
    )

    assert source.count("loadEngineeringSkillCatalog") == 2
    assert "onClick={loadEngineeringSkillCatalog}" in source
    assert "if (isLoadingSkillCatalog)" in handler
    assert "setIsLoadingSkillCatalog(true)" in handler
    assert "setIsLoadingSkillCatalog(false)" in handler

    effects = source.split("useEffect(")[1:]
    assert all(
        "loadEngineeringSkillCatalog" not in part.split(");", 1)[0]
        for part in effects
    )

    assert ".then(loadEngineeringSkillCatalog" not in source
    assert "retry" not in handler.lower()
    assert "fallback" not in handler.lower()


def test_d119_security_catalog_section_has_no_picker_or_execution_action() -> None:
    source = _read(PANEL)
    section = _catalog_section(source)

    assert "skillCatalog.skills.map((skill)" in section
    assert ".sort(" not in section
    assert ".reverse(" not in section

    assert "<select" not in section
    assert 'type="radio"' not in section
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
    assert "setSelectedSkill" not in source
    assert "setActiveSkill" not in source

    assert "invokeBoundedEngineeringSkill" not in section
    assert FIXED_SKILL_PATH not in section
    assert "/invoke" not in section

    lowered = section.lower()
    for action_label in (
        ">invoke<",
        ">run<",
        ">execute<",
    ):
        assert action_label not in lowered


def test_d119_security_d117_fixed_skill_control_remains_independent() -> None:
    source = _read(PANEL)
    handler = _extract(
        source,
        "  async function invokeBoundedEngineeringSkill()",
        "  async function requestAIDraft(",
    )

    assert source.count(FIXED_SKILL_PATH) == 1
    assert handler.count(FIXED_SKILL_PATH) == 1
    assert "workspaceApiRequest<EngineeringInvestigationResponse>" in handler
    assert "conversation_id: conversationId" in handler
    assert "instruction: investigationInstruction.trim()" in handler
    assert "focus_paths: focusPaths" in handler

    assert "getEngineeringSkillCatalog" not in handler
    assert "skillCatalog" not in handler
    assert "selectedSkill" not in handler
    assert "activeSkill" not in handler
    assert "skill_id:" not in handler


def test_d119_security_adds_no_browser_persisted_skill_authority() -> None:
    source = _read(PANEL)

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "indexedDB" not in source
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source


def test_d119_security_adds_no_provider_model_or_runtime_selection() -> None:
    panel = _read(PANEL).lower()
    section = _catalog_section(_read(PANEL)).lower()

    assert 'name="provider"' not in panel
    assert 'name="model"' not in panel
    assert "select provider" not in panel
    assert "select model" not in panel

    for fragment in (
        "provider_id",
        "adapter_id",
        "model_id",
        "credential",
        "tool_id",
        "module_id",
        "connector_id",
        "invoke_url",
        "execution_target",
    ):
        assert fragment not in section


def test_d119_security_keeps_catalog_out_of_plaintext_chat_auto_flow() -> None:
    chat = _read(CHAT)

    assert "getEngineeringSkillCatalog" not in chat
    assert "/engineering/skills" not in chat
    assert "loadEngineeringSkillCatalog" not in chat


def test_d119_security_backend_catalog_and_invocation_boundaries_remain_present() -> None:
    api = _read(ENGINEERING_API)
    deps = _read(ENGINEERING_DEPS)
    schema = _read(CATALOG_SCHEMA)
    bridge = _read(SKILL_BRIDGE)

    assert '"/skills",' in api
    assert '"/skills/{skill_id}/invoke"' in api
    assert "SkillCatalogResponse.from_descriptors(catalog.list())" in api
    assert "Depends(require_local_engineering_owner_request_marker)" in api

    assert "def get_skill_catalog() -> SkillCatalog:" in deps
    assert "return build_builtin_skill_catalog()" in deps

    assert "class SkillDescriptorResponse" in schema
    assert "class SkillCatalogResponse" in schema

    assert "EngineeringInvestigationWorkflowService" in bridge
    assert "ExecutionTargetKind" not in bridge


def test_d119_security_does_not_create_skill_execution_target_kind() -> None:
    planner = _read(EXECUTION_PLANNER).lower()
    guard = _read(EXECUTION_GUARD).lower()

    assert '"skill"' not in planner
    assert "'skill'" not in planner
    assert '"skill"' not in guard
    assert "'skill'" not in guard
