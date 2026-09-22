"""D115 bounded Skill invocation bridge.

The bridge resolves one trusted built-in Skill identity, verifies its exact D114
descriptor shape, and delegates once to the existing owner-bound D113 workflow.

It is not an execution runtime, planner, authorization boundary, handler registry,
provider selector, Tool/Module dispatcher, proposal authority, or apply authority.
"""

from __future__ import annotations

from app.contracts.engineering_investigation import (
    EngineeringInvestigationRequest,
    EngineeringInvestigationResult,
)
from app.services.builtin_skills import (
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL,
    ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID,
)
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationWorkflowService,
)
from app.services.skill_catalog import SkillCatalog


SKILL_INVOCATION_REQUEST_INVALID = "skill_invocation_request_invalid"
SKILL_INVOCATION_SKILL_NOT_FOUND = "skill_invocation_skill_not_found"
SKILL_INVOCATION_SKILL_UNSUPPORTED = "skill_invocation_skill_unsupported"
SKILL_INVOCATION_DESCRIPTOR_MISMATCH = "skill_invocation_descriptor_mismatch"


class SkillInvocationError(RuntimeError):
    """Safe D115 bridge failure with one stable internal code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SkillInvocationBridge:
    """Resolve one frozen Skill identity and delegate one bounded workflow once."""

    def __init__(
        self,
        *,
        catalog: SkillCatalog,
        engineering_investigation_workflow: EngineeringInvestigationWorkflowService,
    ) -> None:
        if not isinstance(catalog, SkillCatalog):
            raise TypeError("catalog must be SkillCatalog.")
        if not isinstance(
            engineering_investigation_workflow,
            EngineeringInvestigationWorkflowService,
        ):
            raise TypeError(
                "engineering_investigation_workflow must be "
                "EngineeringInvestigationWorkflowService."
            )

        self._catalog = catalog
        self._engineering_investigation_workflow = (
            engineering_investigation_workflow
        )

    def invoke(
        self,
        *,
        skill_id: object,
        request: object,
    ) -> EngineeringInvestigationResult:
        """Delegate exactly one supported Skill invocation or fail closed."""
        if (
            type(skill_id) is not str
            or not skill_id
            or skill_id != skill_id.strip()
        ):
            raise SkillInvocationError(SKILL_INVOCATION_REQUEST_INVALID)

        descriptor = self._catalog.resolve(skill_id)
        if descriptor is None:
            raise SkillInvocationError(SKILL_INVOCATION_SKILL_NOT_FOUND)

        if skill_id != ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL_ID:
            raise SkillInvocationError(SKILL_INVOCATION_SKILL_UNSUPPORTED)

        if descriptor != ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL:
            raise SkillInvocationError(SKILL_INVOCATION_DESCRIPTOR_MISMATCH)

        if not isinstance(request, EngineeringInvestigationRequest):
            raise SkillInvocationError(SKILL_INVOCATION_REQUEST_INVALID)

        return self._engineering_investigation_workflow.investigate(request)


__all__ = [
    "SKILL_INVOCATION_DESCRIPTOR_MISMATCH",
    "SKILL_INVOCATION_REQUEST_INVALID",
    "SKILL_INVOCATION_SKILL_NOT_FOUND",
    "SKILL_INVOCATION_SKILL_UNSUPPORTED",
    "SkillInvocationBridge",
    "SkillInvocationError",
]