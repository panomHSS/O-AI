"""D114 Batch 01 contract and authority-boundary tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from app.contracts.skill import (
    SKILL_CAPABILITY_ID_MAX_CHARS,
    SKILL_DESCRIPTION_MAX_CHARS,
    SKILL_DESCRIPTOR_INVALID,
    SKILL_DISPLAY_NAME_MAX_CHARS,
    SKILL_ID_MAX_CHARS,
    SKILL_KIND_MAX_CHARS,
    SKILL_MAX_REQUIRED_AI_CAPABILITIES,
    SKILL_VERSION_MAX_CHARS,
    SkillDescriptor,
)
from app.contracts.task_aware_ai_routing import AITaskKind


def _descriptor(**overrides: object) -> SkillDescriptor:
    values: dict[str, object] = {
        "skill_id": "engineering.investigation_change_plan",
        "version": "1",
        "display_name": "Engineering Investigation & Change Plan",
        "description": (
            "Describe the bounded D113 Engineering investigation capability."
        ),
        "task_kind": AITaskKind.SOFTWARE_ENGINEERING,
        "required_ai_capability_ids": ("text_generation",),
        "input_kind": "engineering_investigation_request",
        "context_kind": "bounded_repository_evidence",
        "output_kind": "engineering_investigation_result",
    }
    values.update(overrides)
    return SkillDescriptor(**values)  # type: ignore[arg-type]


def _assert_invalid(**overrides: object) -> None:
    with pytest.raises(ValueError) as exc:
        _descriptor(**overrides)
    assert str(exc.value) == SKILL_DESCRIPTOR_INVALID


def test_descriptor_accepts_provider_neutral_d113_shape() -> None:
    descriptor = _descriptor()

    assert descriptor.skill_id == "engineering.investigation_change_plan"
    assert descriptor.version == "1"
    assert descriptor.task_kind is AITaskKind.SOFTWARE_ENGINEERING
    assert descriptor.required_ai_capability_ids == ("text_generation",)
    assert descriptor.input_kind == "engineering_investigation_request"
    assert descriptor.context_kind == "bounded_repository_evidence"
    assert descriptor.output_kind == "engineering_investigation_result"


def test_descriptor_is_frozen_and_slots_based() -> None:
    descriptor = _descriptor()

    with pytest.raises(FrozenInstanceError):
        descriptor.display_name = "Changed"  # type: ignore[misc]

    assert not hasattr(descriptor, "__dict__")


def test_descriptor_has_exact_declarative_field_surface() -> None:
    assert tuple(field.name for field in fields(SkillDescriptor)) == (
        "skill_id",
        "version",
        "display_name",
        "description",
        "task_kind",
        "required_ai_capability_ids",
        "input_kind",
        "context_kind",
        "output_kind",
    )


def test_descriptor_exposes_no_execution_or_registration_surface() -> None:
    descriptor = _descriptor()

    for forbidden_name in (
        "execute",
        "invoke",
        "run",
        "register",
        "unregister",
        "handler",
        "callable",
    ):
        assert not hasattr(descriptor, forbidden_name)


def test_descriptor_exposes_no_provider_model_or_runtime_authority_fields() -> None:
    field_names = {field.name for field in fields(SkillDescriptor)}

    forbidden = {
        "provider_id",
        "adapter_id",
        "model_id",
        "endpoint",
        "api_key",
        "credential_reference",
        "tool_adapter_id",
        "module_adapter_id",
        "connector_id",
        "repository_root",
        "filesystem_path",
        "retry_policy",
        "fallback_provider",
        "approval",
        "apply_authority",
    }

    assert field_names.isdisjoint(forbidden)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("skill_id", ""),
        ("skill_id", " engineering.skill"),
        ("skill_id", "Engineering.Skill"),
        ("skill_id", "engineering skill"),
        ("version", ""),
        ("version", " 1"),
        ("version", "1 beta"),
        ("display_name", ""),
        ("display_name", " Name"),
        ("description", ""),
        ("description", "Description "),
        ("input_kind", ""),
        ("input_kind", "InputKind"),
        ("context_kind", "context kind"),
        ("output_kind", " output_kind"),
    ),
)
def test_descriptor_rejects_malformed_text_and_identifiers(
    field_name: str,
    value: object,
) -> None:
    _assert_invalid(**{field_name: value})


def test_descriptor_rejects_non_enum_task_kind() -> None:
    _assert_invalid(task_kind="software_engineering")


def test_descriptor_requires_immutable_capability_tuple() -> None:
    _assert_invalid(required_ai_capability_ids=["text_generation"])


def test_descriptor_rejects_duplicate_capability_ids() -> None:
    _assert_invalid(
        required_ai_capability_ids=(
            "text_generation",
            "text_generation",
        )
    )


@pytest.mark.parametrize(
    "capability_ids",
    (
        ("TextGeneration",),
        (" text_generation",),
        ("text generation",),
    ),
)
def test_descriptor_rejects_malformed_capability_ids(
    capability_ids: tuple[str, ...],
) -> None:
    _assert_invalid(required_ai_capability_ids=capability_ids)


def test_descriptor_allows_no_ai_capability_requirement() -> None:
    descriptor = _descriptor(required_ai_capability_ids=())

    assert descriptor.required_ai_capability_ids == ()


def test_descriptor_rejects_too_many_capability_requirements() -> None:
    capability_ids = tuple(
        f"capability_{index}"
        for index in range(SKILL_MAX_REQUIRED_AI_CAPABILITIES + 1)
    )

    _assert_invalid(required_ai_capability_ids=capability_ids)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("skill_id", "a" * (SKILL_ID_MAX_CHARS + 1)),
        ("version", "1" * (SKILL_VERSION_MAX_CHARS + 1)),
        (
            "display_name",
            "n" * (SKILL_DISPLAY_NAME_MAX_CHARS + 1),
        ),
        (
            "description",
            "d" * (SKILL_DESCRIPTION_MAX_CHARS + 1),
        ),
        ("input_kind", "i" * (SKILL_KIND_MAX_CHARS + 1)),
        ("context_kind", "c" * (SKILL_KIND_MAX_CHARS + 1)),
        ("output_kind", "o" * (SKILL_KIND_MAX_CHARS + 1)),
    ),
)
def test_descriptor_rejects_overlong_fields(
    field_name: str,
    value: object,
) -> None:
    _assert_invalid(**{field_name: value})


def test_descriptor_rejects_overlong_capability_id() -> None:
    _assert_invalid(
        required_ai_capability_ids=(
            "a" * (SKILL_CAPABILITY_ID_MAX_CHARS + 1),
        )
    )