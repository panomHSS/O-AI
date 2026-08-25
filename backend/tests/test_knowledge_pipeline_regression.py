import unittest

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.orchestrator import KnowledgeOrchestrator
from app.intelligence.steps.retrieval_step import RetrievalStep
from app.intelligence.steps.evidence_step import EvidenceStep
from app.intelligence.steps.reasoning_step import (
    ReasoningStep,
)
from app.intelligence.steps.planning_step import PlanningStep
from app.intelligence.steps.decision_step import DecisionStep
from app.intelligence.steps.goal_step import GoalStep

class FakePipeline:
    def __init__(self) -> None:
        self.called = False

    def run(
        self,
        context: ExecutionContext,
    ) -> None:
        self.called = True
        context.response.answer = "pipeline"


class KnowledgeOrchestratorTests(unittest.TestCase):

    def test_execute_runs_pipeline(self) -> None:
        pipeline = FakePipeline()

        orchestrator = KnowledgeOrchestrator(
            pipeline,
        )

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="Hello",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        orchestrator.execute(
            context,
        )

        self.assertTrue(
            pipeline.called,
        )

        self.assertEqual(
            context.response.answer,
            "pipeline",
        )
class FakeIntent:
    def __init__(self) -> None:
        self.question = "boiler"
        self.important_terms = ["boiler"]


class FakeAnalyzer:
    def analyze(self, question: str):
        return FakeIntent()


class FakePlanner:
    def plan(self, intent):
        return ["boiler"]


class FakeRepository:
    def search(self, query: str, limit: int):
        return [
            {
                "chunk_id": "1",
                "content": "Boiler efficiency",
            }
        ]
class RetrievalStepTests(unittest.TestCase):

    def test_execute_populates_execution_context(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="How does a boiler work?",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        step = RetrievalStep(
            repository=FakeRepository(),
            analyzer=FakeAnalyzer(),
            planner=FakePlanner(),
            candidates_per_query=5,
        )

        step.execute(context)

        self.assertIsNotNone(
            context.knowledge.intent,
        )

        self.assertEqual(
            context.knowledge.queries,
            ["boiler"],
        )

        self.assertEqual(
            len(context.knowledge.records),
            1,
        )
class FakeEvidence:
    def __init__(self) -> None:
        self.document_id = "doc-001"
        self.chunk_id = "chunk-001"
        self.file_name = "manual.pdf"
        self.source_path = "/manual.pdf"
        self.source_locator = "P1"
        self.content = "Boiler efficiency"

        self.fts_score = 0.80
        self.file_extension = ".pdf"

        self.score = 0.95

class FakeRanker:
    def rank(
        self,
        question,
        terms,
        records,
    ):
        return (
            [FakeEvidence()],
            2,
            3,
        )


class FakeConflictDetector:
    def detect(
        self,
        selected,
        important_terms,
    ):
        return []


class FakeContextBuilder:
    def build(
        self,
        selected,
    ):
        return selected
class EvidenceStepTests(unittest.TestCase):

    def test_execute_stores_rank_results(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="boiler",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        context.knowledge.intent = FakeIntent()
        context.knowledge.records = [
            {
                "chunk_id": "1",
            }
        ]

        step = EvidenceStep(
            ranker=FakeRanker(),
            conflict_detector=FakeConflictDetector(),
            context_builder=FakeContextBuilder(),
            selected_limit=5,
        )

        step.execute(context)

        self.assertEqual(
            context.knowledge.duplicates_removed,
            2,
        )

        self.assertEqual(
            context.knowledge.filtered_out,
            3,
        )

        self.assertEqual(
            len(context.knowledge.evidence),
            1,
        )
class FakeReasoningPlan:
    pass


class FakeReasoningService:
    def plan(
        self,
        question,
        memories,
        evidence,
    ):
        return FakeReasoningPlan()


class FakeResolvedMemory:
    def __init__(self) -> None:
        self.memory_id = "11111111-1111-1111-1111-111111111111"
        self.version = 1
        self.key = "user.name"


class FakeMemoryResolver:
    def resolve(
        self,
        question,
    ):
        return (
            FakeResolvedMemory(),
        )
class FakePlanningPlan:
    pass


class FakePlanningService:
    def plan(self, reasoning):
        return FakePlanningPlan()
    
class ReasoningStepTests(unittest.TestCase):

    def test_execute_populates_reasoning_context(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="Who am I?",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        step = ReasoningStep(
            service=FakeReasoningService(),
            memory_resolver=FakeMemoryResolver(),
        )

        step.execute(context)

        self.assertIsNotNone(
            context.intelligence.reasoning,
        )

        self.assertEqual(
            len(context.conversation.memories),
            1,
        )

        self.assertEqual(
            context.conversation.memories[0].key,
            "user.name",
        )
        context.intelligence.reasoning = FakeReasoningPlan()

        step = PlanningStep(
            service=FakePlanningService(),
        )

        step.execute(context)

        self.assertIsNotNone(
            context.intelligence.planning,
        )
class PlanningStepTests(unittest.TestCase):

    def test_execute_populates_planning_context(self):

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="Hello",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        context.intelligence.reasoning = FakeReasoningPlan()

        step = PlanningStep(
            service=FakePlanningService(),
        )

        step.execute(context)

        self.assertIsNotNone(
            context.intelligence.planning,
        )
class FakeDecisionAnalysis:
    pass


class FakeDecisionService:
    def analyze(
        self,
        reasoning,
        planning,
    ):
        return FakeDecisionAnalysis()

class FakeGoalAnalysis:
    pass


class FakeGoalService:
    def analyze(
        self,
        reasoning,
        planning,
        decision,
    ):
        return FakeGoalAnalysis()

class GoalStepTests(unittest.TestCase):

    def test_execute_populates_goal_context(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="goal: improve extraction",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        context.intelligence.reasoning = FakeReasoningPlan()
        context.intelligence.planning = FakePlanningPlan()
        context.intelligence.decision = FakeDecisionAnalysis()

        step = GoalStep(
            service=FakeGoalService(),
        )

        step.execute(context)

        self.assertIsNotNone(
            context.intelligence.goals,
        )
    
class DecisionStepTests(unittest.TestCase):

    def test_execute_populates_decision_context(self) -> None:

        context = ExecutionContext(
            request=RequestContext(
                request_id="req-001",
                question="Compare pumps",
            ),
            conversation=ConversationContext(),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )

        context.intelligence.reasoning = FakeReasoningPlan()
        context.intelligence.planning = FakePlanningPlan()

        step = DecisionStep(
            service=FakeDecisionService(),
        )

        step.execute(context)

        self.assertIsNotNone(
            context.intelligence.decision,
        )

if __name__ == "__main__":
    unittest.main()