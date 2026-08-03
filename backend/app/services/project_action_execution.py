"""Owner-controlled Project action execution proposal generation."""

from app.schemas.project_action_execution import (
    ProjectActionExecutionProposal,
)
from app.schemas.project_action_planning import (
    ProjectActionPlan,
)


class ProjectActionExecutionProposalService:
    """Convert an available Project action plan into an approval-gated proposal."""

    def propose(
        self,
        plan: ProjectActionPlan,
    ) -> ProjectActionExecutionProposal | None:
        if (
            plan.status != "plan_available"
            or not plan.owner_approval_required
        ):
            return None

        return ProjectActionExecutionProposal(
            status="awaiting_owner_approval",
            project_revision=plan.project_revision,
            source_action=plan.source_action,
            owner_approval_required=True,
            approved=False,
            executed=False,
            steps=plan.steps,
        )