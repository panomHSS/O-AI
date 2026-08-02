from pydantic import BaseModel, Field, model_validator


class ProjectUpdateProposalCandidate(BaseModel):
    """Bounded candidate produced by Project update analysis."""

    proposed_summary: str | None = Field(
        default=None,
        max_length=4000,
    )
    proposed_next_action: str | None = Field(
        default=None,
        max_length=512,
    )
    reason: str = Field(
        min_length=1,
        max_length=512,
    )

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdateProposalCandidate":
        if (
            self.proposed_summary is None
            and self.proposed_next_action is None
        ):
            raise ValueError(
                "At least one proposed Project progress field is required."
            )
        return self


class ProjectUpdateGenerationResult(BaseModel):
    """Result of deciding whether one conversation turn merits a proposal."""

    candidate: ProjectUpdateProposalCandidate | None = None

    @property
    def should_propose(self) -> bool:
        return self.candidate is not None