from dataclasses import dataclass
from uuid import UUID

from app.schemas.project_update_proposals import (
    CreateProjectUpdateProposalRequest,
    ProjectUpdateProposalResponse,
)
from app.services.project_context import ProjectContext
from app.services.project_update_generation import (
    ProjectUpdateGenerationInput,
    ProjectUpdateProposalGenerator,
)
from app.services.project_update_proposals import (
    ProjectUpdateProposalService,
)


@dataclass(frozen=True)
class ProjectUpdateTurnInput:
    """Inputs required to analyze one completed Project chat turn."""

    conversation_id: UUID
    project_id: UUID
    base_revision: int
    user_message: str
    assistant_reply: str
    project_context: ProjectContext


class ProjectUpdateTurnOrchestrator:
    """Generate and persist owner-reviewable Project update proposals."""

    def __init__(
        self,
        generator: ProjectUpdateProposalGenerator,
        proposal_service: ProjectUpdateProposalService,
    ) -> None:
        self._generator = generator
        self._proposal_service = proposal_service

    def process(
        self,
        input_data: ProjectUpdateTurnInput,
    ) -> ProjectUpdateProposalResponse | None:
        generation = self._generator.generate(
            ProjectUpdateGenerationInput(
                user_message=input_data.user_message,
                assistant_reply=input_data.assistant_reply,
                project_context=input_data.project_context,
            )
        )

        candidate = generation.candidate

        if candidate is None:
            return None

        return self._proposal_service.create(
            CreateProjectUpdateProposalRequest(
                project_id=input_data.project_id,
                conversation_id=input_data.conversation_id,
                base_revision=input_data.base_revision,
                proposed_summary=candidate.proposed_summary,
                proposed_next_action=candidate.proposed_next_action,
                reason=candidate.reason,
            )
        )