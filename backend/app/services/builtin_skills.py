"""D114 trusted built-in Skill metadata.

Built-in Skills are declarative metadata only. They do not contain service
references, callables, routes, adapters, providers, models, credentials, Tools,
Modules, connectors, approval evidence, or apply authority.
"""

from __future__ import annotations

from app.contracts.ai_discovery import AI_CAPABILITY_TEXT_GENERATION
from app.contracts.skill import SkillDescriptor
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.skill_catalog import SkillCatalog


ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID = (
    "engineering.investigation_change_plan"
)

ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL = SkillDescriptor(
    skill_id=ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
    version="1",
    display_name="Engineering Investigation & Change Plan",
    description=(
        "Describe the bounded read-only D113 Engineering investigation "
        "and non-authoritative change-plan capability."
    ),
    task_kind=AITaskKind.SOFTWARE_ENGINEERING,
    required_ai_capability_ids=(AI_CAPABILITY_TEXT_GENERATION,),
    input_kind="engineering_investigation_request",
    context_kind="bounded_repository_evidence",
    output_kind="engineering_investigation_result",
)

BUILTIN_SKILL_DESCRIPTORS = (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
)


def build_builtin_skill_catalog() -> SkillCatalog:
    """Return the deterministic trusted built-in metadata catalog."""
    return SkillCatalog(BUILTIN_SKILL_DESCRIPTORS)


__all__ = [
    "BUILTIN_SKILL_DESCRIPTORS",
    "ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL",
    "ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID",
    "build_builtin_skill_catalog",
]