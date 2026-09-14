"""D29 coordination of selected AI turns and guarded Tool/Module execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.command import CommandRequest, Response
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.response_composition import NormalizedError
from app.services.ai_adapter_registry import AIAdapterRegistry
from app.services.ai_router import AIRouter
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.conversations import ChatTurnResult, ConversationService
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
from app.services.tool_module_router import ToolModuleRouter


@dataclass(frozen=True, slots=True)
class CommandOrchestrationOutcome:
    """One D29 response and its chat turn when a chat command succeeded."""

    response: Response
    chat_turn: ChatTurnResult | None = None


class CommandOrchestrationFailure(Exception):
    """Carries only a normalized, safe terminal response to the API boundary."""

    def __init__(self, response: Response) -> None:
        self.response = response
        super().__init__(response.result.error or "INTERNAL_ERROR")


class CommandOrchestrator:
    """Coordinate D21-D28 contracts without embedding provider-specific logic."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        decision_engine: CommandDecisionEngine,
        ai_router: AIRouter,
        ai_adapters: AIAdapterRegistry,
        error_normalizer: OrchestrationErrorNormalizer,
        response_composer: ResponseComposer,
        tool_module_router: ToolModuleRouter,
    ) -> None:
        self._conversation_service = conversation_service
        self._decision_engine = decision_engine
        self._ai_router = ai_router
        self._ai_adapters = ai_adapters
        self._error_normalizer = error_normalizer
        self._response_composer = response_composer
        self._tool_module_router = tool_module_router

    def process_chat(self, command: CommandRequest) -> CommandOrchestrationOutcome:
        """Run one validated chat command through its selected AI adapter once."""
        try:
            message, conversation_id, project_id = (
                CommandInputPipeline.validated_chat_arguments(command)
            )
            if command.command != "chat.message":
                return self._error("AI_ROUTE_REJECTED", command.request_id)
            decision = self._decision_engine.decide(command)
            route = self._ai_router.route(decision)
            route_error = self._error_normalizer.normalize_ai_route(route)
            if route_error is not None:
                return self._normalized(route_error)
            adapter = self._ai_adapters.resolve(route.adapter_id or "")
            if adapter is None:
                return self._error("AI_ROUTE_UNAVAILABLE", command.request_id)
            turn = self._conversation_service.send_message(
                message,
                conversation_id,
                project_id,
                ai_adapter=adapter,
            )
            return CommandOrchestrationOutcome(
                response=self._response_composer.compose_ai_success(
                    command.request_id,
                    self._to_ai_result(turn.reply),
                ),
                chat_turn=turn,
            )
        except self._preserved_domain_errors():
            raise
        except Exception as error:
            return self._normalized(
                self._error_normalizer.normalize_exception(command.request_id, error)
            )

    def execute_tool(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> Response:
        'Execute one Tool adapter only from a D36 authorized plan.'
        authorization_error = (
            self._error_normalizer.normalize_execution_authorization(
                authorization
            )
        )
        if authorization_error is not None:
            return self._normalized(authorization_error).response
        if (
            authorization.target_kind != "tool"
            or authorization.execution_plan is None
        ):
            return self._error(
                "EXECUTION_AUTHORIZATION_REJECTED",
                request.request_id,
            ).response

        plan = authorization.execution_plan
        route = self._tool_module_router.route(request, plan)
        route_error = self._error_normalizer.normalize_tool_route(route)
        if route_error is not None:
            return self._normalized(route_error).response
        adapter = self._tool_module_router.get_adapter(route.adapter_id or "")
        if adapter is None:
            return self._error(
                "TOOL_ROUTE_UNAVAILABLE",
                request.request_id,
            ).response
        try:
            return self._response_composer.compose_tool_result(
                adapter.execute(request, plan)
            )
        except Exception as error:
            return self._normalized(
                self._error_normalizer.normalize_exception(
                    request.request_id,
                    error,
                )
            ).response
    def _normalized(self, error: NormalizedError) -> CommandOrchestrationOutcome:
        return CommandOrchestrationOutcome(self._response_composer.compose_error(error))

    def _error(self, code: str, request_id: str) -> CommandOrchestrationOutcome:
        return self._normalized(
            NormalizedError(request_id, code, "failed")  # type: ignore[arg-type]
        )

    @staticmethod
    def _to_ai_result(content: str):
        from app.contracts.ai import AIResult

        return AIResult(content=content)

    @staticmethod
    def _preserved_domain_errors():
        """Keep existing conversation/project API semantics outside D28 outcomes."""
        from app.services.conversations import (
            ConversationAssociationError,
            ConversationNotFoundError,
        )
        from app.services.project_context import ProjectContextUnavailableError
        from app.services.projects import ProjectNotFoundError

        return (
            ConversationAssociationError,
            ConversationNotFoundError,
            ProjectContextUnavailableError,
            ProjectNotFoundError,
        )
