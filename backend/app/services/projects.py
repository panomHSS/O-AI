from uuid import UUID

from sqlalchemy.exc import IntegrityError, OperationalError

from app.models.project import Project
from app.models.project_revision import ProjectRevision
from app.repositories.projects import ProjectRepository
from app.schemas.projects import (
    ChangeNextActionRequest, ChangeProjectStatusRequest, CreateProjectRequest,
    ProjectHistoryResponse, ProjectListResponse, ProjectResponse, ProjectRevisionResponse,
    RecordProjectProgressRequest, UpdateProjectDetailsRequest,
)


class ProjectNotFoundError(Exception):
    pass


class ProjectConflictError(Exception):
    pass


class ProjectValidationError(Exception):
    pass


_TRANSITIONS = {
    "ACTIVE": {"PAUSED", "COMPLETED", "ARCHIVED"},
    "PAUSED": {"ACTIVE", "COMPLETED", "ARCHIVED"},
    "COMPLETED": {"ACTIVE"},
    "ARCHIVED": {"ACTIVE"},
}


class ProjectService:
    """Owner-controlled durable project lifecycle with immutable revisions."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def create(self, payload: CreateProjectRequest) -> ProjectResponse:
        try:
            project = self._repository.create(payload.title.strip(), payload.objective.strip())
            self._repository.snapshot(project, payload.change_note.strip())
            self._repository.commit()
            return self._response(project)
        except Exception:
            self._repository.rollback()
            raise

    def get(self, project_id: UUID) -> ProjectResponse:
        return self._response(self._require(project_id))

    def list(self, page: int, page_size: int, status: str | None) -> ProjectListResponse:
        projects, total = self._repository.list(page, page_size, status)
        return ProjectListResponse(items=[self._response(item) for item in projects], page=page, page_size=page_size, total=total)

    def history(self, project_id: UUID) -> ProjectHistoryResponse:
        project = self._require(project_id)
        return ProjectHistoryResponse(items=[self._revision_response(item) for item in self._repository.history(project.id)])

    def update_details(self, project_id: UUID, payload: UpdateProjectDetailsRequest) -> ProjectResponse:
        project = self._checked(project_id, payload.expected_revision)
        if payload.title is None and payload.objective is None:
            raise ProjectValidationError("At least one project detail is required.")
        values: dict[str, object] = {}
        if payload.title is not None:
            values["title"] = payload.title.strip()
        if payload.objective is not None:
            values["objective"] = payload.objective.strip()
        return self._mutate(project, payload.expected_revision, payload.change_note, values)

    def record_progress(self, project_id: UUID, payload: RecordProjectProgressRequest) -> ProjectResponse:
        project = self._checked(project_id, payload.expected_revision)
        return self._mutate(project, payload.expected_revision, payload.change_note, {"current_summary": self._clean_optional(payload.current_summary)})

    def change_next_action(self, project_id: UUID, payload: ChangeNextActionRequest) -> ProjectResponse:
        project = self._checked(project_id, payload.expected_revision)
        return self._mutate(project, payload.expected_revision, payload.change_note, {"next_action": payload.next_action})

    def change_status(self, project_id: UUID, payload: ChangeProjectStatusRequest) -> ProjectResponse:
        project = self._checked(project_id, payload.expected_revision)
        if payload.status not in _TRANSITIONS[project.status]:
            raise ProjectValidationError("The requested project status transition is not allowed.")
        return self._mutate(project, payload.expected_revision, payload.change_note, {"status": payload.status})

    def _mutate(self, project: Project, expected_revision: int, change_note: str, values: dict[str, object]) -> ProjectResponse:
        try:
            updated = self._repository.mutate_if_current(project, expected_revision, values)
            if updated is None:
                raise ProjectConflictError("The project has a newer revision. Refresh and try again.")
            self._repository.snapshot(updated, change_note)
            self._repository.commit()
            return self._response(updated)
        except ProjectConflictError:
            self._repository.rollback()
            raise
        except (IntegrityError, OperationalError) as error:
            self._repository.rollback()
            raise ProjectConflictError("The project could not be updated because a newer revision exists.") from error
        except Exception:
            self._repository.rollback()
            raise

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    def _checked(self, project_id: UUID, expected_revision: int) -> Project:
        project = self._require(project_id)
        if project.current_revision != expected_revision:
            raise ProjectConflictError("The project has a newer revision. Refresh and try again.")
        return project

    def _require(self, project_id: UUID) -> Project:
        project = self._repository.get(str(project_id))
        if project is None:
            raise ProjectNotFoundError("The requested project was not found.")
        return project

    @staticmethod
    def _response(project: Project) -> ProjectResponse:
        return ProjectResponse(id=UUID(project.id), title=project.title, objective=project.objective, status=project.status, current_summary=project.current_summary, next_action=project.next_action, current_revision=project.current_revision, created_at=project.created_at, updated_at=project.updated_at)

    @staticmethod
    def _revision_response(item: ProjectRevision) -> ProjectRevisionResponse:
        return ProjectRevisionResponse(id=UUID(item.id), revision_number=item.revision_number, title=item.title, objective=item.objective, status=item.status, current_summary=item.current_summary, next_action=item.next_action, change_note=item.change_note, created_at=item.created_at)
