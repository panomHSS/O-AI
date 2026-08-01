from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.models.project import Project
from app.models.project_revision import ProjectRevision


class ProjectRepository:
    """Persistence boundary for explicit owner-managed project mutations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, title: str, objective: str) -> Project:
        project = Project(title=title, objective=objective, status="ACTIVE", current_revision=1)
        self._session.add(project)
        self._session.flush()
        return project

    def get(self, project_id: str) -> Project | None:
        return self._session.get(Project, project_id)

    def list(self, page: int, page_size: int, status: str | None) -> tuple[Sequence[Project], int]:
        filters = [Project.status == status] if status else []
        items = self._session.scalars(select(Project).where(*filters).order_by(Project.updated_at.desc(), Project.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        total = self._session.scalar(select(func.count(Project.id)).where(*filters)) or 0
        return items, total

    def history(self, project_id: str) -> Sequence[ProjectRevision]:
        return self._session.scalars(select(ProjectRevision).where(ProjectRevision.project_id == project_id).order_by(ProjectRevision.revision_number.desc())).all()

    def snapshot(self, project: Project, change_note: str) -> ProjectRevision:
        revision = ProjectRevision(project_id=project.id, revision_number=project.current_revision, title=project.title, objective=project.objective, status=project.status, current_summary=project.current_summary, next_action=project.next_action, change_note=change_note)
        self._session.add(revision)
        self._session.flush()
        return revision

    def mutate_if_current(self, project: Project, expected_revision: int, values: dict[str, object]) -> Project | None:
        result = self._session.execute(
            update(Project)
            .where(Project.id == project.id, Project.current_revision == expected_revision)
            .values(**values, current_revision=expected_revision + 1, updated_at=utc_now())
        )
        if result.rowcount != 1:
            return None
        self._session.expire(project)
        return self._session.get(Project, project.id)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
