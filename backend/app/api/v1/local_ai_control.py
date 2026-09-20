"""D103 local-owner configured-model proposal/decision API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_local_ai_control_execution_service
from app.schemas.api import ApiSuccess
from app.schemas.local_ai_control import (
    LocalAIControlDecisionRequest,
    LocalAIControlDecisionResponse,
    LocalAIControlProposalRequest,
    LocalAIControlProposalResponse,
)
from app.services.local_ai_control_approval import (
    LocalAIControlApprovalAlreadyClaimedError,
    LocalAIControlApprovalDigestMismatchError,
    LocalAIControlApprovalError,
    LocalAIControlApprovalExpiredError,
    LocalAIControlApprovalNotApprovedError,
    LocalAIControlApprovalNotPendingError,
    LocalAIControlApprovalProposalInvalidError,
    LocalAIControlApprovalStoreFullError,
)
from app.services.local_ai_control_execution import (
    LocalAIControlExecutionError,
    LocalAIControlExecutionService,
)


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(
    prefix="/local-ai/control",
    tags=["local-ai-control"],
)


def require_local_ai_control_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local-owner browser intent; not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _approval_error(error: LocalAIControlApprovalError) -> HTTPException:
    if isinstance(error, LocalAIControlApprovalExpiredError):
        http_status = status.HTTP_410_GONE
    elif isinstance(
        error,
        (
            LocalAIControlApprovalAlreadyClaimedError,
            LocalAIControlApprovalDigestMismatchError,
            LocalAIControlApprovalNotApprovedError,
            LocalAIControlApprovalNotPendingError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(error, LocalAIControlApprovalStoreFullError):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, LocalAIControlApprovalProposalInvalidError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail=error.reason_code,
    )


@router.post(
    "/proposals",
    response_model=ApiSuccess[LocalAIControlProposalResponse],
    status_code=status.HTTP_200_OK,
)
def create_local_ai_control_proposal(
    payload: LocalAIControlProposalRequest,
    _: Annotated[
        None,
        Depends(require_local_ai_control_request_marker),
    ],
    service: Annotated[
        LocalAIControlExecutionService,
        Depends(get_local_ai_control_execution_service),
    ],
) -> ApiSuccess[LocalAIControlProposalResponse]:
    try:
        outcome = service.propose(payload.operation)
    except LocalAIControlApprovalError as error:
        raise _approval_error(error) from error
    except LocalAIControlExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.reason_code,
        ) from error

    return ApiSuccess(
        data=LocalAIControlProposalResponse.from_outcome(outcome)
    )


@router.post(
    "/proposals/{proposal_id}/decision",
    response_model=ApiSuccess[LocalAIControlDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def decide_local_ai_control_proposal(
    proposal_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: LocalAIControlDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_ai_control_request_marker),
    ],
    service: Annotated[
        LocalAIControlExecutionService,
        Depends(get_local_ai_control_execution_service),
    ],
) -> ApiSuccess[LocalAIControlDecisionResponse]:
    try:
        outcome = service.decide(
            proposal_id,
            decision=payload.decision,
            control_digest=payload.control_digest,
        )
    except LocalAIControlApprovalError as error:
        raise _approval_error(error) from error
    except LocalAIControlExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.reason_code,
        ) from error

    return ApiSuccess(
        data=LocalAIControlDecisionResponse.from_outcome(outcome)
    )


__all__ = [
    "require_local_ai_control_request_marker",
    "router",
]
