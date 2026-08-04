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
            steps=[
                first_step,
                second_step,
            ]
        )

        executor.execute(
            proposal,
        )

        self.assertEqual(
            dispatcher.calls,
            [
                first_step,
                second_step,
            ],
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
            steps=[
                first_step,
                second_step,
                third_step,
            ]
        )

        with self.assertRaises(RuntimeError):
            executor.execute(
                proposal,
            )

        self.assertEqual(
            dispatcher.calls,
            [
                first_step,
                second_step,
            ],
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