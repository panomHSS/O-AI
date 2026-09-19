# Explicit D93 workspace helpers for legacy tests only.

from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.models.conversation import Conversation
from app.models.project import Project

TEST_WORKSPACE_SCOPE = WorkspaceScope(WorkspaceId.PERSONAL)
TEST_WORKSPACE_ID = TEST_WORKSPACE_SCOPE.workspace_id.value


def ensure_project_action_parents(
    session,
    project_id: str,
    conversation_id: str,
    project_revision: int,
) -> None:
    project = session.get(Project, project_id)
    if project is None:
        project = Project(
            id=project_id,
            workspace_id=TEST_WORKSPACE_ID,
            title="Legacy project-action test parent",
            objective="Exercise D93 parent-scoped proposal lifecycle.",
            status="ACTIVE",
            current_revision=project_revision,
        )
        session.add(project)
    elif project.workspace_id is None:
        project.workspace_id = TEST_WORKSPACE_ID
    elif project.workspace_id != TEST_WORKSPACE_ID:
        raise AssertionError("Unexpected project workspace in legacy test.")

    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        conversation = Conversation(
            id=conversation_id,
            workspace_id=TEST_WORKSPACE_ID,
            title="Legacy project-action test conversation",
            project_id=project_id,
        )
        session.add(conversation)
    else:
        if conversation.workspace_id is None:
            conversation.workspace_id = TEST_WORKSPACE_ID
        elif conversation.workspace_id != TEST_WORKSPACE_ID:
            raise AssertionError(
                "Unexpected conversation workspace in legacy test."
            )
        if conversation.project_id != project_id:
            raise AssertionError(
                "Legacy test conversation belongs to a different project."
            )

    session.flush()


def create_project_action_proposal(repository, session, **kwargs):
    ensure_project_action_parents(
        session,
        str(kwargs["project_id"]),
        str(kwargs["conversation_id"]),
        int(kwargs["project_revision"]),
    )
    return repository.create(**kwargs)
