from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_calendar_delete_owner_decision_service,
    get_calendar_delete_selection_proposal_service,
    get_calendar_write_chat_ux_service,
    get_conversation_service,
)
from app.api.workspace_scope import get_workspace_scope
from app.api.v1.calendar_write_approvals import (
    require_local_calendar_write_request_marker,
)
from app.contracts.workspace import WorkspaceScope
from app.schemas.api import ApiSuccess
from app.schemas.calendar_delete_owner import (
    CalendarDeleteDecisionRequest,
    CalendarDeleteDecisionResponse,
    CalendarDeletePrepareRequest,
    CalendarDeletePrepareResponse,
)
from app.schemas.calendar_write_chat import (
    CalendarWriteChatDecisionRequest,
    CalendarWriteChatDecisionResponse,
)
from app.services.calendar_delete_owner_decision import (
    CalendarDeleteOwnerDecisionError,
    CalendarDeleteOwnerDecisionService,
)
from app.services.calendar_delete_decision import CalendarDeleteDecisionError
from app.services.calendar_delete_selection_proposal import (
    CalendarDeleteSelectionProposalError,
    CalendarDeleteSelectionProposalService,
)
from app.services.calendar_read_selection import CalendarReadSelectionError
from app.services.calendar_write_approval import CalendarWriteApprovalError
from app.services.calendar_write_followup import CalendarWriteFollowupError
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
    "/selection/{selection_id}/delete/prepare",
    response_model=ApiSuccess[CalendarDeletePrepareResponse],
    status_code=status.HTTP_200_OK,
)
def prepare_calendar_delete(
    selection_id: str,
    payload: CalendarDeletePrepareRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    workspace_scope: Annotated[
        WorkspaceScope,
        Depends(get_workspace_scope),
    ],
    service: Annotated[
        CalendarDeleteSelectionProposalService,
        Depends(get_calendar_delete_selection_proposal_service),
    ],
) -> ApiSuccess[CalendarDeletePrepareResponse]:
    try:
        outcome = service.propose_from_selection(
            selection_id=selection_id,
            workspace_id=workspace_scope.workspace_id,
            conversation_id=payload.conversation_id,
        )
    except (
        CalendarReadSelectionError,
        CalendarWriteFollowupError,
        CalendarWriteApprovalError,
        CalendarDeleteSelectionProposalError,
    ) as error:
        reason_code = getattr(
            error,
            "reason_code",
            "calendar_delete_prepare_rejected",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(reason_code),
        ) from error

    proposal = outcome.proposal
    return ApiSuccess(
        data=CalendarDeletePrepareResponse(
            selection_id=selection_id,
            approval_id=proposal.approval_id,
            write_digest=proposal.write_digest,
            operation=proposal.preview.operation,
            status=outcome.status,
            expires_at=proposal.expires_at,
        )
    )


@router.post(
    "/delete/{approval_id}/deny",
    response_model=ApiSuccess[CalendarDeleteDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_calendar_delete(
    approval_id: str,
    payload: CalendarDeleteDecisionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    workspace_scope: Annotated[
        WorkspaceScope,
        Depends(get_workspace_scope),
    ],
    service: Annotated[
        CalendarDeleteOwnerDecisionService,
        Depends(get_calendar_delete_owner_decision_service),
    ],
) -> ApiSuccess[CalendarDeleteDecisionResponse]:
    try:
        outcome = service.deny(
            approval_id=approval_id,
            write_digest=payload.write_digest,
            workspace_id=workspace_scope.workspace_id,
            conversation_id=payload.conversation_id,
        )
    except (
        CalendarDeleteDecisionError,
        CalendarWriteApprovalError,
        CalendarDeleteOwnerDecisionError,
    ) as error:
        raise _decision_error(error) from error

    return ApiSuccess(
        data=CalendarDeleteDecisionResponse(
            approval_id=outcome.approval_id,
            decision=outcome.decision,
            status=outcome.status,
            reason_code=outcome.reason_code,
        )
    )


@router.post(
    "/delete/{approval_id}/approve",
    response_model=ApiSuccess[CalendarDeleteDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_calendar_delete(
    approval_id: str,
    payload: CalendarDeleteDecisionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    workspace_scope: Annotated[
        WorkspaceScope,
        Depends(get_workspace_scope),
    ],
    service: Annotated[
        CalendarDeleteOwnerDecisionService,
        Depends(get_calendar_delete_owner_decision_service),
    ],
) -> ApiSuccess[CalendarDeleteDecisionResponse]:
    try:
        outcome = service.approve(
            approval_id=approval_id,
            write_digest=payload.write_digest,
            workspace_id=workspace_scope.workspace_id,
            conversation_id=payload.conversation_id,
        )
    except (
        CalendarDeleteDecisionError,
        CalendarWriteApprovalError,
        CalendarDeleteOwnerDecisionError,
    ) as error:
        raise _decision_error(error) from error

    return ApiSuccess(
        data=CalendarDeleteDecisionResponse(
            approval_id=outcome.approval_id,
            decision=outcome.decision,
            status=outcome.status,
            reason_code=outcome.reason_code,
        )
    )


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
