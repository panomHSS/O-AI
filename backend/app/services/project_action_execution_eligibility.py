"""Eligibility boundary for Project action execution."""


class ProjectActionExecutionEligibilityService:
    """Decide whether an execution proposal may enter execution."""

    def is_eligible(
        self,
        proposal,
        current_project_revision: int | None = None,
    ) -> bool:
        if (
            proposal.status != "APPROVED"
            or proposal.approved is not True
            or proposal.executed is not False
        ):
            return False

        if current_project_revision is None:
            return False

        proposal_revision = proposal.project_revision

        if (
            not self._valid_revision(proposal_revision)
            or not self._valid_revision(
                current_project_revision
            )
        ):
            return False

        return (
            proposal_revision
            == current_project_revision
        )

    @staticmethod
    def _valid_revision(
        value: object,
    ) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 1
        )