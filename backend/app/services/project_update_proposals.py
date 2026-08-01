from uuid import UUID

from app.repositories.conversations import ConversationRepository
from app.repositories.project_update_proposals import (
    ProjectUpdateProposalRepository,
)
from app.schemas.project_update_proposals import (
    CreateProjectUpdateProposalRequest,
    ProjectUpdateProposalListResponse,
    ProjectUpdateProposalResponse,
)
from app.services.projects import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
)


class ProjectUpdateProposalNotFoundError(Exception):
    pass


class ProjectUpdateProposalConflictError(Exception):
    pass


class ProjectUpdateProposalValidationError(Exception):
    pass


class ProjectUpdateProposalService:
    """Owner-reviewed Project update proposal lifecycle."""

    def __init__(
        self,
        repository: ProjectUpdateProposalRepository,
        conversation_repository: ConversationRepository,
        project_service: ProjectService,
    ) -> None:
        self._repository = repository
        self._conversation_repository = conversation_repository
        self._project_service = project_service

    def create(
        self,
        payload: CreateProjectUpdateProposalRequest,
    ) -> ProjectUpdateProposalResponse:
        try:
            conversation = self._conversation_repository.get(
                str(payload.conversation_id)
            )
            if conversation is None:
                raise ProjectUpdateProposalValidationError(
                    "The requested conversation was not found."
                )

            if conversation.project_id is None:
                raise ProjectUpdateProposalValidationError(
                    "The conversation is not associated with a Project."
                )

            if conversation.project_id != str(payload.project_id):
                raise ProjectUpdateProposalValidationError(
                    "The conversation is associated with a different Project."
                )

            project = self._project_service.get(payload.project_id)

            if project.current_revision != payload.base_revision:
                raise ProjectUpdateProposalConflictError(
                    "The Project has a newer revision."
                )

            if (
                payload.proposed_summary is None
                and payload.proposed_next_action is None
            ):
                raise ProjectUpdateProposalValidationError(
                    "At least one proposed Project progress field is required."
                )

            proposal = self._repository.create(
                project_id=str(payload.project_id),
                conversation_id=str(payload.conversation_id),
                base_revision=payload.base_revision,
                proposed_summary=payload.proposed_summary,
                proposed_next_action=payload.proposed_next_action,
                reason=payload.reason,
            )
            self._repository.commit()
            return self._response(proposal)

        except (
            ProjectUpdateProposalValidationError,
            ProjectUpdateProposalConflictError,
            ProjectNotFoundError,
        ):
            self._repository.rollback()
            raise
        except Exception:
            self._repository.rollback()
            raise

    def get(
        self,
        proposal_id: UUID,
    ) -> ProjectUpdateProposalResponse:
        proposal = self._repository.get(str(proposal_id))
        if proposal is None:
            raise ProjectUpdateProposalNotFoundError(
                "The requested Project update proposal was not found."
            )
        return self._response(proposal)

    def list_for_project(
        self,
        project_id: UUID,
        status: str | None = None,
    ) -> ProjectUpdateProposalListResponse:
        items = self._repository.list_for_project(
            str(project_id),
            status,
        )
        return ProjectUpdateProposalListResponse(
            items=[self._response(item) for item in items]
        )

    def reject(
        self,
        proposal_id: UUID,
    ) -> ProjectUpdateProposalResponse:
        try:
            proposal = self._require_pending(proposal_id)

            decided = self._repository.decide_if_pending(
                proposal.id,
                "REJECTED",
            )
            if decided is None:
                raise ProjectUpdateProposalConflictError(
                    "The proposal has already been decided."
                )

            self._repository.commit()
            return self._response(decided)

        except (
            ProjectUpdateProposalNotFoundError,
            ProjectUpdateProposalConflictError,
        ):
            self._repository.rollback()
            raise
        except Exception:
            self._repository.rollback()
            raise

    def approve(
        self,
        proposal_id: UUID,
    ) -> ProjectUpdateProposalResponse:
        try:
            proposal = self._require_pending(proposal_id)

            try:
                project = self._project_service.get(
                    UUID(proposal.project_id)
                )
            except ProjectNotFoundError:
                raise ProjectUpdateProposalValidationError(
                    "The proposal's Project was not found."
                )

            if project.current_revision != proposal.base_revision:
                stale = self._repository.decide_if_pending(
                    proposal.id,
                    "STALE",
                )
                if stale is None:
                    raise ProjectUpdateProposalConflictError(
                        "The proposal has already been decided."
                    )

                self._repository.commit()
                return self._response(stale)

            updated = self._project_service.stage_progress_update(
                UUID(proposal.project_id),
                expected_revision=proposal.base_revision,
                current_summary=proposal.proposed_summary,
                next_action=proposal.proposed_next_action,
                change_note=f"Applied Project update proposal {proposal.id}.",
            )

            applied = self._repository.decide_if_pending(
                proposal.id,
                "APPLIED",
                applied_revision=updated.current_revision,
            )
            if applied is None:
                raise ProjectUpdateProposalConflictError(
                    "The proposal has already been decided."
                )

            self._repository.commit()
            return self._response(applied)

        except ProjectConflictError:
            self._repository.rollback()
            raise ProjectUpdateProposalConflictError(
                "The Project changed while the proposal was being approved."
            )
        except (
            ProjectUpdateProposalNotFoundError,
            ProjectUpdateProposalConflictError,
            ProjectUpdateProposalValidationError,
        ):
            self._repository.rollback()
            raise
        except Exception:
            self._repository.rollback()
            raise

    def _require_pending(self, proposal_id: UUID):
        proposal = self._repository.get(str(proposal_id))

        if proposal is None:
            raise ProjectUpdateProposalNotFoundError(
                "The requested Project update proposal was not found."
            )

        if proposal.status != "PENDING":
            raise ProjectUpdateProposalConflictError(
                "The proposal has already been decided."
            )

        return proposal

    @staticmethod
    def _response(proposal) -> ProjectUpdateProposalResponse:
        return ProjectUpdateProposalResponse(
            id=UUID(proposal.id),
            project_id=UUID(proposal.project_id),
            conversation_id=UUID(proposal.conversation_id),
            base_revision=proposal.base_revision,
            proposed_summary=proposal.proposed_summary,
            proposed_next_action=proposal.proposed_next_action,
            reason=proposal.reason,
            status=proposal.status,
            created_at=proposal.created_at,
            decided_at=proposal.decided_at,
            applied_revision=proposal.applied_revision,
        )