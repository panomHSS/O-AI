from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_calendar_write_chat_ux_service,
    get_conversation_service,
)
from app.api.v1.calendar_write_approvals import (
    require_local_calendar_write_request_marker,
)
from app.schemas.api import ApiSuccess
from app.schemas.calendar_write_chat import (
    CalendarWriteChatDecisionRequest,
    CalendarWriteChatDecisionResponse,
)
from app.services.calendar_write_approval import CalendarWriteApprovalError
from app.services.calendar_write_chat_ux import (
    CalendarWriteChatUXError,
    CalendarWriteChatUXService,
)
from app.services.conversations import ConversationService


router = APIRouter(
    prefix="/calendar-write-chat",
    tags=["calendar-write-chat"],
)


def _complete_original_conversation(
    *,
    conversation_service: ConversationService,
    outcome,
) -> None:
    try:
        conversation_service.complete_turn(
            str(outcome.conversation_id),
            outcome.reply,
        )
    except Exception as error:
        # Binding is already terminal/consumed; retry cannot grant D74 again.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="calendar_write_chat_completion_failed",
        ) from error


def _decision_error(error: Exception) -> HTTPException:
    reason_code = getattr(
        error,
        "reason_code",
        "calendar_write_chat_decision_rejected",
    )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(reason_code),
    )


def _require_original_conversation_scope(
    *,
    approval_id: str,
    write_digest: str,
    service: CalendarWriteChatUXService,
    conversation_service: ConversationService,
) -> None:
    """Verify request-workspace ownership before consuming decision authority."""
    binding = service.decision_binding(
        approval_id=approval_id,
        write_digest=write_digest,
    )
    conversation_service.get_conversation(binding.conversation_id)


@router.post(
    "/{approval_id}/deny",
    response_model=ApiSuccess[CalendarWriteChatDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_calendar_write_chat(
    approval_id: str,
    payload: CalendarWriteChatDecisionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    service: Annotated[
        CalendarWriteChatUXService,
        Depends(get_calendar_write_chat_ux_service),
    ],
    conversation_service: Annotated[
        ConversationService,
        Depends(get_conversation_service),
    ],
) -> ApiSuccess[CalendarWriteChatDecisionResponse]:
    try:
        _require_original_conversation_scope(
            approval_id=approval_id,
            write_digest=payload.write_digest,
            service=service,
            conversation_service=conversation_service,
        )
        outcome = service.deny(
            approval_id=approval_id,
            write_digest=payload.write_digest,
        )
    except (CalendarWriteChatUXError, CalendarWriteApprovalError) as error:
        raise _decision_error(error) from error

    _complete_original_conversation(
        conversation_service=conversation_service,
        outcome=outcome,
    )
    return ApiSuccess(
        data=CalendarWriteChatDecisionResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/approve",
    response_model=ApiSuccess[CalendarWriteChatDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_calendar_write_chat(
    approval_id: str,
    payload: CalendarWriteChatDecisionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    service: Annotated[
        CalendarWriteChatUXService,
        Depends(get_calendar_write_chat_ux_service),
    ],
    conversation_service: Annotated[
        ConversationService,
        Depends(get_conversation_service),
    ],
) -> ApiSuccess[CalendarWriteChatDecisionResponse]:
    try:
        _require_original_conversation_scope(
            approval_id=approval_id,
            write_digest=payload.write_digest,
            service=service,
            conversation_service=conversation_service,
        )
        outcome = service.approve(
            approval_id=approval_id,
            write_digest=payload.write_digest,
        )
    except (CalendarWriteChatUXError, CalendarWriteApprovalError) as error:
        raise _decision_error(error) from error

    _complete_original_conversation(
        conversation_service=conversation_service,
        outcome=outcome,
    )
    return ApiSuccess(
        data=CalendarWriteChatDecisionResponse.from_outcome(outcome)
    )
