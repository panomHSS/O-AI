"""D118 owner-facing read-only Skill Catalog API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts.skill import SkillDescriptor


class SkillDescriptorResponse(BaseModel):
    """Bounded public projection of one trusted D114 Skill descriptor."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    version: str
    display_name: str
    description: str
    task_kind: Literal["general_chat", "software_engineering"]
    required_ai_capability_ids: list[str]
    input_kind: str
    context_kind: str
    output_kind: str

    @classmethod
    def from_descriptor(
        cls,
        descriptor: SkillDescriptor,
    ) -> "SkillDescriptorResponse":
        return cls(
            skill_id=descriptor.skill_id,
            version=descriptor.version,
            display_name=descriptor.display_name,
            description=descriptor.description,
            task_kind=descriptor.task_kind.value,
            required_ai_capability_ids=list(
                descriptor.required_ai_capability_ids
            ),
            input_kind=descriptor.input_kind,
            context_kind=descriptor.context_kind,
            output_kind=descriptor.output_kind,
        )


class SkillCatalogResponse(BaseModel):
    """Deterministic read-only public Skill catalog projection."""

    model_config = ConfigDict(extra="forbid")

    skills: list[SkillDescriptorResponse]

    @classmethod
    def from_descriptors(
        cls,
        descriptors: tuple[SkillDescriptor, ...],
    ) -> "SkillCatalogResponse":
        return cls(
            skills=[
                SkillDescriptorResponse.from_descriptor(descriptor)
                for descriptor in descriptors
            ]
        )


__all__ = [
    "SkillCatalogResponse",
    "SkillDescriptorResponse",
]
