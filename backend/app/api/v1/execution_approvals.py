"""D45 local-owner execution approval API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_execution_approval_service
from app.schemas.api import ApiSuccess
from app.schemas.execution_approvals import (
    CreateExecutionApprovalRequest,
    ExecutionApprovalDecisionRequest,
    ExecutionApprovalDecisionResponse,
    ExecutionApprovalProposalResponse,
)
from app.services.execution_approval_service import ExecutionApprovalService


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(
    prefix="/execution-approvals",
    tags=["execution-approvals"],
)


def require_local_execution_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local browser intent; this is not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.post(
    "",
    response_model=ApiSuccess[ExecutionApprovalProposalResponse],
    status_code=status.HTTP_200_OK,
)
def create_execution_approval(
    payload: CreateExecutionApprovalRequest,
    _: Annotated[
        None,
        Depends(require_local_execution_request_marker),
    ],
    service: Annotated[
        ExecutionApprovalService,
        Depends(get_execution_approval_service),
    ],
) -> ApiSuccess[ExecutionApprovalProposalResponse]:
    outcome = service.propose(
        target_kind=payload.target_kind,
        adapter_id=payload.adapter_id,
        operation=payload.operation,
        parameters=payload.parameters,
    )
    return ApiSuccess(
        data=ExecutionApprovalProposalResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/approve",
    response_model=ApiSuccess[ExecutionApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def approve_execution(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: ExecutionApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_execution_request_marker),
    ],
    service: Annotated[
        ExecutionApprovalService,
        Depends(get_execution_approval_service),
    ],
) -> ApiSuccess[ExecutionApprovalDecisionResponse]:
    outcome = service.approve(
        approval_id,
        payload.plan_digest,
    )
    return ApiSuccess(
        data=ExecutionApprovalDecisionResponse.from_outcome(outcome)
    )


@router.post(
    "/{approval_id}/deny",
    response_model=ApiSuccess[ExecutionApprovalDecisionResponse],
    status_code=status.HTTP_200_OK,
)
def deny_execution(
    approval_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: ExecutionApprovalDecisionRequest,
    _: Annotated[
        None,
        Depends(require_local_execution_request_marker),
    ],
    service: Annotated[
        ExecutionApprovalService,
        Depends(get_execution_approval_service),
    ],
) -> ApiSuccess[ExecutionApprovalDecisionResponse]:
    outcome = service.deny(
        approval_id,
        payload.plan_digest,
    )
    return ApiSuccess(
        data=ExecutionApprovalDecisionResponse.from_outcome(outcome)
    )
