import re
from hashlib import sha256
from uuid import UUID
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge_answer import CitationResponse, ConflictResponse, KnowledgeAnswerResponse, RetrievalSummaryResponse
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.memory_resolver import MemoryResolver
from app.services.reasoning import ReasoningService
from app.services.planning import PlanningService
from app.services.decision import DecisionService
from app.services.goals import GoalService
from app.repositories.message_citations import CitationSnapshot, MAX_CITATIONS_PER_MESSAGE
from app.services.knowledge_intelligence import CitationEngine, ConfidenceEvaluator, ConflictDetector, ContextBuilder, Evidence, EvidenceRanker, GroundedPromptBuilder, IntentAnalyzer, RetrievalPlanner
from app.intelligence.context.execution import ExecutionContext
from app.services.knowledge_intelligence import (
    ConflictDetector,
    ContextBuilder,
    EvidenceRanker,
)
from app.intelligence.orchestrator.knowledge_orchestrator import (
    KnowledgeOrchestrator,
)
from uuid import uuid4

from app.intelligence.context import (
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.intelligence.orchestrator import (
    KnowledgeOrchestrator,
)
from app.intelligence.orchestrator import (
    KnowledgeOrchestrator,
)

class KnowledgeAnswerService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        conversations: ConversationService,
        chat: ChatService,
        analyzer: IntentAnalyzer,
        planner: RetrievalPlanner,
        ranker: EvidenceRanker,
        conflict_detector: ConflictDetector,
        context_builder: ContextBuilder,
        prompt_builder: GroundedPromptBuilder,
        citations: CitationEngine,
        confidence: ConfidenceEvaluator,
        candidates_per_query: int,
        selected_limit: int,
        memory_resolver: MemoryResolver | None = None,
        reasoning_service: ReasoningService | None = None,
        planning_service: PlanningService | None = None,
        decision_service: DecisionService | None = None,
        goal_service: GoalService | None = None,
        orchestrator: KnowledgeOrchestrator | None = None,
    ) -> None:
        self._repository, self._conversations, self._chat = repository, conversations, chat
        self._analyzer, self._planner, self._ranker, self._conflicts = analyzer, planner, ranker, conflict_detector
        self._context, self._prompt, self._citations, self._confidence = context_builder, prompt_builder, citations, confidence
        self._candidates_per_query, self._selected_limit = candidates_per_query, selected_limit
        self._memory_resolver = memory_resolver
        self._reasoning_service = reasoning_service or ReasoningService()
        self._planning_service = planning_service or PlanningService()
        self._decision_service = decision_service or DecisionService()
        self._goal_service = goal_service or GoalService()
        self._orchestrator = orchestrator

    def _create_execution_context(
        self,
        *,
        question: str,
        conversation,
        history,
        project_context,
    ) -> ExecutionContext:
        return ExecutionContext(
            request=RequestContext(
                request_id=str(uuid4()),
                question=question,
                conversation_id=UUID(conversation.id),
                project_id=conversation.project_id,
            ),
            conversation=ConversationContext(
                history=history,
                project_context=project_context,
            ),
            knowledge=KnowledgeContext(),
            intelligence=IntelligenceContext(),
            response=ResponseContext(),
        )
    
    def _retrieve_records(
        self,
        question: str,
    ) -> tuple:
        intent = self._analyzer.analyze(
            question,
        )
        queries = self._planner.plan(intent)
        records = []
        seen = set()

        for query in queries:
            normalized_query = " ".join(query.split())

            if not normalized_query:
                continue

            for item in self._repository.search(
                normalized_query,
                self._candidates_per_query,
            ):
                if item["chunk_id"] not in seen:
                    records.append(item)
                    seen.add(item["chunk_id"])

        return (
            intent,
            queries,
            records,
        )
    def _build_evidence(
        self,
        intent,
        records,
    ):
        selected, duplicates, filtered = self._ranker.rank(
            intent.question,
            intent.important_terms,
            records,
        )

        selected = [
            Evidence(
                **{
                    **item.__dict__,
                    "citation_id": f"S{index}",
                }
            )
            for index, item in enumerate(
                selected[: self._selected_limit],
                1,
            )
        ]

        conflicts = self._conflicts.detect(
            selected,
            intent.important_terms,
        )

        context = self._context.build(selected)

        return (
            selected,
            duplicates,
            filtered,
            conflicts,
            context,
        )

    def _build_response(
        self,
        *,
        answer,
        valid,
        quality,
        conversation,
        records,
        context,
        duplicates,
        filtered,
        conflicts,
        queries,
        memories,
        reasoning_plan,
        planning_plan,
        decision_analysis,
        goal_analysis,
    ):
        return KnowledgeAnswerResponse(
            answer=answer,
            citations=[
                CitationResponse(
                    id=item.citation_id,
                    document_id=UUID(item.document_id),
                    file_name=item.file_name,
                    source_path=item.source_path,
                    source_locator=item.source_locator,
                    excerpt=item.content[:500],
                )
                for item in valid
            ],
            evidence_quality=quality,
            conversation_id=UUID(conversation.id),
            retrieval_summary=RetrievalSummaryResponse(
                candidates_considered=len(records),
                evidence_selected=len(context),
                duplicates_removed=duplicates,
                filtered_out=filtered,
                conflicting_evidence_count=len(conflicts),
                queries_used=queries,
            ),
            conflicts=[
                ConflictResponse(
                    citations=list(item.citation_ids),
                    reason=item.reason,
                )
                for item in conflicts
            ],
            memories_used=[
                {
                    "memory_id": item.memory_id,
                    "version": item.version,
                    "key": item.key,
                }
                for item in memories
            ],
            reasoning_plan=reasoning_plan,
            planning_plan=planning_plan,
            decision_analysis=decision_analysis,
            goal_analysis=goal_analysis,
        )

    def _prepare_response(
        self,
        *,
        question,
        history,
        project_context,
        intent,
        context,
        conflicts,
    ):

        if not context:
            memories = ()
            reasoning_plan = self._reasoning_service.plan(
                question,
                memories,
                context,
            )

            planning_plan = self._planning_service.plan(
                reasoning_plan,
            )

            decision_analysis = self._decision_service.analyze(
                reasoning_plan,
                planning_plan,
            )

            goal_analysis = self._goal_service.analyze(
                reasoning_plan,
                planning_plan,
                decision_analysis,
            )

            answer = self._chat.send_message(
                self._prompt.build(
                    intent.question,
                    context,
                    conflicts,
                ),
                history,
                memories,
                reasoning_plan,
                planning_plan,
                decision_analysis,
                goal_analysis,
                project_context,
            )

            answer, valid = self._citations.validate(
                answer,
                context,
            )

            if not valid:
                answer = (
                    "Sufficient supporting evidence was not found in local documents."
                )

        return (
            answer,
            valid,
            memories,
            reasoning_plan,
            planning_plan,
            decision_analysis,
            goal_analysis,
        )

    def answer(self, question: str, conversation_id: UUID | None, project_id: UUID | None = None) -> KnowledgeAnswerResponse:
        conversation, history = self._conversations.begin_turn(question, conversation_id, project_id)
        project_context = self._conversations.resolve_project_context(conversation)
        execution_context = self._create_execution_context(
            question=question,
            conversation=conversation,
            history=history,
            project_context=project_context,
        ) 
        if self._orchestrator is not None:
            self._orchestrator.execute(
                execution_context,
            )
        knowledge = execution_context.knowledge
        intelligence = execution_context.intelligence
        (
            intent,
            queries,
            records,
        ) = self._retrieve_records(
            question,
        )
        (
            selected,
            duplicates,
            filtered,
            conflicts,
            context,
        ) = self._build_evidence(
            intent,
            records,
        )
        # Runtime Switch (D11)
        if knowledge.intent is not None:
            intent = knowledge.intent

        if knowledge.queries:
            queries = knowledge.queries

        if knowledge.records:
            records = knowledge.records

        if knowledge.context:
            context = knowledge.context

        if knowledge.conflicts:
            conflicts = knowledge.conflicts

        duplicates = knowledge.duplicates_removed
        filtered = knowledge.filtered_out

        if not context:
            answer = "Sufficient supporting evidence was not found in local documents."
            valid = []
            memories = ()
            reasoning_plan = self._reasoning_service.plan(question, memories, context)
            planning_plan = self._planning_service.plan(reasoning_plan)
            decision_analysis = self._decision_service.analyze(reasoning_plan, planning_plan)
            goal_analysis = self._goal_service.analyze(reasoning_plan, planning_plan, decision_analysis)
        else:
            memories = self._memory_resolver.resolve(question) if self._memory_resolver else ()
            reasoning_plan = self._reasoning_service.plan(question, memories, context)
            planning_plan = self._planning_service.plan(reasoning_plan)
            decision_analysis = self._decision_service.analyze(reasoning_plan, planning_plan)
            goal_analysis = self._goal_service.analyze(reasoning_plan, planning_plan, decision_analysis)
            answer = self._chat.send_message(self._prompt.build(intent.question, context, conflicts), history, memories, reasoning_plan, planning_plan, decision_analysis, goal_analysis, project_context)
            answer, valid = self._citations.validate(answer, context)
            if not valid: answer = "Sufficient supporting evidence was not found in local documents."
        quality = self._confidence.evaluate(context, valid, conflicts)
        snapshots = [
            CitationSnapshot(
                citation_id=item.citation_id, document_id=item.document_id, file_name=item.file_name,
                source_path=item.source_path, source_locator=item.source_locator, excerpt=item.content[:500],
                excerpt_hash=sha256(item.content[:500].encode("utf-8")).hexdigest(), confidence=max(0.0, min(1.0, item.score)),
            )
            for item in valid[:MAX_CITATIONS_PER_MESSAGE]
        ]
        self._conversations.complete_turn(conversation.id, answer, snapshots)
        return self._build_response(
            answer=answer,
            valid=valid,
            quality=quality,
            conversation=conversation,
            records=records,
            context=context,
            duplicates=duplicates,
            filtered=filtered,
            conflicts=conflicts,
            queries=queries,
            memories=memories,
            reasoning_plan=reasoning_plan,
            planning_plan=planning_plan,
            decision_analysis=decision_analysis,
            goal_analysis=goal_analysis,
        )