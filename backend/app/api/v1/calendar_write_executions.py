"""D74 local-owner API for one approved Calendar create execution."""

from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import (
    get_calendar_create_execution_service,
    get_calendar_update_delete_execution_service,
)
from app.api.v1.calendar_write_approvals import require_local_calendar_write_request_marker
from app.schemas.api import ApiSuccess
from app.schemas.calendar_write_executions import (
    CalendarCreateExecutionRequest,
    CalendarCreateExecutionResponse,
    CalendarDeleteExecutionRequest,
    CalendarDeleteExecutionResponse,
    CalendarUpdateExecutionRequest,
    CalendarUpdateExecutionResponse,
)
from app.services.calendar_create_execution import (
    CalendarCreateExecutionError,
    CalendarCreateExecutionService,
)
from app.services.calendar_update_delete_execution import (
    CalendarDeleteExecutionError,
    CalendarUpdateDeleteExecutionService,
    CalendarUpdateExecutionError,
)
from app.services.calendar_write_approval import (
    CalendarWriteApprovalAlreadyClaimedError,
    CalendarWriteApprovalDigestMismatchError,
    CalendarWriteApprovalError,
    CalendarWriteApprovalExpiredError,
    CalendarWriteApprovalNotApprovedError,
)

router = APIRouter(prefix="/calendar-write-executions", tags=["calendar-write-executions"])


def _approval_error(error: CalendarWriteApprovalError) -> HTTPException:
    if isinstance(error, CalendarWriteApprovalExpiredError):
        code = status.HTTP_410_GONE
    elif isinstance(error, (CalendarWriteApprovalAlreadyClaimedError, CalendarWriteApprovalDigestMismatchError, CalendarWriteApprovalNotApprovedError)):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=error.reason_code)


@router.post("/create", response_model=ApiSuccess[CalendarCreateExecutionResponse], status_code=status.HTTP_200_OK)
def execute_calendar_create(
    payload: CalendarCreateExecutionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    service: Annotated[CalendarCreateExecutionService, Depends(get_calendar_create_execution_service)],
) -> ApiSuccess[CalendarCreateExecutionResponse]:
    try:
        outcome = service.execute_create(payload.approval_id, payload.write_digest)
    except CalendarWriteApprovalError as error:
        raise _approval_error(error) from error
    except CalendarCreateExecutionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.reason_code) from error
    return ApiSuccess(data=CalendarCreateExecutionResponse.from_outcome(outcome))


@router.post(
    "/update",
    response_model=ApiSuccess[CalendarUpdateExecutionResponse],
    status_code=status.HTTP_200_OK,
)
def execute_calendar_update(
    payload: CalendarUpdateExecutionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    service: Annotated[
        CalendarUpdateDeleteExecutionService,
        Depends(get_calendar_update_delete_execution_service),
    ],
) -> ApiSuccess[CalendarUpdateExecutionResponse]:
    try:
        outcome = service.execute_update(
            payload.approval_id,
            payload.write_digest,
        )
    except CalendarWriteApprovalError as error:
        raise _approval_error(error) from error
    except CalendarUpdateExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.reason_code,
        ) from error
    return ApiSuccess(
        data=CalendarUpdateExecutionResponse.from_outcome(outcome)
    )


@router.post(
    "/delete",
    response_model=ApiSuccess[CalendarDeleteExecutionResponse],
    status_code=status.HTTP_200_OK,
)
def execute_calendar_delete(
    payload: CalendarDeleteExecutionRequest,
    _: Annotated[None, Depends(require_local_calendar_write_request_marker)],
    service: Annotated[
        CalendarUpdateDeleteExecutionService,
        Depends(get_calendar_update_delete_execution_service),
    ],
) -> ApiSuccess[CalendarDeleteExecutionResponse]:
    try:
        outcome = service.execute_delete(
            payload.approval_id,
            payload.write_digest,
        )
    except CalendarWriteApprovalError as error:
        raise _approval_error(error) from error
    except CalendarDeleteExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.reason_code,
        ) from error
    return ApiSuccess(
        data=CalendarDeleteExecutionResponse.from_outcome(outcome)
    )
