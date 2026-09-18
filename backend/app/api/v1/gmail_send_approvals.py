"""D87 local-owner API for Gmail send proposal and approval only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_gmail_send_approval_service
from app.schemas.api import ApiSuccess
from app.schemas.gmail_send_approvals import (
    GmailSendApprovalDecisionRequest,
    GmailSendApprovalDecisionResponse,
    GmailSendApprovalProposalResponse,
    GmailSendApprovalRequest,
    to_gmail_send_request,
)
from app.services.gmail_send_approval import (
    GmailSendApprovalDigestMismatchError,
    GmailSendApprovalError,
    GmailSendApprovalExpiredError,
    GmailSendApprovalNotApprovedError,
    GmailSendApprovalNotPendingError,
    GmailSendApprovalProposalInvalidError,
    GmailSendApprovalService,
    GmailSendApprovalStoreFullError,
)


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(
    prefix="/gmail-send-approvals",
    tags=["gmail-send-approvals"],
)


def require_local_gmail_send_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local browser intent; this is not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _service_error(error: GmailSendApprovalError) -> HTTPException:
    if isinstance(error, GmailSendApprovalExpiredError):
        http_status = status.HTTP_410_GONE
    elif isinstance(
        error,
        (
            GmailSendApprovalDigestMismatchError,
            GmailSendApprovalNotApprovedError,
            GmailSendApprovalNotPendingError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(error, GmailSendApprovalStoreFullError):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, GmailSendApprovalProposalInvalidError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail=error.reason_code,
    )


@router.post(
    "",
    response_model=ApiSuccess[GmailSendApprovalProposalResponse],
    status_code=status.HTTP_200_OK,
)
def create_gmail_send_approval(
    payload: GmailSendApprovalRequest,
    _: Annotated[
        None,
        Depends(require_local_gmail_send_request_marker),
    ],
    service: Annotated[
        GmailSendApprovalService,
        Depends(get_gmail_send_approval_service),
    ],
) -> ApiSuccess[GmailSendApprovalProposalResponse]:
    try:
        request = to_gmail_send_request(payload)
        outcome = service.propose(request)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="gmail_send_request_invalid",
        ) from error
    except GmailSendApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=GmailSendApprovalProposalResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/approve",
    response_model=ApiSuccess[GmailSendApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_gmail_send(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: GmailSendApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_gmail_send_request_marker),
    ],
    service: Annotated[
        GmailSendApprovalService,
        Depends(get_gmail_send_approval_service),
    ],
) -> ApiSuccess[GmailSendApprovalDecisionResponse]:
    try:
        outcome = service.approve(
            approval_id,
            payload.send_digest,
        )
    except GmailSendApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=GmailSendApprovalDecisionResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/deny",
    response_model=ApiSuccess[GmailSendApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_gmail_send(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: GmailSendApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_gmail_send_request_marker),
    ],
    service: Annotated[
        GmailSendApprovalService,
        Depends(get_gmail_send_approval_service),
    ],
) -> ApiSuccess[GmailSendApprovalDecisionResponse]:
    try:
        outcome = service.deny(
            approval_id,
            payload.send_digest,
        )
    except GmailSendApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=GmailSendApprovalDecisionResponse.from_outcome(outcome)
    )


__all__ = [
    "require_local_gmail_send_request_marker",
    "router",
]
