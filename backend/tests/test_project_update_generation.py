import unittest

from app.services.project_context import ProjectContext
from app.services.project_update_generation import (
    ProjectUpdateGenerationInput,
    ProjectUpdateProposalGenerator,
)


class ProjectUpdateProposalGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = ProjectUpdateProposalGenerator()
        self.context = ProjectContext(
            title="O-AI",
            objective="Build a safe personal assistant.",
            status="ACTIVE",
            current_summary="Project backbone completed.",
            next_action="Implement proposal generation.",
            current_revision=1,
        )

    def test_without_project_context_does_not_propose(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Progress: Milestone completed.",
                assistant_reply="Great.",
                project_context=None,
            )
        )

        self.assertFalse(result.should_propose)

    def test_ordinary_conversation_does_not_propose(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="What should we work on next?",
                assistant_reply="We can continue the Project.",
                project_context=self.context,
            )
        )

        self.assertFalse(result.should_propose)

    def test_explicit_progress_creates_summary_candidate(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Progress: Proposal generator implemented.",
                assistant_reply="Recorded.",
                project_context=self.context,
            )
        )

        self.assertTrue(result.should_propose)
        self.assertEqual(
            result.candidate.proposed_summary,
            "Proposal generator implemented.",
        )
        self.assertIsNone(result.candidate.proposed_next_action)

    def test_explicit_next_action_creates_next_action_candidate(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Next action: Add proposal generation tests.",
                assistant_reply="Understood.",
                project_context=self.context,
            )
        )

        self.assertTrue(result.should_propose)
        self.assertEqual(
            result.candidate.proposed_next_action,
            "Add proposal generation tests.",
        )
        self.assertIsNone(result.candidate.proposed_summary)

    def test_unchanged_summary_does_not_propose(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Progress: Project backbone completed.",
                assistant_reply="No change.",
                project_context=self.context,
            )
        )

        self.assertFalse(result.should_propose)

    def test_unchanged_next_action_does_not_propose(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Next action: Implement proposal generation.",
                assistant_reply="No change.",
                project_context=self.context,
            )
        )

        self.assertFalse(result.should_propose)

    def test_assistant_reply_cannot_create_candidate_by_itself(self) -> None:
        result = self.generator.generate(
            ProjectUpdateGenerationInput(
                user_message="Okay.",
                assistant_reply="Progress: Everything is complete.",
                project_context=self.context,
            )
        )

        self.assertFalse(result.should_propose)


if __name__ == "__main__":
    unittest.main()