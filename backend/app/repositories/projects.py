from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.contracts.workspace import WorkspaceScope
from app.db.base import utc_now
from app.models.project import Project
from app.models.project_revision import ProjectRevision


class ProjectRepository:
    """Workspace-scoped persistence boundary for owner-managed Projects."""

    def __init__(
        self,
        session: Session,
        workspace_scope: WorkspaceScope,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_scope.workspace_id.value

    def create(self, title: str, objective: str) -> Project:
        project = Project(
            title=title,
            objective=objective,
            status="ACTIVE",
            current_revision=1,
            workspace_id=self._workspace_id,
        )
        self._session.add(project)
        self._session.flush()
        return project

    def get(self, project_id: str) -> Project | None:
        return self._session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == self._workspace_id,
            )
        )

    def list(
        self,
        page: int,
        page_size: int,
        status: str | None,
    ) -> tuple[Sequence[Project], int]:
        filters = [Project.workspace_id == self._workspace_id]
        if status:
            filters.append(Project.status == status)

        items = self._session.scalars(
            select(Project)
            .where(*filters)
            .order_by(
                Project.updated_at.desc(),
                Project.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        total = (
            self._session.scalar(
                select(func.count(Project.id)).where(*filters)
            )
            or 0
        )
        return items, total

    def history(self, project_id: str) -> Sequence[ProjectRevision]:
        return self._session.scalars(
            select(ProjectRevision)
            .join(Project, Project.id == ProjectRevision.project_id)
            .where(
                ProjectRevision.project_id == project_id,
                Project.workspace_id == self._workspace_id,
            )
            .order_by(ProjectRevision.revision_number.desc())
        ).all()

    def snapshot(
        self,
        project: Project,
        change_note: str,
    ) -> ProjectRevision:
        self._require_owned(project)
        revision = ProjectRevision(
            project_id=project.id,
            revision_number=project.current_revision,
            title=project.title,
            objective=project.objective,
            status=project.status,
            current_summary=project.current_summary,
            next_action=project.next_action,
            change_note=change_note,
        )
        self._session.add(revision)
        self._session.flush()
        return revision

    def mutate_if_current(
        self,
        project: Project,
        expected_revision: int,
        values: dict[str, object],
    ) -> Project | None:
        self._require_owned(project)
        result = self._session.execute(
            update(Project)
            .where(
                Project.id == project.id,
                Project.workspace_id == self._workspace_id,
                Project.current_revision == expected_revision,
            )
            .values(
                **values,
                current_revision=expected_revision + 1,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            return None
        self._session.expire(project)
        return self.get(project.id)

    def _require_owned(self, project: Project) -> None:
        if project.workspace_id != self._workspace_id:
            raise ValueError("workspace_mismatch")

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
