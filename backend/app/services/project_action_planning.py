"""Deterministic planning for owner-controlled Project actions."""

from __future__ import annotations

from app.schemas.project_action_planning import (
    ProjectActionPlan,
    ProjectActionPlanStep,
)
from app.schemas.project_actions import ProjectActionAnalysis


class ProjectActionPlanningService:
    """Build an ephemeral plan from an actionable Project analysis."""

    def plan(
        self,
        analysis: ProjectActionAnalysis,
    ) -> ProjectActionPlan:
        if (
            analysis.status != "suggestion_available"
            or not analysis.suggested_actions
        ):
            return ProjectActionPlan(
                status="no_plan_available",
                project_revision=analysis.project_revision,
                source_action=None,
                owner_approval_required=False,
                steps=[],
            )

        action = analysis.suggested_actions[0]

        return ProjectActionPlan(
            status="plan_available",
            project_revision=analysis.project_revision,
            source_action=action.description,
            owner_approval_required=True,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description=action.description,
                )
            ],
        )