"""D114 deterministic read-only Skill Catalog.

The catalog stores immutable trusted server-owned Skill descriptors only. Catalog
lookup grants no execution, provider, model, Tool, Module, connector, credential,
approval, proposal, repository mutation, or apply authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.skill import SkillDescriptor


SKILL_CATALOG_DUPLICATE_SKILL_ID = "skill_catalog_duplicate_skill_id"
SKILL_CATALOG_INVALID_DEFINITION = "skill_catalog_invalid_definition"


@dataclass(frozen=True, slots=True, init=False)
class SkillCatalog:
    """Immutable deterministic metadata catalog; never an execution registry."""

    _descriptors: tuple[SkillDescriptor, ...]

    def __init__(
        self,
        descriptors: tuple[SkillDescriptor, ...],
    ) -> None:
        if not isinstance(descriptors, tuple):
            raise ValueError(SKILL_CATALOG_INVALID_DEFINITION)

        seen: set[str] = set()
        validated: list[SkillDescriptor] = []

        for descriptor in descriptors:
            if not isinstance(descriptor, SkillDescriptor):
                raise ValueError(SKILL_CATALOG_INVALID_DEFINITION)
            if descriptor.skill_id in seen:
                raise ValueError(SKILL_CATALOG_DUPLICATE_SKILL_ID)

            seen.add(descriptor.skill_id)
            validated.append(descriptor)

        ordered = tuple(
            sorted(
                validated,
                key=lambda item: item.skill_id,
            )
        )
        object.__setattr__(self, "_descriptors", ordered)

    def list(self) -> tuple[SkillDescriptor, ...]:
        """Return deterministic immutable descriptor metadata."""
        return self._descriptors

    def resolve(self, skill_id: object) -> SkillDescriptor | None:
        """Resolve metadata only; unknown or malformed IDs grant nothing."""
        if (
            not isinstance(skill_id, str)
            or not skill_id
            or skill_id != skill_id.strip()
        ):
            return None

        for descriptor in self._descriptors:
            if descriptor.skill_id == skill_id:
                return descriptor
        return None


__all__ = [
    "SKILL_CATALOG_DUPLICATE_SKILL_ID",
    "SKILL_CATALOG_INVALID_DEFINITION",
    "SkillCatalog",
]