"""D88 explicit local-owner API for one approved Gmail send execution."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_gmail_send_execution_service
from app.api.v1.gmail_send_approvals import (
    require_local_gmail_send_request_marker,
)
from app.schemas.api import ApiSuccess
from app.schemas.gmail_send_executions import (
    GmailSendExecutionRequest,
    GmailSendExecutionResponse,
)
from app.services.gmail_send_execution import (
    GmailSendExecutionError,
    GmailSendExecutionExpiredError,
    GmailSendExecutionIntegrityError,
    GmailSendExecutionStoreFullError,
)
from app.services.gmail_send_execution_service import (
    GmailSendExecutionAuthorizationError,
    GmailSendExecutionDisabledError,
    GmailSendExecutionDigestMismatchError,
    GmailSendExecutionNotApprovedError,
    GmailSendExecutionSenderNotConfiguredError,
    GmailSendExecutionService,
)


router = APIRouter(
    prefix="/gmail-send-executions",
    tags=["gmail-send-executions"],
)


def _execution_error(error: GmailSendExecutionError) -> HTTPException:
    if isinstance(error, GmailSendExecutionExpiredError):
        http_status = status.HTTP_410_GONE
    elif isinstance(
        error,
        (
            GmailSendExecutionDisabledError,
            GmailSendExecutionSenderNotConfiguredError,
            GmailSendExecutionStoreFullError,
        ),
    ):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(
        error,
        (
            GmailSendExecutionNotApprovedError,
            GmailSendExecutionDigestMismatchError,
            GmailSendExecutionAuthorizationError,
            GmailSendExecutionIntegrityError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_409_CONFLICT

    return HTTPException(
        status_code=http_status,
        detail=error.reason_code,
    )


@router.post(
    "",
    response_model=ApiSuccess[GmailSendExecutionResponse],
    status_code=status.HTTP_200_OK,
)
def execute_gmail_send(
    payload: GmailSendExecutionRequest,
    _: Annotated[
        None,
        Depends(require_local_gmail_send_request_marker),
    ],
    service: Annotated[
        GmailSendExecutionService,
        Depends(get_gmail_send_execution_service),
    ],
) -> ApiSuccess[GmailSendExecutionResponse]:
    try:
        outcome = service.execute(
            payload.approval_id,
            payload.send_digest,
        )
    except GmailSendExecutionError as error:
        raise _execution_error(error) from error

    return ApiSuccess(
        data=GmailSendExecutionResponse.from_outcome(outcome)
    )


__all__ = ["router"]
