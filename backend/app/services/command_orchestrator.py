"""D49 normal-chat orchestration over the unified AI execution boundary."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.ai import AIResult
from app.contracts.command import CommandRequest, Response
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.response_composition import NormalizedError
from app.services.ai_runtime import AIRuntime
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.conversations import ChatTurnResult, ConversationService
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer
from app.services.response_composer import ResponseComposer
from app.services.tool_runtime import ToolRuntime


@dataclass(frozen=True, slots=True)
class CommandOrchestrationOutcome:
    response: Response
    chat_turn: ChatTurnResult | None = None


class CommandOrchestrationFailure(Exception):
    def __init__(self, response: Response) -> None:
        self.response = response
        super().__init__(response.result.error or "INTERNAL_ERROR")


class CommandOrchestrator:
    """Coordinate normal chat without owning AI routing or execution authority."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        planner: ExecutionPlanner,
        guard: ExecutionGuard,
        ai_runtime: AIRuntime,
        error_normalizer: OrchestrationErrorNormalizer,
        response_composer: ResponseComposer,
        tool_runtime: ToolRuntime,
    ) -> None:
        self._conversation_service = conversation_service
        self._planner = planner
        self._guard = guard
        self._ai_runtime = ai_runtime
        self._error_normalizer = error_normalizer
        self._response_composer = response_composer
        self._tool_runtime = tool_runtime

    def process_chat(self, command: CommandRequest) -> CommandOrchestrationOutcome:
        try:
            message, conversation_id, project_id = (
                CommandInputPipeline.validated_chat_arguments(command)
            )
            if command.command != "chat.message":
                return self._error("AI_ROUTE_REJECTED", command.request_id)

            planning = self._planner.plan(command)
            planning_error = self._error_normalizer.normalize_execution_planning(
                planning
            )
            if planning_error is not None:
                return self._normalized(planning_error)

            authorization = self._guard.authorize(command, planning)
            authorization_error = (
                self._error_normalizer.normalize_execution_authorization(
                    authorization
                )
            )
            if authorization_error is not None:
                return self._normalized(authorization_error)

            authorized_adapter = self._ai_runtime.bind(
                command,
                authorization,
            )
            turn = self._conversation_service.send_context_message(
                message,
                conversation_id,
                project_id,
                ai_adapter=authorized_adapter,
            )
            return CommandOrchestrationOutcome(
                response=self._response_composer.compose_ai_success(
                    command.request_id,
                    AIResult(content=turn.reply),
                ),
                chat_turn=turn,
            )
        except self._preserved_domain_errors():
            raise
        except Exception as error:
            return self._normalized(
                self._error_normalizer.normalize_exception(
                    command.request_id,
                    error,
                )
            )

    def execute_tool(
        self,
        request: CommandRequest,
        authorization: ExecutionAuthorization,
    ) -> Response:
        authorization_error = (
            self._error_normalizer.normalize_execution_authorization(
                authorization
            )
        )
        if authorization_error is not None:
            return self._normalized(authorization_error).response

        result = self._tool_runtime.execute(request, authorization)
        return self._response_composer.compose_tool_result(result)

    def _normalized(
        self,
        error: NormalizedError,
    ) -> CommandOrchestrationOutcome:
        return CommandOrchestrationOutcome(
            self._response_composer.compose_error(error)
        )

    def _error(
        self,
        code: str,
        request_id: str,
    ) -> CommandOrchestrationOutcome:
        return self._normalized(
            NormalizedError(
                request_id,
                code,  # type: ignore[arg-type]
                "failed",
            )
        )

    @staticmethod
    def _preserved_domain_errors():
        from app.services.conversations import (
            ConversationAssociationError,
            ConversationNotFoundError,
        )
        from app.services.project_context import (
            ProjectContextUnavailableError,
        )
        from app.services.projects import ProjectNotFoundError

        return (
            ConversationAssociationError,
            ConversationNotFoundError,
            ProjectContextUnavailableError,
            ProjectNotFoundError,
        )
