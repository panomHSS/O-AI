"""D114 Batch 02 read-only catalog and built-in Skill tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.builtin_skills import (
    BUILTIN_SKILL_DESCRIPTORS,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    build_builtin_skill_catalog,
)
from app.services.skill_catalog import (
    SKILL_CATALOG_DUPLICATE_SKILL_ID,
    SKILL_CATALOG_INVALID_DEFINITION,
    SkillCatalog,
)


def _descriptor(skill_id: str) -> SkillDescriptor:
    return SkillDescriptor(
        skill_id=skill_id,
        version="1",
        display_name=f"Skill {skill_id}",
        description="Deterministic declarative test metadata.",
        task_kind=AITaskKind.SOFTWARE_ENGINEERING,
        required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
        input_kind="test_input",
        context_kind="test_context",
        output_kind="test_output",
    )


def test_catalog_requires_immutable_tuple_definitions() -> None:
    with pytest.raises(ValueError) as exc:
        SkillCatalog([_descriptor("alpha.skill")])  # type: ignore[arg-type]

    assert str(exc.value) == SKILL_CATALOG_INVALID_DEFINITION


def test_catalog_rejects_non_descriptor_definitions() -> None:
    with pytest.raises(ValueError) as exc:
        SkillCatalog(("not-a-descriptor",))  # type: ignore[arg-type]

    assert str(exc.value) == SKILL_CATALOG_INVALID_DEFINITION


def test_catalog_rejects_duplicate_skill_ids() -> None:
    descriptor = _descriptor("alpha.skill")

    with pytest.raises(ValueError) as exc:
        SkillCatalog((descriptor, descriptor))

    assert str(exc.value) == SKILL_CATALOG_DUPLICATE_SKILL_ID


def test_catalog_list_order_is_deterministic_by_skill_id() -> None:
    catalog = SkillCatalog(
        (
            _descriptor("zeta.skill"),
            _descriptor("alpha.skill"),
            _descriptor("middle.skill"),
        )
    )

    assert tuple(
        descriptor.skill_id
        for descriptor in catalog.list()
    ) == (
        "alpha.skill",
        "middle.skill",
        "zeta.skill",
    )


def test_catalog_list_returns_immutable_tuple() -> None:
    catalog = SkillCatalog((_descriptor("alpha.skill"),))

    listed = catalog.list()

    assert isinstance(listed, tuple)
    assert listed == (_descriptor("alpha.skill"),)


def test_catalog_is_frozen() -> None:
    catalog = SkillCatalog((_descriptor("alpha.skill"),))

    with pytest.raises(FrozenInstanceError):
        catalog._descriptors = ()  # type: ignore[misc]


@pytest.mark.parametrize(
    "unknown",
    (
        "missing.skill",
        "",
        " missing.skill",
        None,
        123,
    ),
)
def test_unknown_or_malformed_resolution_returns_no_descriptor(
    unknown: object,
) -> None:
    catalog = SkillCatalog((_descriptor("alpha.skill"),))

    assert catalog.resolve(unknown) is None


def test_catalog_resolves_metadata_only() -> None:
    descriptor = _descriptor("alpha.skill")
    catalog = SkillCatalog((descriptor,))

    assert catalog.resolve("alpha.skill") is descriptor


def test_catalog_exposes_no_execution_or_mutation_registry_surface() -> None:
    catalog = SkillCatalog((_descriptor("alpha.skill"),))

    for forbidden_name in (
        "execute",
        "invoke",
        "run",
        "register",
        "unregister",
        "enable",
        "disable",
        "install",
        "load",
    ):
        assert not hasattr(catalog, forbidden_name)


def test_catalog_has_only_internal_descriptor_storage() -> None:
    assert tuple(field.name for field in fields(SkillCatalog)) == (
        "_descriptors",
    )


def test_builtin_catalog_contains_exactly_one_d113_descriptor() -> None:
    catalog = build_builtin_skill_catalog()

    assert BUILTIN_SKILL_DESCRIPTORS == (
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    )
    assert catalog.list() == BUILTIN_SKILL_DESCRIPTORS
    assert catalog.resolve(
        ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID
    ) is ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL


def test_builtin_d113_descriptor_matches_frozen_mapping() -> None:
    descriptor = ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL

    assert descriptor.skill_id == "engineering.investigation_change_plan"
    assert descriptor.version == "1"
    assert descriptor.display_name == (
        "Engineering Investigation & Change Plan"
    )
    assert descriptor.task_kind is AITaskKind.SOFTWARE_ENGINEERING
    assert descriptor.required_ai_capability_ids == (
        AI_CAPABILITY_TEXT_GENERATION,
    )
    assert descriptor.input_kind == "engineering_investigation_request"
    assert descriptor.context_kind == "bounded_repository_evidence"
    assert descriptor.output_kind == "engineering_investigation_result"


def test_builtin_descriptor_contains_no_execution_authority_fields() -> None:
    field_names = {
        field.name
        for field in fields(SkillDescriptor)
    }

    forbidden = {
        "provider_id",
        "adapter_id",
        "model_id",
        "endpoint",
        "credential_reference",
        "tool_adapter_id",
        "module_adapter_id",
        "connector_id",
        "handler",
        "callable",
        "route",
        "service",
        "approval",
        "apply_authority",
    }

    assert field_names.isdisjoint(forbidden)


def test_builtin_descriptor_is_not_callable() -> None:
    assert not callable(ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL)