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
from app.repositories.message_citations import CitationSnapshot, MAX_CITATIONS_PER_MESSAGE
from app.services.knowledge_intelligence import CitationEngine, ConfidenceEvaluator, ConflictDetector, ContextBuilder, Evidence, EvidenceRanker, GroundedPromptBuilder, IntentAnalyzer, RetrievalPlanner

class KnowledgeAnswerService:
    def __init__(self, repository: KnowledgeRepository, conversations: ConversationService, chat: ChatService, analyzer: IntentAnalyzer, planner: RetrievalPlanner, ranker: EvidenceRanker, conflict_detector: ConflictDetector, context_builder: ContextBuilder, prompt_builder: GroundedPromptBuilder, citations: CitationEngine, confidence: ConfidenceEvaluator, candidates_per_query: int, selected_limit: int, memory_resolver: MemoryResolver | None = None, reasoning_service: ReasoningService | None = None, planning_service: PlanningService | None = None, decision_service: DecisionService | None = None) -> None:
        self._repository, self._conversations, self._chat = repository, conversations, chat
        self._analyzer, self._planner, self._ranker, self._conflicts = analyzer, planner, ranker, conflict_detector
        self._context, self._prompt, self._citations, self._confidence = context_builder, prompt_builder, citations, confidence
        self._candidates_per_query, self._selected_limit = candidates_per_query, selected_limit
        self._memory_resolver = memory_resolver
        self._reasoning_service = reasoning_service or ReasoningService()
        self._planning_service = planning_service or PlanningService()
        self._decision_service = decision_service or DecisionService()
    def answer(self, question: str, conversation_id: UUID | None) -> KnowledgeAnswerResponse:
        conversation, history = self._conversations.begin_turn(question, conversation_id)
        intent = self._analyzer.analyze(question); queries = self._planner.plan(intent)
        records = []; seen = set()
        for query in queries:
            terms = re.findall(r"[\w\u0E00-\u0E7F]+", query)
            if not terms:
                continue
            for item in self._repository.search(" AND ".join(f'"{term}"' for term in terms), self._candidates_per_query):
                if item["chunk_id"] not in seen: records.append(item); seen.add(item["chunk_id"])
        selected, duplicates, filtered = self._ranker.rank(intent.question, intent.important_terms, records)
        selected = [Evidence(**{**item.__dict__, "citation_id": f"S{index}"}) for index, item in enumerate(selected[:self._selected_limit], 1)]
        conflicts = self._conflicts.detect(selected, intent.important_terms); context = self._context.build(selected)
        if not context:
            answer = "Sufficient supporting evidence was not found in local documents."
            valid = []
            memories = ()
            reasoning_plan = self._reasoning_service.plan(question, memories, context)
            planning_plan = self._planning_service.plan(reasoning_plan)
            decision_analysis = self._decision_service.analyze(reasoning_plan, planning_plan)
        else:
            memories = self._memory_resolver.resolve(question) if self._memory_resolver else ()
            reasoning_plan = self._reasoning_service.plan(question, memories, context)
            planning_plan = self._planning_service.plan(reasoning_plan)
            decision_analysis = self._decision_service.analyze(reasoning_plan, planning_plan)
            answer = self._chat.send_message(self._prompt.build(intent.question, context, conflicts), history, memories, reasoning_plan, planning_plan, decision_analysis)
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
        return KnowledgeAnswerResponse(answer=answer, citations=[CitationResponse(id=item.citation_id, document_id=UUID(item.document_id), file_name=item.file_name, source_path=item.source_path, source_locator=item.source_locator, excerpt=item.content[:500]) for item in valid], evidence_quality=quality, conversation_id=UUID(conversation.id), retrieval_summary=RetrievalSummaryResponse(candidates_considered=len(records), evidence_selected=len(context), duplicates_removed=duplicates, filtered_out=filtered, conflicting_evidence_count=len(conflicts), queries_used=queries), conflicts=[ConflictResponse(citations=list(item.citation_ids), reason=item.reason) for item in conflicts], memories_used=[{"memory_id": item.memory_id, "version": item.version, "key": item.key} for item in memories], reasoning_plan=reasoning_plan, planning_plan=planning_plan, decision_analysis=decision_analysis)
