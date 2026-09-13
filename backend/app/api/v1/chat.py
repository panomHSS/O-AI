from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import (
    get_command_input_pipeline,
    get_project_update_turn_orchestrator,
)
from app.schemas.api import ApiSuccess
from app.schemas.chat import ChatRequest, ChatResponse, MemoryUsageResponse
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.project_update_orchestrator import (
    ProjectUpdateTurnInput,
    ProjectUpdateTurnOrchestrator,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ApiSuccess[ChatResponse],
    status_code=status.HTTP_200_OK,
)
def send_chat_message(
    request: Request,
    payload: ChatRequest,
    command_input_pipeline: Annotated[
        CommandInputPipeline,
        Depends(get_command_input_pipeline),
    ],
    project_update_orchestrator: Annotated[
        ProjectUpdateTurnOrchestrator,
        Depends(get_project_update_turn_orchestrator),
    ],
) -> ApiSuccess[ChatResponse]:
    """Handle a chat turn through the narrow D22 input boundary."""
    command = command_input_pipeline.normalize_chat(
        request_id=request.state.request_id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
    )
    result = command_input_pipeline.process_chat(command)

    project_update_proposal = None

    if (
        result.project_id is not None
        and result.project_context is not None
    ):
        project_update_proposal = project_update_orchestrator.process(
            ProjectUpdateTurnInput(
                conversation_id=result.conversation_id,
                project_id=result.project_id,
                base_revision=result.project_context.current_revision,
                user_message=payload.message,
                assistant_reply=result.reply,
                project_context=result.project_context,
            )
        )

    return ApiSuccess(
        data=ChatResponse(
            reply=result.reply,
            conversation_id=result.conversation_id,
            project_update_proposal=project_update_proposal,
            project_action_analysis=result.project_action_analysis,
            project_action_plan=result.project_action_plan,
            project_action_execution_proposal=(
                result.project_action_execution_proposal
            ),
            memories_used=[
                MemoryUsageResponse(
                    memory_id=item.memory_id,
                    version=item.version,
                    key=item.key,
                )
                for item in result.memories_used
            ],
            reasoning_plan=result.reasoning_plan,
            planning_plan=result.planning_plan,
            decision_analysis=result.decision_analysis,
            goal_analysis=result.goal_analysis,
        )
    )
