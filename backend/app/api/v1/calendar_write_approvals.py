"""D73 local-owner API for Calendar write proposal and approval only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_calendar_write_approval_service
from app.schemas.api import ApiSuccess
from app.schemas.calendar_write_approvals import (
    CalendarWriteApprovalDecisionRequest,
    CalendarWriteApprovalDecisionResponse,
    CalendarWriteApprovalProposalResponse,
    CalendarWriteApprovalRequest,
    to_calendar_write_request,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalDigestMismatchError,
    CalendarWriteApprovalError,
    CalendarWriteApprovalExpiredError,
    CalendarWriteApprovalNotApprovedError,
    CalendarWriteApprovalNotPendingError,
    CalendarWriteApprovalProposalInvalidError,
    CalendarWriteApprovalService,
    CalendarWriteApprovalStoreFullError,
)


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(
    prefix="/calendar-write-approvals",
    tags=["calendar-write-approvals"],
)


def require_local_calendar_write_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local browser intent; this is not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _service_error(error: CalendarWriteApprovalError) -> HTTPException:
    if isinstance(error, CalendarWriteApprovalExpiredError):
        http_status = status.HTTP_410_GONE
    elif isinstance(
        error,
        (
            CalendarWriteApprovalDigestMismatchError,
            CalendarWriteApprovalNotApprovedError,
            CalendarWriteApprovalNotPendingError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(error, CalendarWriteApprovalStoreFullError):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, CalendarWriteApprovalProposalInvalidError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail=error.reason_code,
    )


@router.post(
    "",
    response_model=ApiSuccess[CalendarWriteApprovalProposalResponse],
    status_code=status.HTTP_200_OK,
)
def create_calendar_write_approval(
    payload: CalendarWriteApprovalRequest,
    _: Annotated[
        None,
        Depends(require_local_calendar_write_request_marker),
    ],
    service: Annotated[
        CalendarWriteApprovalService,
        Depends(get_calendar_write_approval_service),
    ],
) -> ApiSuccess[CalendarWriteApprovalProposalResponse]:
    try:
        request = to_calendar_write_request(payload)
        outcome = service.propose(request)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="calendar_write_request_invalid",
        ) from error
    except CalendarWriteApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=CalendarWriteApprovalProposalResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/approve",
    response_model=ApiSuccess[CalendarWriteApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_calendar_write(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: CalendarWriteApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_calendar_write_request_marker),
    ],
    service: Annotated[
        CalendarWriteApprovalService,
        Depends(get_calendar_write_approval_service),
    ],
) -> ApiSuccess[CalendarWriteApprovalDecisionResponse]:
    try:
        outcome = service.approve(
            approval_id,
            payload.write_digest,
        )
    except CalendarWriteApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=CalendarWriteApprovalDecisionResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/deny",
    response_model=ApiSuccess[CalendarWriteApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_calendar_write(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: CalendarWriteApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_calendar_write_request_marker),
    ],
    service: Annotated[
        CalendarWriteApprovalService,
        Depends(get_calendar_write_approval_service),
    ],
) -> ApiSuccess[CalendarWriteApprovalDecisionResponse]:
    try:
        outcome = service.deny(
            approval_id,
            payload.write_digest,
        )
    except CalendarWriteApprovalError as error:
        raise _service_error(error) from error

    return ApiSuccess(
        data=CalendarWriteApprovalDecisionResponse.from_outcome(outcome)
    )
