import unittest

from app.services.project_action_execution_set_objective_handler import (
    ProjectActionExecutionSetObjectiveHandler,
)
from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionExecutionSetObjectiveHandlerTests(
    unittest.TestCase
):
    def test_sets_project_objective(
        self,
    ) -> None:
        projects = RecordingProjectObjectiveWriter()

        handler = ProjectActionExecutionSetObjectiveHandler(
            projects=projects,
        )

        step = {
            "sequence": 1,
            "description": "Set project objective",
            "capability": "PROJECT_ACTION",
            "action_type": "PROJECT_SET_OBJECTIVE",
            "payload": {
                "objective": "Improve project execution",
            },
        }

        context = ProjectActionExecutionContext(
            proposal_id="proposal-123",
            project_id="project-123",
            project_revision=97,
            step=step,
        )
        
        handler.execute(
            context,
        )

        self.assertEqual(
            projects.calls,
            [
                (
                    "project-123",
                    "Improve project execution",
                )
            ],
        )

class RecordingProjectObjectiveWriter:
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, str]
        ] = []

    def set_objective(
        self,
        project_id: str,
        objective: str,
    ) -> None:
        self.calls.append(
            (
                project_id,
                objective,
            )
        )