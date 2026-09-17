from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.dependencies import (
    get_chat_action_bridge,
    get_calendar_write_chat_service,
    get_cross_connector_chat_service,
    get_runtime_capability_chat_service,
    get_command_input_pipeline,
    get_command_orchestrator,
    get_project_update_turn_orchestrator,
)
from app.db.verification import TARGET_REVISION
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
from app.services.chat_calendar_write import CalendarWriteChatService
from app.services.chat_cross_connector import CrossConnectorChatService
from app.services.chat_runtime_capability import RuntimeCapabilityChatService
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
    cross_connector_chat_service: Annotated[
        CrossConnectorChatService,
        Depends(get_cross_connector_chat_service),
    ],
    calendar_write_chat_service: CalendarWriteChatService = Depends(
        get_calendar_write_chat_service
    ),
    runtime_capability_chat_service: RuntimeCapabilityChatService = Depends(
        get_runtime_capability_chat_service
    ),
    x_oai_local_request: Annotated[
        str | None,
        Header(),
    ] = None,
) -> ApiSuccess[ChatResponse]:
    """Handle normal chat or one explicit owner-reviewed /action turn."""

    if cross_connector_chat_service.is_request(payload.message):
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if payload.conversation_id is None or payload.project_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        cross_outcome = cross_connector_chat_service.process(
            request_id=request.state.request_id, message=payload.message,
            conversation_id=payload.conversation_id,
        )
        return ApiSuccess(data=ChatResponse(
            reply=cross_outcome.reply, conversation_id=cross_outcome.conversation_id,
        ))

    clarification_classifier = getattr(
        chat_action_bridge,
        "calendar_clarification_disposition",
        None,
    )
    clarification_disposition = (
        clarification_classifier(
            payload.conversation_id,
            payload.message,
        )
        if callable(clarification_classifier)
        else "none"
    )
    if clarification_disposition == "handle":
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if payload.conversation_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        action_outcome = chat_action_bridge.process_calendar_clarification(
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
    if clarification_disposition == "clear":
        chat_action_bridge.clear_calendar_clarification(
            payload.conversation_id
        )

    # D81 acceptance remediation: reserve exact bounded runtime-status
    # phrases before broad Plugin signal detection. This classification is
    # side-effect free and grants no action or execution authority.
    runtime_status_classifier = getattr(
        runtime_capability_chat_service,
        "is_request",
        None,
    )
    runtime_status_requested = (
        callable(runtime_status_classifier)
        and runtime_status_classifier(payload.message)
    )

    # D83 reserves bounded Calendar mutation intent before broad Action/Plugin
    # classification.  This parser is deterministic/local-only and creates no
    # D73 proposal, authorization, credential access, network call, or write.
    calendar_write_classifier = getattr(
        calendar_write_chat_service,
        "is_request",
        None,
    )
    calendar_write_requested = (
        not runtime_status_requested
        and callable(calendar_write_classifier)
        and calendar_write_classifier(payload.message)
    )

    if (
        not runtime_status_requested
        and not calendar_write_requested
        and (
            chat_action_bridge.is_action_directive(payload.message)
            or chat_action_bridge.is_plugin_action_request(payload.message)
        )
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

    plaintext_calendar_approval_guard = getattr(
        chat_action_bridge,
        "is_pending_calendar_plaintext_approval",
        None,
    )
    if (
        callable(plaintext_calendar_approval_guard)
        and plaintext_calendar_approval_guard(
            payload.conversation_id,
            payload.message,
        )
    ):
        if payload.conversation_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST
            )
        guard_processor = getattr(
            chat_action_bridge,
            "process_pending_calendar_plaintext_approval",
            None,
        )
        if not callable(guard_processor):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        action_outcome = guard_processor(
            message=payload.message,
            conversation_id=payload.conversation_id,
            project_id=payload.project_id,
        )
        return ApiSuccess(
            data=ChatResponse(
                reply=action_outcome.reply,
                conversation_id=action_outcome.conversation_id,
                action=ChatActionResponse(
                    status=action_outcome.status,
                    reason_code=action_outcome.reason_code,
                    approval=None,
                ),
            )
        )

    calendar_write_guard_classifier = getattr(
        calendar_write_chat_service,
        "pending_plaintext_approval_disposition",
        None,
    )
    calendar_write_guard_disposition = (
        calendar_write_guard_classifier(
            conversation_id=payload.conversation_id,
            message=payload.message,
        )
        if callable(calendar_write_guard_classifier)
        else "none"
    )
    if calendar_write_guard_disposition == "block":
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            )
        if payload.conversation_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST
            )
        guard_processor = getattr(
            calendar_write_chat_service,
            "process_pending_plaintext_approval_turn",
            None,
        )
        if not callable(guard_processor):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        calendar_write_outcome = guard_processor(
            message=payload.message,
            conversation_id=payload.conversation_id,
            project_id=payload.project_id,
        )
        return ApiSuccess(
            data=ChatResponse(
                reply=calendar_write_outcome.reply,
                conversation_id=(
                    calendar_write_outcome.conversation_id
                ),
            )
        )

    if calendar_write_requested:
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            )
        calendar_write_processor = getattr(
            calendar_write_chat_service,
            "process_chat_turn",
            None,
        )
        if not callable(calendar_write_processor):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        calendar_write_outcome = calendar_write_processor(
            message=payload.message,
            conversation_id=payload.conversation_id,
            project_id=payload.project_id,
        )
        return ApiSuccess(
            data=ChatResponse(
                reply=calendar_write_outcome.reply,
                conversation_id=(
                    calendar_write_outcome.conversation_id
                ),
            )
        )

    if runtime_status_requested:
        if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            )
        revision = getattr(
            request.app.state,
            "database_revision",
            TARGET_REVISION,
        )
        runtime_outcome = runtime_capability_chat_service.process(
            message=payload.message,
            conversation_id=payload.conversation_id,
            project_id=payload.project_id,
            database_revision=revision,
        )
        return ApiSuccess(
            data=ChatResponse(
                reply=runtime_outcome.reply,
                conversation_id=runtime_outcome.conversation_id,
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
