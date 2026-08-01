import unittest
from app.schemas.reasoning import ReasoningPlan
from app.services.decision import DecisionService
from app.services.goals import GoalContextBuilder, GoalService
from app.services.planning import PlanningService

class GoalServiceTests(unittest.TestCase):
    def test_explicit_candidates_are_deterministic_and_non_persistent_metadata(self):
        reasoning = ReasoningPlan(intent="general", normalized_question="goal: Learn Python")
        planning = PlanningService().plan(reasoning); decision = DecisionService().analyze(reasoning, planning)
        result = GoalService().analyze(reasoning, planning, decision)
        self.assertEqual([(item.id, item.title) for item in result.goals], [("goal-1", "Learn Python")])
        self.assertEqual(result.status, "candidate")
        self.assertIn("Do not create, change, schedule, execute", GoalContextBuilder.build(result))
    def test_unmarked_text_is_not_a_goal_or_project(self):
        reasoning = ReasoningPlan(intent="general", normalized_question="Learn Python")
        planning = PlanningService().plan(reasoning); decision = DecisionService().analyze(reasoning, planning)
        result = GoalService().analyze(reasoning, planning, decision)
        self.assertEqual((result.goals, result.projects, result.status), ([], [], "not_applicable"))
