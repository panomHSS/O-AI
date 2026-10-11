"""D120 second trusted built-in Skill metadata acceptance."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.builtin_skills import (
    BUILTIN_SKILL_DESCRIPTORS,
    ENGINEERING_AI_DRAFT_SKILL,
    ENGINEERING_AI_DRAFT_SKILL_ID,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    build_builtin_skill_catalog,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_d120_builtin_catalog_contains_exactly_two_trusted_skills() -> None:
    catalog = build_builtin_skill_catalog()

    assert BUILTIN_SKILL_DESCRIPTORS == (
        ENGINEERING_AI_DRAFT_SKILL,
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    )
    assert catalog.list() == BUILTIN_SKILL_DESCRIPTORS
    assert tuple(item.skill_id for item in catalog.list()) == (
        "engineering.ai_draft",
        "engineering.investigation_change_plan",
    )


def test_d120_engineering_ai_draft_descriptor_matches_frozen_mapping() -> None:
    descriptor = ENGINEERING_AI_DRAFT_SKILL

    assert descriptor.skill_id == "engineering.ai_draft"
    assert descriptor.version == "1"
    assert descriptor.display_name == "Engineering AI Draft"
    assert descriptor.description == (
        "Describe the bounded D110 non-authoritative AI-assisted Engineering "
        "drafting capability."
    )
    assert descriptor.task_kind is AITaskKind.SOFTWARE_ENGINEERING
    assert descriptor.required_ai_capability_ids == (
        AI_CAPABILITY_TEXT_GENERATION,
    )
    assert descriptor.input_kind == "engineering_ai_draft_request"
    assert descriptor.context_kind == "bounded_repository_observation"
    assert descriptor.output_kind == "engineering_ai_draft_result"


def test_d120_new_descriptor_is_metadata_only() -> None:
    assert ENGINEERING_AI_DRAFT_SKILL_ID == "engineering.ai_draft"
    assert isinstance(ENGINEERING_AI_DRAFT_SKILL, SkillDescriptor)
    assert not callable(ENGINEERING_AI_DRAFT_SKILL)

    assert {field.name for field in fields(SkillDescriptor)} == {
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


def test_d120_catalog_visibility_does_not_rewire_fixed_frontend_invocation() -> None:
    panel = (
        _REPO_ROOT
        / "frontend"
        / "components"
        / "chat"
        / "engineering-owner-panel.tsx"
    ).read_text(encoding="utf-8")

    assert (
        '"/engineering/skills/engineering.investigation_change_plan/invoke"'
        in panel
    )
    assert (
        '"/engineering/skills/engineering.ai_draft/invoke"'
        in panel
    )
    assert panel.count(
        "/engineering/skills/engineering.ai_draft/invoke"
    ) == 1
    assert "selectedSkillId" not in panel
    assert "activeSkillId" not in panel


def test_d120_catalog_frontend_remains_generic_metadata_rendering() -> None:
    panel = (
        _REPO_ROOT
        / "frontend"
        / "components"
        / "chat"
        / "engineering-owner-panel.tsx"
    ).read_text(encoding="utf-8")

    assert "Skill catalog (read-only)" in panel
    assert "skillCatalog.skills.map((skill)" in panel
    assert "Metadata only" in panel
