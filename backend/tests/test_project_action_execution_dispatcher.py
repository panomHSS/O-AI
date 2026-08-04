import unittest

from app.services.project_action_execution_dispatcher import (
    ProjectActionExecutionDispatcher,
)
from app.services.project_action_execution_no_op_handler import (
    ProjectActionExecutionNoOpHandler,
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

        dispatcher.dispatch(
            step,
        )

        self.assertEqual(
            handler.calls,
            [step],
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

        with self.assertRaises(ValueError):
            dispatcher.dispatch(
                step,
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

        with self.assertRaises(ValueError):
            dispatcher.dispatch(
                step,
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

        dispatcher.dispatch(
            step,
        )

        self.assertEqual(
            no_op_handler.calls,
            [step],
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

        result = dispatcher.dispatch(
            step,
        )

        self.assertIsNone(
            result,
        )


class RecordingActionHandler:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(
        self,
        step: dict,
    ) -> None:
        self.calls.append(step)