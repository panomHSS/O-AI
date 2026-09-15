from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.dependencies import (
    get_chat_action_bridge,
    get_command_input_pipeline,
    get_command_orchestrator,
    get_project_update_turn_orchestrator,
)
from app.schemas.api import ApiSuccess
from app.schemas.chat import (
    ChatActionResponse,
    ChatRequest,
    ChatResponse,
    MemoryUsageResponse,
)
from app.schemas.execution_approvals import (
    ExecutionApprovalProposalResponse,
)
from app.services.chat_action_bridge import ChatActionBridge
from app.services.command_input_pipeline import CommandInputPipeline
from app.services.command_orchestrator import (
    CommandOrchestrator,
    CommandOrchestrationFailure,
)
from app.services.project_update_orchestrator import (
    ProjectUpdateTurnInput,
    ProjectUpdateTurnOrchestrator,
)

router = APIRouter(prefix="/chat", tags=["chat"])

LOCAL_REQUEST_HEADER_VALUE = "1"


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
    command_orchestrator: Annotated[
        CommandOrchestrator,
        Depends(get_command_orchestrator),
    ],
    project_update_orchestrator: Annotated[
        ProjectUpdateTurnOrchestrator,
        Depends(get_project_update_turn_orchestrator),
    ],
    chat_action_bridge: Annotated[
        ChatActionBridge,
        Depends(get_chat_action_bridge),
    ],
    x_oai_local_request: Annotated[
        str | None,
        Header(),
    ] = None,
) -> ApiSuccess[ChatResponse]:
    """Handle normal chat or one explicit owner-reviewed /action turn."""

    if (
        chat_action_bridge.is_action_directive(payload.message)
        or chat_action_bridge.is_plugin_action_request(payload.message)
    ):
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            )

        action_outcome = chat_action_bridge.process(
            message=payload.message,
            conversation_id=payload.conversation_id,
            project_id=payload.project_id,
        )
        approval = (
            ExecutionApprovalProposalResponse.from_outcome(
                action_outcome.approval
            )
            if action_outcome.approval is not None
            else None
        )
        return ApiSuccess(
            data=ChatResponse(
                reply=action_outcome.reply,
                conversation_id=action_outcome.conversation_id,
                action=ChatActionResponse(
                    status=action_outcome.status,
                    reason_code=action_outcome.reason_code,
                    approval=approval,
                ),
            )
        )

    command = command_input_pipeline.normalize_chat(
        request_id=request.state.request_id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
    )
    outcome = command_orchestrator.process_chat(command)
    if outcome.chat_turn is None:
        raise CommandOrchestrationFailure(outcome.response)
    result = outcome.chat_turn

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
