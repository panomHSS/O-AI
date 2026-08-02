from app.schemas.project_actions import (
    ProjectActionAnalysis,
    SuggestedProjectAction,
)
from app.services.project_context import ProjectContext


class ProjectActionService:
    """Surface explicit Project next actions without executing them."""

    def analyze(
        self,
        project_context: ProjectContext,
    ) -> ProjectActionAnalysis:
        next_action = project_context.next_action

        if (
            project_context.status in {
                "PAUSED",
                "COMPLETED",
                "ARCHIVED",
            }
            or not next_action
        ):
            return ProjectActionAnalysis(
                status="no_explicit_action",
                project_revision=project_context.current_revision,
                owner_approval_required=False,
            )

        return ProjectActionAnalysis(
            status="suggestion_available",
            project_revision=project_context.current_revision,
            owner_approval_required=True,
            suggested_actions=[
                SuggestedProjectAction(
                    description=next_action,
                )
            ],
        )