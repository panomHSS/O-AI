"""D109 local owner Engineering read/proposal API.

Batch 01 deliberately exposes no Approve, Deny, or Apply endpoint.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import get_engineering_owner_workflow_service
from app.schemas.api import ApiSuccess
from app.schemas.engineering_owner import (
    EngineeringOwnerActiveWorkflowResponse,
    EngineeringOwnerProposalRequest,
    EngineeringOwnerReadRequest,
    EngineeringOwnerReadResponse,
    EngineeringOwnerWorkflowResponse,
)
from app.services.engineering_owner_binding import (
    EngineeringOwnerActiveWorkflowError,
    EngineeringOwnerBindingError,
    EngineeringOwnerBindingStoreFullError,
)
from app.services.engineering_owner_workflow import (
    EngineeringOwnerConversationNotFoundError,
    EngineeringOwnerRequestError,
    EngineeringOwnerUpstreamError,
    EngineeringOwnerWorkflowError,
    EngineeringOwnerWorkflowService,
)


LOCAL_REQUEST_HEADER_VALUE = "1"

router = APIRouter(prefix="/engineering", tags=["engineering"])


def require_local_engineering_owner_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    """Require explicit local owner-browser intent; not authentication."""
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _service_error(error: Exception) -> HTTPException:
    if isinstance(error, EngineeringOwnerConversationNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerActiveWorkflowError):
        http_status = status.HTTP_409_CONFLICT
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerBindingStoreFullError):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerRequestError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerUpstreamError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerBindingError):
        http_status = status.HTTP_409_CONFLICT
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerWorkflowError):
        http_status = status.HTTP_400_BAD_REQUEST
        detail = error.reason_code
    else:
        http_status = status.HTTP_400_BAD_REQUEST
        detail = "engineering_owner_request_invalid"
    return HTTPException(status_code=http_status, detail=detail)


@router.post(
    "/read",
    response_model=ApiSuccess[EngineeringOwnerReadResponse],
    status_code=status.HTTP_200_OK,
)
def read_engineering_repository(
    payload: EngineeringOwnerReadRequest,
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    service: Annotated[
        EngineeringOwnerWorkflowService,
        Depends(get_engineering_owner_workflow_service),
    ],
) -> ApiSuccess[EngineeringOwnerReadResponse]:
    try:
        observation = service.read(
            conversation_id=payload.conversation_id,
            operation=payload.operation,
            relative_path=payload.relative_path,
        )
        data = EngineeringOwnerReadResponse.from_observation(
            workspace_id=service.workspace_scope.workspace_id.value,
            conversation_id=payload.conversation_id,
            observation=observation,
        )
    except Exception as error:
        if isinstance(
            error,
            (
                EngineeringOwnerWorkflowError,
                EngineeringOwnerBindingError,
            ),
        ):
            raise _service_error(error) from error
        raise
    return ApiSuccess(data=data)


@router.post(
    "/proposals",
    response_model=ApiSuccess[EngineeringOwnerWorkflowResponse],
    status_code=status.HTTP_200_OK,
)
def create_engineering_proposal(
    payload: EngineeringOwnerProposalRequest,
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    service: Annotated[
        EngineeringOwnerWorkflowService,
        Depends(get_engineering_owner_workflow_service),
    ],
) -> ApiSuccess[EngineeringOwnerWorkflowResponse]:
    try:
        binding = service.propose(
            conversation_id=payload.conversation_id,
            operation=payload.operation,
            relative_path=payload.relative_path,
            proposed_content=payload.proposed_content,
        )
    except Exception as error:
        if isinstance(
            error,
            (
                EngineeringOwnerWorkflowError,
                EngineeringOwnerBindingError,
            ),
        ):
            raise _service_error(error) from error
        raise
    return ApiSuccess(
        data=EngineeringOwnerWorkflowResponse.from_binding(
            workspace_id=service.workspace_scope.workspace_id.value,
            binding=binding,
        )
    )


@router.get(
    "/conversations/{conversation_id}/active",
    response_model=ApiSuccess[EngineeringOwnerActiveWorkflowResponse],
    status_code=status.HTTP_200_OK,
)
def get_active_engineering_workflow(
    conversation_id: Annotated[UUID, Path()],
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    service: Annotated[
        EngineeringOwnerWorkflowService,
        Depends(get_engineering_owner_workflow_service),
    ],
) -> ApiSuccess[EngineeringOwnerActiveWorkflowResponse]:
    try:
        binding = service.active(conversation_id=conversation_id)
    except Exception as error:
        if isinstance(
            error,
            (
                EngineeringOwnerWorkflowError,
                EngineeringOwnerBindingError,
            ),
        ):
            raise _service_error(error) from error
        raise

    workspace_id = service.workspace_scope.workspace_id.value
    active = (
        EngineeringOwnerWorkflowResponse.from_binding(
            workspace_id=workspace_id,
            binding=binding,
        )
        if binding is not None
        else None
    )
    return ApiSuccess(
        data=EngineeringOwnerActiveWorkflowResponse(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            active=active,
        )
    )


__all__ = [
    "LOCAL_REQUEST_HEADER_VALUE",
    "get_active_engineering_workflow",
    "read_engineering_repository",
    "create_engineering_proposal",
    "require_local_engineering_owner_request_marker",
    "router",
]
