import unittest

from app.schemas.project_actions import (
    ProjectActionAnalysis,
    SuggestedProjectAction,
)
from app.services.project_action_planning import (
    ProjectActionPlanningService,
)
from app.schemas.project_action_planning import (
    ProjectActionPlan,
    ProjectActionPlanStep,
)


class ProjectActionPlanSchemaTests(unittest.TestCase):
    def test_project_action_plan_preserves_structured_steps(
        self,
    ) -> None:
        plan = ProjectActionPlan(
            status="plan_available",
            project_revision=9,
            source_action="Run acceptance tests",
            owner_approval_required=True,
            steps=[
                ProjectActionPlanStep(
                    sequence=1,
                    description="Prepare acceptance-test environment",
                ),
                ProjectActionPlanStep(
                    sequence=2,
                    description="Run targeted acceptance tests",
                ),
            ],
        )

        self.assertEqual(plan.status, "plan_available")
        self.assertEqual(plan.project_revision, 9)
        self.assertEqual(
            plan.source_action,
            "Run acceptance tests",
        )
        self.assertTrue(plan.owner_approval_required)
        self.assertEqual(len(plan.steps), 2)

        self.assertEqual(plan.steps[0].sequence, 1)
        self.assertEqual(
            plan.steps[0].description,
            "Prepare acceptance-test environment",
        )

        self.assertEqual(plan.steps[1].sequence, 2)
        self.assertEqual(
            plan.steps[1].description,
            "Run targeted acceptance tests",
        )
    def test_action_suggestion_creates_structured_plan(
        self,
    ) -> None:
        analysis = ProjectActionAnalysis(
            status="suggestion_available",
            project_revision=9,
            owner_approval_required=True,
            suggested_actions=[
                SuggestedProjectAction(
                    description="Run acceptance tests",
                )
            ],
        )

        plan = ProjectActionPlanningService().plan(analysis)

        self.assertEqual(plan.status, "plan_available")
        self.assertEqual(plan.project_revision, 9)
        self.assertEqual(
            plan.source_action,
            "Run acceptance tests",
        )
        self.assertTrue(plan.owner_approval_required)
        self.assertGreaterEqual(len(plan.steps), 1)

        self.assertEqual(plan.steps[0].sequence, 1)
        self.assertTrue(plan.steps[0].description)

    def test_no_explicit_action_creates_no_plan(
        self,
    ) -> None:
        analysis = ProjectActionAnalysis(
            status="no_explicit_action",
            project_revision=10,
            owner_approval_required=False,
            suggested_actions=[],
        )

        plan = ProjectActionPlanningService().plan(analysis)

        self.assertEqual(
            plan.status,
            "no_plan_available",
        )
        self.assertEqual(plan.project_revision, 10)
        self.assertIsNone(plan.source_action)
        self.assertFalse(plan.owner_approval_required)
        self.assertEqual(plan.steps, [])

    def test_suggestion_status_without_action_creates_no_plan(
        self,
    ) -> None:
        analysis = ProjectActionAnalysis(
            status="suggestion_available",
            project_revision=11,
            owner_approval_required=True,
            suggested_actions=[],
        )

        plan = ProjectActionPlanningService().plan(analysis)

        self.assertEqual(
            plan.status,
            "no_plan_available",
        )
        self.assertEqual(plan.project_revision, 11)
        self.assertIsNone(plan.source_action)
        self.assertFalse(plan.owner_approval_required)
        self.assertEqual(plan.steps, [])


if __name__ == "__main__":
    unittest.main()