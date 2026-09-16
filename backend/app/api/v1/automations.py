"""D79 strict local-owner automation proposal and lifecycle API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_automation_approval_service
from app.schemas.api import ApiSuccess
from app.schemas.automations import (
    AutomationCancelResponse,
    AutomationDecisionRequest,
    AutomationDecisionResponse,
    AutomationDefinitionResponse,
    AutomationListResponse,
    AutomationProposalRequest,
    AutomationProposalResponse,
    AutomationRunListResponse,
    AutomationRunResponse,
    to_schedule,
)
from app.services.automation_approval import (
    AutomationActiveCapacityError,
    AutomationApprovalService,
    AutomationDigestMismatchError,
    AutomationDisabledError,
    AutomationExpiredError,
    AutomationLifecycleError,
    AutomationNotActiveError,
    AutomationNotFoundError,
    AutomationNotPendingError,
    AutomationPendingCapacityError,
    AutomationProposalInvalidError,
    AutomationStorageInvariantError,
)


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(tags=["automations"])


def require_local_automation_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local owner intent; this is not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _service_error(error: AutomationLifecycleError) -> HTTPException:
    if isinstance(error, AutomationNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, AutomationExpiredError):
        http_status = status.HTTP_410_GONE
    elif isinstance(
        error,
        (
            AutomationDigestMismatchError,
            AutomationNotActiveError,
            AutomationNotPendingError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    elif isinstance(
        error,
        (
            AutomationActiveCapacityError,
            AutomationDisabledError,
            AutomationPendingCapacityError,
        ),
    ):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, AutomationProposalInvalidError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(error, AutomationStorageInvariantError):
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=http_status,
        detail=error.reason_code,
    )


@router.post(
    "/automation-proposals",
    response_model=ApiSuccess[AutomationProposalResponse],
    status_code=status.HTTP_200_OK,
)
def create_automation_proposal(
    payload: AutomationProposalRequest,
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationProposalResponse]:
    try:
        outcome = service.propose(
            message=payload.message,
            schedule=to_schedule(payload.schedule),
            max_runs=payload.max_runs,
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="automation_proposal_invalid",
        ) from error
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationProposalResponse.from_outcome(outcome)
    )


@router.post(
    "/automation-proposals/{automation_id}/approve",
    response_model=ApiSuccess[AutomationDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_automation_proposal(
    automation_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: AutomationDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationDecisionResponse]:
    try:
        outcome = service.approve(
            automation_id,
            payload.definition_digest,
        )
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationDecisionResponse.from_outcome(outcome)
    )


@router.post(
    "/automation-proposals/{automation_id}/deny",
    response_model=ApiSuccess[AutomationDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_automation_proposal(
    automation_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: AutomationDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationDecisionResponse]:
    try:
        outcome = service.deny(
            automation_id,
            payload.definition_digest,
        )
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationDecisionResponse.from_outcome(outcome)
    )


@router.get(
    "/automations",
    response_model=ApiSuccess[AutomationListResponse],
    status_code=status.HTTP_200_OK,
)
def list_automations(
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationListResponse]:
    try:
        items = service.list_automations()
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationListResponse(
            items=[
                AutomationDefinitionResponse.from_view(item)
                for item in items
            ]
        )
    )


@router.get(
    "/automation-runs",
    response_model=ApiSuccess[AutomationRunListResponse],
    status_code=status.HTTP_200_OK,
)
def list_automation_runs(
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationRunListResponse]:
    try:
        items = service.list_runs()
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationRunListResponse(
            items=[
                AutomationRunResponse.from_view(item)
                for item in items
            ]
        )
    )


@router.post(
    "/automations/{automation_id}/cancel",
    response_model=ApiSuccess[AutomationCancelResponse],
    status_code=status.HTTP_200_OK,
)
def cancel_automation(
    automation_id: Annotated[str, Path(min_length=1, max_length=128)],
    _: Annotated[
        None,
        Depends(require_local_automation_request_marker),
    ],
    service: Annotated[
        AutomationApprovalService,
        Depends(get_automation_approval_service),
    ],
) -> ApiSuccess[AutomationCancelResponse]:
    try:
        outcome = service.cancel(automation_id)
    except AutomationLifecycleError as error:
        raise _service_error(error) from error
    return ApiSuccess(
        data=AutomationCancelResponse.from_outcome(outcome)
    )
