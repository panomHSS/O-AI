import re
from hashlib import sha256
from uuid import UUID
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge_answer import CitationResponse, ConflictResponse, KnowledgeAnswerResponse, RetrievalSummaryResponse
from app.services.chat import ChatService
from app.contracts.command import CommandRequest
from app.services.ai_runtime import AIRuntime
from app.services.command_orchestrator import CommandOrchestrationFailure
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
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
from app.pipeline.retrieval import RetrievalPipeline
from app.pipeline.components import RetrievalComponents

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
        retrieval_pipeline: RetrievalPipeline | None = None,
        execution_planner: ExecutionPlanner | None = None,
        execution_guard: ExecutionGuard | None = None,
        ai_runtime: AIRuntime | None = None,
        error_normalizer: OrchestrationErrorNormalizer | None = None,
        response_composer: ResponseComposer | None = None,
    ) -> None:

        self._repository = repository
        self._conversations = conversations
        self._chat = chat

        self._analyzer = analyzer
        self._planner = planner
        self._ranker = ranker
        self._conflicts = conflict_detector
        self._context = context_builder

        self._prompt = prompt_builder
        self._citations = citations
        self._confidence = confidence

        self._candidates_per_query = candidates_per_query
        self._selected_limit = selected_limit

        self._memory_resolver = memory_resolver

        self._reasoning_service = reasoning_service or ReasoningService()
        self._planning_service = planning_service or PlanningService()
        self._decision_service = decision_service or DecisionService()
        self._goal_service = goal_service or GoalService()

        self._orchestrator = orchestrator
        self._retrieval_pipeline = retrieval_pipeline

        execution_presence = (
            execution_planner is not None,
            execution_guard is not None,
            ai_runtime is not None,
        )
        if any(execution_presence) and not all(execution_presence):
            raise ValueError(
                "Grounded AI execution requires planner, guard, and runtime together."
            )

        self._execution_planner = execution_planner
        self._execution_guard = execution_guard
        self._ai_runtime = ai_runtime
        self._normalize_ai_execution_failures = all(execution_presence)
        self._error_normalizer = (
            error_normalizer or OrchestrationErrorNormalizer()
        )
        self._response_composer = (
            response_composer
            or ResponseComposer(self._error_normalizer)
        )

    def _create_execution_context(
        self,
        *,
        request_id: str,
        question: str,
        conversation,
        history,
        project_context,
    ) -> ExecutionContext:
        return ExecutionContext(
            request=RequestContext(
                request_id=request_id,
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
        execution_context: ExecutionContext,
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
            answer=execution_context.response.answer,
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

    def answer(
        self,
        question: str,
        conversation_id: UUID | None,
        project_id: UUID | None = None,
        *,
        request_id: str | None = None,
    ) -> KnowledgeAnswerResponse:
        correlation_id = request_id or str(uuid4())
        conversation, history = self._conversations.begin_turn(
            question,
            conversation_id,
            project_id,
        )
        project_context = self._conversations.resolve_project_context(conversation)
        execution_context = self._create_execution_context(
            request_id=correlation_id,
            question=question,
            conversation=conversation,
            history=history,
            project_context=project_context,
        )
        if self._orchestrator is not None:

            self._orchestrator.execute(
                execution_context,
            )

            (
                intent,
                queries,
                records,
                selected,
                duplicates,
                filtered,
                conflicts,
                context,
            ) = self._read_knowledge(
                execution_context,
            )
        else:
            if self._retrieval_pipeline is not None:
                self._retrieval_pipeline.execute(
                    execution_context,
                )

                (
                    intent,
                    queries,
                    records,
                    selected,
                    duplicates,
                    filtered,
                    conflicts,
                    context,
                ) = self._read_knowledge(
                    execution_context,
                )

            else:
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

                self._write_knowledge(
                    execution_context,
                    intent=intent,
                    queries=queries,
                    records=records,
                    evidence=selected,
                    duplicates_removed=duplicates,
                    filtered_out=filtered,
                    conflicts=conflicts,
                    context=context,
                )

        if not context:
            (
                answer,
                valid,
                quality,
                snapshots,
                memories,
            ) = self._handle_no_context(
                execution_context=execution_context,
                conflicts=conflicts,
            )

            answer = "Sufficient supporting evidence was not found in local documents."
            execution_context.response.answer = answer
            valid = []

            quality = self._evaluate_confidence(
                context=context,
                valid=valid,
                conflicts=conflicts,
            )

            snapshots = []
        else:
            (
                answer,
                valid,
                quality,
                snapshots,
                memories,
            ) = self._handle_grounded_response(
                execution_context=execution_context,
                question=question,
                history=history,
                project_context=project_context,
                intent=intent,
                context=context,
                conflicts=conflicts,
            )
        self._conversations.complete_turn(conversation.id, answer, snapshots)
        return self._build_response(
            execution_context=execution_context,
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
            reasoning_plan=execution_context.intelligence.reasoning,
            planning_plan=execution_context.intelligence.planning,
            decision_analysis=execution_context.intelligence.decision,
            goal_analysis=execution_context.intelligence.goals,
        )

    def _build_intelligence_analysis(
        self,
        execution_context: ExecutionContext,
    ):
        question = execution_context.request.question
        memories = execution_context.conversation.memories
        context = execution_context.knowledge.context
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
        execution_context.intelligence.reasoning = (
            reasoning_plan
        )
        execution_context.intelligence.planning = (
            planning_plan
        )
        execution_context.intelligence.decision = (
            decision_analysis
        )
        execution_context.intelligence.goals = (
            goal_analysis
        )

    def _handle_no_context(
        self,
        *,
        execution_context: ExecutionContext,
        conflicts,
    ):
        memories = ()

        self._build_intelligence_analysis(
            execution_context,
        )

        answer = "Sufficient supporting evidence was not found in local documents."
        execution_context.response.answer = answer

        valid = []

        quality = self._evaluate_confidence(
            context=execution_context.knowledge.context,
            valid=valid,
            conflicts=conflicts,
        )

        snapshots = []

        return (
            answer,
            valid,
            quality,
            snapshots,
            memories,
        )

    def _handle_grounded_response(
        self,
        *,
        execution_context: ExecutionContext,
        question: str,
        history,
        project_context,
        intent,
        context,
        conflicts,
    ):

        memories = (
            self._memory_resolver.resolve(question)
            if self._memory_resolver
            else ()
        )
        execution_context.conversation.memories = list(memories)
        
        self._build_intelligence_analysis(
            execution_context,
        )            
        answer = self._generate_chat_response(
            execution_context=execution_context,
            question=question,
            intent=intent,
            context=context,
            conflicts=conflicts,
            history=history,
            memories=memories,
            reasoning_plan=execution_context.intelligence.reasoning,
            planning_plan=execution_context.intelligence.planning,
            decision_analysis=execution_context.intelligence.decision,
            goal_analysis=execution_context.intelligence.goals,
            project_context=project_context,
        )
        execution_context.response.answer = answer

        answer, valid = self._citations.validate(answer, context)
        if not valid:
            answer = (
                "Sufficient supporting evidence was not found in local documents."
            )
        execution_context.response.answer = answer
        quality = self._evaluate_confidence(
            context=context,
            valid=valid,
            conflicts=conflicts,
        )
        snapshots = self._create_citation_snapshots(
            valid=valid,
        )            

        return (
            answer,
            valid,
            quality,
            snapshots,
            memories,
        )

    def _generate_chat_response(
        self,
        *,
        execution_context: ExecutionContext,
        question: str,
        intent,
        context,
        conflicts,
        history,
        memories,
        reasoning_plan,
        planning_plan,
        decision_analysis,
        goal_analysis,
        project_context,
    ) -> str:
        self._ensure_ai_execution_boundary()

        assert self._execution_planner is not None
        assert self._execution_guard is not None
        assert self._ai_runtime is not None

        command = CommandRequest(
            request_id=execution_context.request.request_id,
            command="chat.message",
            arguments={
                "message": question,
                "conversation_id": execution_context.request.conversation_id,
                "project_id": execution_context.request.project_id,
            },
        )

        try:
            planning = self._execution_planner.plan(command)
            planning_error = (
                self._error_normalizer.normalize_execution_planning(
                    planning
                )
            )
            if planning_error is not None:
                raise CommandOrchestrationFailure(
                    self._response_composer.compose_error(
                        planning_error
                    )
                )

            authorization = self._execution_guard.authorize(
                command,
                planning,
            )
            authorization_error = (
                self._error_normalizer.normalize_execution_authorization(
                    authorization
                )
            )
            if authorization_error is not None:
                raise CommandOrchestrationFailure(
                    self._response_composer.compose_error(
                        authorization_error
                    )
                )

            authorized_adapter = self._ai_runtime.bind(
                command,
                authorization,
            )
            return self._chat.send_message(
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
                ai_adapter=authorized_adapter,
            )
        except CommandOrchestrationFailure:
            raise
        except Exception as error:
            if not self._normalize_ai_execution_failures:
                raise
            normalized = self._error_normalizer.normalize_exception(
                command.request_id,
                error,
            )
            raise CommandOrchestrationFailure(
                self._response_composer.compose_error(
                    normalized
                )
            ) from error

    def _ensure_ai_execution_boundary(self) -> None:
        if (
            self._execution_planner is not None
            and self._execution_guard is not None
            and self._ai_runtime is not None
        ):
            return

        from app.services.adapter_registry import AdapterRegistry
        from app.services.ai_capability_model_discovery import (
            AICapabilityModelDiscovery,
        )
        from app.services.ai_discovery_sources import (
            ChatGPTConfiguredModelDiscoverySource,
        )
        from app.services.ai_provider_routing import (
            AIProviderRoutingPolicy,
        )
        from app.services.ai_router import AIRouter
        from app.services.capability_permission_policy import (
            CapabilityPermissionPolicy,
        )
        from app.services.command_decision_engine import (
            CommandDecisionEngine,
        )

        default_adapter = self._chat.default_ai_adapter()
        registry = AdapterRegistry((default_adapter,))
        policy = AIProviderRoutingPolicy(
            default_adapter_id=default_adapter.adapter_id,
            enabled_adapter_ids=frozenset(
                {default_adapter.adapter_id}
            ),
        )
        router = AIRouter(
            registry=registry,
            policy=policy,
        )
        discovery = AICapabilityModelDiscovery(
            registry=registry,
            sources=(
                ChatGPTConfiguredModelDiscoverySource(
                    configured_model_id="provider-managed",
                    adapter_id=default_adapter.adapter_id,
                ),
            ),
        )
        permission_policy = CapabilityPermissionPolicy(
            registry=registry,
            permissions=(),
        )

        self._execution_planner = ExecutionPlanner(
            registry=registry,
            decision_engine=CommandDecisionEngine(),
            ai_router=router,
            ai_discovery=discovery,
            permission_policy=permission_policy,
        )
        self._execution_guard = ExecutionGuard(
            registry=registry,
            permission_policy=permission_policy,
        )
        self._ai_runtime = AIRuntime(
            registry=registry,
        )

    def _validate_grounding(
        self,
        *,
        answer: str,
        context,
    ) -> tuple[str, list]:
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
        )
    
    def _evaluate_confidence(
        self,
        *,
        context,
        valid,
        conflicts,
    ):
        return self._confidence.evaluate(
            context,
            valid,
            conflicts,
        )

    def _create_citation_snapshots(
        self,
        *,
        valid,
    ):
        return [
            CitationSnapshot(
                citation_id=item.citation_id,
                document_id=item.document_id,
                file_name=item.file_name,
                source_path=item.source_path,
                source_locator=item.source_locator,
                excerpt=item.content[:500],
                excerpt_hash=sha256(
                    item.content[:500].encode("utf-8")
                ).hexdigest(),
                confidence=max(
                    0.0,
                    min(
                        1.0,
                        item.score,
                    ),
                ),
            )
            for item in valid[:MAX_CITATIONS_PER_MESSAGE]
        ]

    def _read_knowledge(
        self,
        execution_context: ExecutionContext,
    ):
        knowledge = execution_context.knowledge

        return (
            knowledge.intent,
            knowledge.queries,
            knowledge.records,
            knowledge.evidence,
            knowledge.duplicates_removed,
            knowledge.filtered_out,
            knowledge.conflicts,
            knowledge.context,
        )

    def _write_knowledge(
        self,
        execution_context: ExecutionContext,
        *,
        intent,
        queries,
        records,
        evidence,
        duplicates_removed,
        filtered_out,
        conflicts,
        context,
    ) -> None:
        """Populate the knowledge context."""

        knowledge = execution_context.knowledge

        knowledge.intent = intent
        knowledge.queries = queries
        knowledge.records = records
        knowledge.evidence = evidence
        knowledge.duplicates_removed = duplicates_removed
        knowledge.filtered_out = filtered_out
        knowledge.conflicts = conflicts
        knowledge.context = context