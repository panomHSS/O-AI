"""D114 Skills Foundation security acceptance.

D114 is declarative metadata only. These tests guard against accidental authority
migration into Skill contracts or the read-only catalog.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.contracts.skill import SkillDescriptor
from app.services.builtin_skills import (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    build_builtin_skill_catalog,
)
from app.services.skill_catalog import SkillCatalog


_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_D114_PRODUCTION_FILES = (
    _BACKEND_ROOT / "app" / "contracts" / "skill.py",
    _BACKEND_ROOT / "app" / "services" / "skill_catalog.py",
    _BACKEND_ROOT / "app" / "services" / "builtin_skills.py",
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "socket",
    "sqlite3",
    "sqlalchemy",
    "requests",
    "httpx",
    "importlib",
    "app.adapters",
    "app.connectors",
    "app.providers",
    "app.services.ai_runtime",
    "app.services.execution_guard",
    "app.services.execution_planner",
    "app.services.module_runtime",
    "app.services.tool_runtime",
    "app.services.credential_access_broker",
    "app.services.engineering_apply_execution",
    "app.services.engineering_change_proposal",
    "app.services.engineering_investigation",
    "app.services.engineering_investigation_workflow",
)

_FORBIDDEN_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def test_d114_production_imports_do_not_gain_execution_authority() -> None:
    for path in _D114_PRODUCTION_FILES:
        tree = _parse(path)

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    imports.append(node.module)

        for imported in imports:
            assert not imported.startswith(_FORBIDDEN_IMPORT_PREFIXES), (
                f"{path.name} imports forbidden authority surface: "
                f"{imported}"
            )


def test_d114_production_has_no_dynamic_execution_calls() -> None:
    for path in _D114_PRODUCTION_FILES:
        tree = _parse(path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):
                assert node.func.id not in _FORBIDDEN_CALL_NAMES, (
                    f"{path.name} calls forbidden function: "
                    f"{node.func.id}"
                )


def test_skill_descriptor_has_metadata_only_fields() -> None:
    field_names = {
        field.name
        for field in fields(SkillDescriptor)
    }

    assert field_names == {
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


def test_skill_catalog_has_no_execution_or_mutation_surface() -> None:
    catalog = build_builtin_skill_catalog()

    for forbidden_name in (
        "execute",
        "invoke",
        "run",
        "register",
        "unregister",
        "install",
        "enable",
        "disable",
        "load",
        "save",
        "delete",
    ):
        assert not hasattr(catalog, forbidden_name)


def test_builtin_skill_is_metadata_not_service_or_callable() -> None:
    descriptor = ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL

    assert isinstance(descriptor, SkillDescriptor)
    assert not callable(descriptor)

    for forbidden_name in (
        "service",
        "handler",
        "callable",
        "route",
        "adapter",
        "provider",
        "model",
        "credential",
        "approval",
        "apply",
    ):
        assert not hasattr(descriptor, forbidden_name)


def test_catalog_unknown_resolution_grants_nothing() -> None:
    catalog = build_builtin_skill_catalog()

    assert isinstance(catalog, SkillCatalog)
    assert catalog.resolve("unknown.skill") is None


def test_d114_source_does_not_define_skill_as_execution_target() -> None:
    for path in _D114_PRODUCTION_FILES:
        source = path.read_text(encoding="utf-8")

        assert 'target_kind="skill"' not in source
        assert "target_kind='skill'" not in source
        assert '"skill.execute"' not in source
        assert "'skill.execute'" not in source


def test_d114_source_does_not_define_dynamic_plugin_or_manifest_loading() -> None:
    forbidden_fragments = (
        "entry_points(",
        "import_module(",
        "spec_from_file_location(",
        "load_module(",
        "skill_manifest",
        "skills.json",
        "skills.yaml",
        "skills.yml",
    )

    for path in _D114_PRODUCTION_FILES:
        source = path.read_text(encoding="utf-8").lower()

        for fragment in forbidden_fragments:
            assert fragment.lower() not in source


def test_builtin_catalog_contains_exactly_one_descriptor() -> None:
    catalog = build_builtin_skill_catalog()

    assert len(catalog.list()) == 1
    assert (
        catalog.list()[0].skill_id
        == "engineering.investigation_change_plan"
    )