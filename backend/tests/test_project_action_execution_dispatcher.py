import unittest

from app.services.project_action_execution_dispatcher import (
    ProjectActionExecutionDispatcher,
)
from app.services.project_action_execution_no_op_handler import (
    ProjectActionExecutionNoOpHandler,
)
from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionExecutionDispatcherTests(
    unittest.TestCase
):
    def test_dispatches_supported_action_type(
        self,
    ) -> None:
        handler = RecordingActionHandler()

        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "NO_OP": handler,
            }
        )

        step = {
            "sequence": 1,
            "description": "Perform no operation",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        context = make_context(
            step,
        )

        dispatcher.dispatch(
            context,
        )
        self.assertEqual(
            handler.calls,
            [context],
        )    

    def test_rejects_unknown_action_type(
        self,
    ) -> None:
        handler = RecordingActionHandler()

        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "NO_OP": handler,
            }
        )

        step = {
            "sequence": 1,
            "description": "Unknown action",
            "capability": "PROJECT_ACTION",
            "action_type": "UNKNOWN_ACTION",
            "payload": {},
        }

        context = make_context(
            step,
        )

        with self.assertRaises(ValueError):
            dispatcher.dispatch(
                context,
            )

        self.assertEqual(
            handler.calls,
            [],
        )

    def test_rejects_missing_action_type(
        self,
    ) -> None:
        handler = RecordingActionHandler()

        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "NO_OP": handler,
            }
        )

        step = {
            "sequence": 1,
            "description": "Missing action type",
            "capability": "PROJECT_ACTION",
            "payload": {},
        }

        context = make_context(
            step,
        )

        with self.assertRaises(ValueError):
            dispatcher.dispatch(
                context,
            )

        self.assertEqual(
            handler.calls,
            [],
        )

    def test_dispatches_only_matching_handler(
        self,
    ) -> None:
        no_op_handler = RecordingActionHandler()
        other_handler = RecordingActionHandler()

        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "NO_OP": no_op_handler,
                "OTHER_ACTION": other_handler,
            }
        )

        step = {
            "sequence": 1,
            "description": "Perform no operation",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        context = make_context(
            step,
        )

        dispatcher.dispatch(
            context,
        )

        self.assertEqual(
            no_op_handler.calls,
            [context],
        )
        self.assertEqual(
            other_handler.calls,
            [],
        )
        self.assertEqual(
            no_op_handler.calls,
            [context],
        )
        self.assertEqual(
            other_handler.calls,
            [],
        )

    def test_dispatches_no_op_to_official_handler(
        self,
    ) -> None:
        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "NO_OP": ProjectActionExecutionNoOpHandler(),
            }
        )

        step = {
            "sequence": 1,
            "description": "Perform no operation",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        context = make_context(
            step,
        )

        result = dispatcher.dispatch(
            context,
        )

        self.assertIsNone(
            result,
        )

    def test_dispatches_execution_context_to_matching_handler(
        self,
    ) -> None:
        handler = RecordingContextActionHandler()

        dispatcher = ProjectActionExecutionDispatcher(
            handlers={
                "PROJECT_SET_OBJECTIVE": handler,
            }
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
        
        dispatcher.dispatch(
            context,
        )

        self.assertEqual(
            handler.calls,
            [context],
        )


class RecordingActionHandler:
    def __init__(self) -> None:
        self.calls: list[
            ProjectActionExecutionContext
        ] = []

    def execute(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        self.calls.append(
            context
        )

class RecordingContextActionHandler:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def execute(
        self,
        context: object,
    ) -> None:
        self.calls.append(
            context
        )

def make_context(
    step: dict,
) -> ProjectActionExecutionContext:
    return ProjectActionExecutionContext(
        proposal_id="proposal-123",
        project_id="project-123",
        project_revision=97,
        step=step,
    )