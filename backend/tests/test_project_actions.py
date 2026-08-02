import unittest

from app.services.project_actions import ProjectActionService
from app.services.project_context import ProjectContext


class ProjectActionServiceTests(unittest.TestCase):
    def test_explicit_next_action_becomes_owner_reviewed_suggestion(
        self,
    ) -> None:
        context = ProjectContext(
            title="Project Action Intelligence",
            objective="Surface safe owner-controlled next actions.",
            status="ACTIVE",
            current_summary="Project update proposals are complete.",
            next_action="Run acceptance tests",
            current_revision=3,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(
            analysis.status,
            "suggestion_available",
        )
        self.assertEqual(analysis.project_revision, 3)
        self.assertTrue(analysis.owner_approval_required)
        self.assertEqual(len(analysis.suggested_actions), 1)
        self.assertEqual(
            analysis.suggested_actions[0].description,
            "Run acceptance tests",
        )
    def test_missing_next_action_does_not_infer_suggestion(
        self,
    ) -> None:
        context = ProjectContext(
            title="No explicit action",
            objective="Do not invent Project actions.",
            status="ACTIVE",
            current_summary="Current work is complete.",
            next_action=None,
            current_revision=4,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(
            analysis.status,
            "no_explicit_action",
        )
        self.assertEqual(analysis.project_revision, 4)
        self.assertFalse(analysis.owner_approval_required)
        self.assertEqual(analysis.suggested_actions, [])
    def test_completed_project_does_not_surface_next_action(
        self,
    ) -> None:
        context = ProjectContext(
            title="Completed Project",
            objective="Respect Project lifecycle state.",
            status="COMPLETED",
            current_summary="The Project is complete.",
            next_action="Start another implementation phase",
            current_revision=5,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(
            analysis.status,
            "no_explicit_action",
        )
        self.assertEqual(analysis.project_revision, 5)
        self.assertFalse(analysis.owner_approval_required)
        self.assertEqual(analysis.suggested_actions, [])

    def test_archived_project_does_not_surface_next_action(
        self,
    ) -> None:
        context = ProjectContext(
            title="Archived Project",
            objective="Respect archived Project state.",
            status="ARCHIVED",
            current_summary="The Project has been archived.",
            next_action="Resume implementation",
            current_revision=6,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(
            analysis.status,
            "no_explicit_action",
        )
        self.assertEqual(analysis.project_revision, 6)
        self.assertFalse(analysis.owner_approval_required)
        self.assertEqual(analysis.suggested_actions, [])

    def test_paused_project_does_not_surface_next_action(
        self,
    ) -> None:
        context = ProjectContext(
            title="Paused Project",
            objective="Respect paused Project state.",
            status="PAUSED",
            current_summary="Work is temporarily paused.",
            next_action="Continue implementation",
            current_revision=7,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(
            analysis.status,
            "no_explicit_action",
        )
        self.assertEqual(analysis.project_revision, 7)
        self.assertFalse(analysis.owner_approval_required)
        self.assertEqual(analysis.suggested_actions, [])

    def test_no_suggestion_never_requires_owner_approval(
        self,
    ) -> None:
        context = ProjectContext(
            title="No Action",
            objective="Keep action analysis internally consistent.",
            status="ACTIVE",
            current_summary="No next action has been defined.",
            next_action=None,
            current_revision=8,
        )

        analysis = ProjectActionService().analyze(context)

        self.assertEqual(analysis.suggested_actions, [])
        self.assertFalse(analysis.owner_approval_required)

if __name__ == "__main__":
    unittest.main()