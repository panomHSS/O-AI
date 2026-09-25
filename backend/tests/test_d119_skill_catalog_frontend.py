"""D119 owner-facing read-only Skill catalog frontend acceptance."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TYPES = ROOT / "frontend" / "types" / "chat.ts"
CLIENT = ROOT / "frontend" / "lib" / "api-client.ts"
PANEL = ROOT / "frontend" / "components" / "chat" / "engineering-owner-panel.tsx"

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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

        field = stripped.split(":", 1)[0].strip().rstrip("?")
        if field:
            fields.add(field)

    return fields


def _catalog_helper(source: str) -> str:
    start = source.index("export function getEngineeringSkillCatalog()")
    end = source.index("export function readEngineeringRepository(", start)
    return source[start:end]


def _catalog_handler(source: str) -> str:
    start = source.index("  async function loadEngineeringSkillCatalog()")
    end = source.index("  async function requestInvestigation(", start)
    return source[start:end]


def _catalog_section(source: str) -> str:
    heading = source.index("Skill catalog (read-only)")
    start = source.rfind("<section", 0, heading)
    end = source.index("</section>", heading) + len("</section>")
    return source[start:end]


def test_d119_frontend_types_match_exact_d118_public_projection() -> None:
    source = _read(TYPES)

    assert _interface_fields(source, "EngineeringSkillCatalogItem") == PUBLIC_FIELDS
    assert _interface_fields(source, "EngineeringSkillCatalogResponse") == {"skills"}


def test_d119_catalog_client_is_global_read_only_get_with_local_marker() -> None:
    helper = _catalog_helper(_read(CLIENT))

    assert "apiRequest<EngineeringSkillCatalogResponse>" in helper
    assert '"/engineering/skills"' in helper
    assert 'method: "GET"' in helper
    assert '"X-OAI-Local-Request": "1"' in helper

    assert "workspaceApiRequest" not in helper
    assert "body:" not in helper
    assert "workspaceId" not in helper
    assert "conversationId" not in helper
    assert "skillId" not in helper
    assert "/invoke" not in helper


def test_d119_catalog_load_is_explicit_and_duplicate_pending_is_guarded() -> None:
    source = _read(PANEL)
    handler = _catalog_handler(source)

    assert source.count("loadEngineeringSkillCatalog") == 2
    assert "onClick={loadEngineeringSkillCatalog}" in source
    assert "if (isLoadingSkillCatalog)" in handler
    assert "await getEngineeringSkillCatalog()" in handler
    assert "setIsLoadingSkillCatalog(true)" in handler
    assert "setIsLoadingSkillCatalog(false)" in handler

    assert "useEffect(() => loadEngineeringSkillCatalog" not in source
    assert ".then(loadEngineeringSkillCatalog" not in source


def test_d119_catalog_ui_is_metadata_only_and_preserves_server_order() -> None:
    section = _catalog_section(_read(PANEL))

    assert "Trusted server metadata only." in section
    assert "Visibility does not grant execution authority." in section
    assert "skillCatalog.skills.map((skill)" in section
    assert ".sort(" not in section
    assert ".reverse(" not in section

    for field in PUBLIC_FIELDS:
        assert f"skill.{field}" in section

    assert "selectedSkill" not in section
    assert "activeSkill" not in section
    assert "invokeBoundedEngineeringSkill" not in section
    assert "/invoke" not in section
    assert "workspaceId" not in section
    assert "conversationId" not in section


def test_d119_catalog_adds_no_picker_or_catalog_driven_invocation() -> None:
    source = _read(PANEL)
    section = _catalog_section(source)

    assert "<select" not in section
    assert "radio" not in section.lower()
    assert "selectedSkillId" not in source
    assert "activeSkillId" not in source
    assert "onClick={loadEngineeringSkillCatalog}" in section

    fixed_path = (
        "/engineering/skills/"
        "engineering.investigation_change_plan/invoke"
    )
    assert source.count(fixed_path) == 1
    assert "async function invokeBoundedEngineeringSkill()" in source
    assert "workspaceApiRequest<EngineeringInvestigationResponse>" in source
