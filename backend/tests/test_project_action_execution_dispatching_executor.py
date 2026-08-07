import unittest
from types import SimpleNamespace

from app.services.project_action_execution_dispatching_executor import (
    ProjectActionExecutionDispatchingExecutor,
)


class ProjectActionExecutionDispatchingExecutorTests(
    unittest.TestCase
):
    def test_dispatches_every_proposal_step_in_order(
        self,
    ) -> None:
        dispatcher = RecordingDispatcher()

        executor = ProjectActionExecutionDispatchingExecutor(
            dispatcher=dispatcher,
        )

        first_step = {
            "sequence": 1,
            "description": "First action",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        second_step = {
            "sequence": 2,
            "description": "Second action",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        proposal = SimpleNamespace(
            id="proposal-123",
            project_id="project-123",
            project_revision=91,
            steps=[
                first_step,
                second_step,
            ],
        )

        executor.execute(
            proposal,
        )

        self.assertEqual(
            len(dispatcher.calls),
            2,
        )

        self.assertEqual(
            dispatcher.calls[0].proposal_id,
            "proposal-123",
        )
        self.assertEqual(
            dispatcher.calls[0].project_id,
            "project-123",
        )
        self.assertEqual(
            dispatcher.calls[0].project_revision,
            91,
        )
        self.assertEqual(
            dispatcher.calls[0].step,
            first_step,
        )

        self.assertEqual(
            dispatcher.calls[1].proposal_id,
            "proposal-123",
        )
        self.assertEqual(
            dispatcher.calls[1].project_id,
            "project-123",
        )
        self.assertEqual(
            dispatcher.calls[1].project_revision,
            91,
        )
        self.assertEqual(
            dispatcher.calls[1].step,
            second_step,
        )

    def test_stops_dispatching_after_first_failure(
        self,
    ) -> None:
        dispatcher = FailingSecondDispatcher()

        executor = ProjectActionExecutionDispatchingExecutor(
            dispatcher=dispatcher,
        )

        first_step = {
            "sequence": 1,
            "description": "First action",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        second_step = {
            "sequence": 2,
            "description": "Failing action",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        third_step = {
            "sequence": 3,
            "description": "Must not execute",
            "capability": "PROJECT_ACTION",
            "action_type": "NO_OP",
            "payload": {},
        }

        proposal = SimpleNamespace(
            id="proposal-456",
            project_id="project-456",
            project_revision=92,
            steps=[
                first_step,
                second_step,
                third_step,
            ],
        )

        with self.assertRaises(RuntimeError):
            executor.execute(
                proposal,
            )

        self.assertEqual(
            len(dispatcher.calls),
            2,
        )

        self.assertEqual(
            dispatcher.calls[0].project_revision,
            92,
        )
        self.assertEqual(
            dispatcher.calls[0].step,
            first_step,
        )

        self.assertEqual(
            dispatcher.calls[1].project_revision,
            92,
        )
        self.assertEqual(
            dispatcher.calls[1].step,
            second_step,
        )

    def test_dispatches_trusted_execution_context(
        self,
    ) -> None:
        dispatcher = RecordingContextDispatcher()

        executor = ProjectActionExecutionDispatchingExecutor(
            dispatcher=dispatcher,
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

        proposal = SimpleNamespace(
            id="proposal-123",
            project_id="project-123",
            project_revision=97,
            steps=[
                step,
            ],
        )

        executor.execute(
            proposal,
        )

        self.assertEqual(
            len(dispatcher.calls),
            1,
        )

        context = dispatcher.calls[0]

        self.assertEqual(
            context.proposal_id,
            "proposal-123",
        )
        self.assertEqual(
            context.project_id,
            "project-123",
        )
        self.assertEqual(
            context.project_revision,
            97,
        )
        self.assertEqual(
            context.step,
            step,
        )
        
class RecordingDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch(
        self,
        step: dict,
    ) -> None:
        self.calls.append(step)

class FailingSecondDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def dispatch(
        self,
        step: dict,
    ) -> None:
        self.calls.append(step)

        if len(self.calls) == 2:
            raise RuntimeError(
                "Dispatch failed."
            )

class RecordingContextDispatcher:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def dispatch(
        self,
        context: object,
    ) -> None:
        self.calls.append(
            context
        )