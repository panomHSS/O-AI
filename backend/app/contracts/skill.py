"""D114 immutable declarative Skill Descriptor contract.

A Skill Descriptor is trusted server-owned metadata only. It grants no execution,
provider, model, context, Tool, Module, connector, credential, approval, proposal,
repository mutation, or apply authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.contracts.task_aware_ai_routing import AITaskKind


SKILL_DESCRIPTOR_INVALID = "skill_descriptor_invalid"

SKILL_ID_MAX_CHARS = 128
SKILL_VERSION_MAX_CHARS = 32
SKILL_DISPLAY_NAME_MAX_CHARS = 160
SKILL_DESCRIPTION_MAX_CHARS = 1000
SKILL_KIND_MAX_CHARS = 128
SKILL_CAPABILITY_ID_MAX_CHARS = 128
SKILL_MAX_REQUIRED_AI_CAPABILITIES = 8

_MACHINE_ID_PATTERN = re.compile(
    r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$"
)
_VERSION_PATTERN = re.compile(
    r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"
)


def _invalid() -> ValueError:
    return ValueError(SKILL_DESCRIPTOR_INVALID)


def _validate_text(
    value: object,
    *,
    max_chars: int,
) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_chars
    ):
        raise _invalid()
    return value


def _validate_machine_id(
    value: object,
    *,
    max_chars: int,
) -> str:
    text = _validate_text(value, max_chars=max_chars)
    if _MACHINE_ID_PATTERN.fullmatch(text) is None:
        raise _invalid()
    return text


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    """Immutable provider-neutral metadata describing one bounded Skill shape."""

    skill_id: str
    version: str
    display_name: str
    description: str
    task_kind: AITaskKind
    required_ai_capability_ids: tuple[str, ...]
    input_kind: str
    context_kind: str
    output_kind: str

    def __post_init__(self) -> None:
        _validate_machine_id(
            self.skill_id,
            max_chars=SKILL_ID_MAX_CHARS,
        )

        version = _validate_text(
            self.version,
            max_chars=SKILL_VERSION_MAX_CHARS,
        )
        if _VERSION_PATTERN.fullmatch(version) is None:
            raise _invalid()

        _validate_text(
            self.display_name,
            max_chars=SKILL_DISPLAY_NAME_MAX_CHARS,
        )
        _validate_text(
            self.description,
            max_chars=SKILL_DESCRIPTION_MAX_CHARS,
        )

        if not isinstance(self.task_kind, AITaskKind):
            raise _invalid()

        if not isinstance(self.required_ai_capability_ids, tuple):
            raise _invalid()
        if (
            len(self.required_ai_capability_ids)
            > SKILL_MAX_REQUIRED_AI_CAPABILITIES
        ):
            raise _invalid()

        seen: set[str] = set()
        for capability_id in self.required_ai_capability_ids:
            normalized = _validate_machine_id(
                capability_id,
                max_chars=SKILL_CAPABILITY_ID_MAX_CHARS,
            )
            if normalized in seen:
                raise _invalid()
            seen.add(normalized)

        _validate_machine_id(
            self.input_kind,
            max_chars=SKILL_KIND_MAX_CHARS,
        )
        _validate_machine_id(
            self.context_kind,
            max_chars=SKILL_KIND_MAX_CHARS,
        )
        _validate_machine_id(
            self.output_kind,
            max_chars=SKILL_KIND_MAX_CHARS,
        )


__all__ = [
    "SKILL_CAPABILITY_ID_MAX_CHARS",
    "SKILL_DESCRIPTION_MAX_CHARS",
    "SKILL_DESCRIPTOR_INVALID",
    "SKILL_DISPLAY_NAME_MAX_CHARS",
    "SKILL_ID_MAX_CHARS",
    "SKILL_KIND_MAX_CHARS",
    "SKILL_MAX_REQUIRED_AI_CAPABILITIES",
    "SKILL_VERSION_MAX_CHARS",
    "SkillDescriptor",
]