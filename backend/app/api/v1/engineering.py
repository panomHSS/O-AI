"""D109 local owner Engineering API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.api.dependencies import (
    get_engineering_ai_draft_workflow_service,
    get_engineering_investigation_workflow_service,
    get_skill_invocation_bridge,
    get_engineering_owner_workflow_service,
)
from app.schemas.api import ApiSuccess
from app.schemas.engineering_ai_draft import (
    EngineeringAIDraftCreateRequest,
    EngineeringAIDraftResponse,
)
from app.schemas.engineering_investigation import (
    EngineeringInvestigationCreateRequest,
    EngineeringInvestigationResponse,
)
from app.schemas.engineering_owner import (
    EngineeringOwnerActiveWorkflowResponse,
    EngineeringOwnerDecisionRequest,
    EngineeringOwnerProposalRequest,
    EngineeringOwnerReadRequest,
    EngineeringOwnerReadResponse,
    EngineeringOwnerWorkflowResponse,
)
from app.contracts.engineering_ai_draft import EngineeringAIDraftRequest
from app.contracts.engineering_investigation import (
    EngineeringInvestigationRequest,
)
from app.services.engineering_ai_draft import (
    EngineeringAIDraftConversationNotFoundError,
    EngineeringAIDraftError,
    EngineeringAIDraftWorkflowService,
)
from app.services.engineering_investigation import EngineeringInvestigationError
from app.services.skill_invocation_bridge import (
    SKILL_INVOCATION_DESCRIPTOR_MISMATCH,
    SKILL_INVOCATION_REQUEST_INVALID,
    SKILL_INVOCATION_SKILL_NOT_FOUND,
    SKILL_INVOCATION_SKILL_UNSUPPORTED,
    SkillInvocationBridge,
    SkillInvocationError,
)
from app.services.engineering_investigation_workflow import (
    EngineeringInvestigationConversationNotFoundError,
    EngineeringInvestigationWorkflowService,
)
from app.services.engineering_owner_binding import (
    EngineeringOwnerActiveWorkflowError,
    EngineeringOwnerBindingError,
    EngineeringOwnerBindingNotFoundError,
    EngineeringOwnerBindingStateError,
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
    elif isinstance(error, EngineeringOwnerBindingNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerActiveWorkflowError):
        http_status = status.HTTP_409_CONFLICT
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerBindingStateError):
        http_status = status.HTTP_409_CONFLICT
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerBindingStoreFullError):
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerRequestError):
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = error.reason_code
    elif isinstance(error, EngineeringOwnerUpstreamError):
        http_status = status.HTTP_409_CONFLICT
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


def _ai_draft_error(error: EngineeringAIDraftError) -> HTTPException:
    detail = error.code
    if isinstance(error, EngineeringAIDraftConversationNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif detail == "engineering_ai_draft_unavailable":
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=http_status, detail=detail)


def _investigation_error(
    error: EngineeringInvestigationError,
) -> HTTPException:
    detail = error.code
    if isinstance(
        error,
        EngineeringInvestigationConversationNotFoundError,
    ):
        http_status = status.HTTP_404_NOT_FOUND
    elif detail in {
        "engineering_investigation_ai_unavailable",
        "engineering_investigation_evidence_unavailable",
    }:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=http_status, detail=detail)

def _skill_invocation_error(
    error: SkillInvocationError,
) -> HTTPException:
    detail = error.code
    if detail == SKILL_INVOCATION_SKILL_NOT_FOUND:
        http_status = status.HTTP_404_NOT_FOUND
    elif detail == SKILL_INVOCATION_DESCRIPTOR_MISMATCH:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif detail in {
        SKILL_INVOCATION_REQUEST_INVALID,
        SKILL_INVOCATION_SKILL_UNSUPPORTED,
    }:
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:
        detail = SKILL_INVOCATION_REQUEST_INVALID
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=http_status, detail=detail)


def _workflow_response(
    service: EngineeringOwnerWorkflowService,
    binding,
) -> ApiSuccess[EngineeringOwnerWorkflowResponse]:
    return ApiSuccess(
        data=EngineeringOwnerWorkflowResponse.from_binding(
            workspace_id=service.workspace_scope.workspace_id.value,
            binding=binding,
        )
    )


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
    "/ai-drafts",
    response_model=ApiSuccess[EngineeringAIDraftResponse],
    status_code=status.HTTP_200_OK,
)
def create_engineering_ai_draft(
    payload: EngineeringAIDraftCreateRequest,
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    service: Annotated[
        EngineeringAIDraftWorkflowService,
        Depends(get_engineering_ai_draft_workflow_service),
    ],
) -> ApiSuccess[EngineeringAIDraftResponse]:
    try:
        request = EngineeringAIDraftRequest(
            conversation_id=payload.conversation_id,
            relative_path=payload.relative_path,
            instruction=payload.instruction,
        )
        result = service.draft(request)
    except ValueError as error:
        detail = str(error)
        if not detail.startswith("engineering_ai_draft_"):
            detail = "engineering_ai_draft_request_invalid"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        ) from error
    except EngineeringAIDraftError as error:
        raise _ai_draft_error(error) from error

    return ApiSuccess(
        data=EngineeringAIDraftResponse.from_result(result)
    )


@router.post(
    "/investigations",
    response_model=ApiSuccess[EngineeringInvestigationResponse],
    status_code=status.HTTP_200_OK,
)
def create_engineering_investigation(
    payload: EngineeringInvestigationCreateRequest,
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    service: Annotated[
        EngineeringInvestigationWorkflowService,
        Depends(get_engineering_investigation_workflow_service),
    ],
) -> ApiSuccess[EngineeringInvestigationResponse]:
    try:
        request = EngineeringInvestigationRequest(
            conversation_id=payload.conversation_id,
            instruction=payload.instruction,
            focus_paths=tuple(payload.focus_paths),
        )
        result = service.investigate(request)
    except ValueError as error:
        detail = str(error)
        if not detail.startswith("engineering_investigation_"):
            detail = "engineering_investigation_request_invalid"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        ) from error
    except EngineeringInvestigationError as error:
        raise _investigation_error(error) from error

    return ApiSuccess(
        data=EngineeringInvestigationResponse.from_result(
            workspace_id=service.workspace_scope.workspace_id.value,
            focus_paths=request.focus_paths,
            result=result,
        )
    )

@router.post(
    "/skills/{skill_id}/invoke",
    response_model=ApiSuccess[EngineeringInvestigationResponse],
    status_code=status.HTTP_200_OK,
)
def invoke_engineering_skill(
    skill_id: Annotated[str, Path(min_length=1)],
    payload: EngineeringInvestigationCreateRequest,
    _: Annotated[
        None,
        Depends(require_local_engineering_owner_request_marker),
    ],
    bridge: Annotated[
        SkillInvocationBridge,
        Depends(get_skill_invocation_bridge),
    ],
    workflow: Annotated[
        EngineeringInvestigationWorkflowService,
        Depends(get_engineering_investigation_workflow_service),
    ],
) -> ApiSuccess[EngineeringInvestigationResponse]:
    try:
        request = EngineeringInvestigationRequest(
            conversation_id=payload.conversation_id,
            instruction=payload.instruction,
            focus_paths=tuple(payload.focus_paths),
        )
        result = bridge.invoke(
            skill_id=skill_id,
            request=request,
        )
    except ValueError as error:
        detail = str(error)
        if not detail.startswith("engineering_investigation_"):
            detail = SKILL_INVOCATION_REQUEST_INVALID
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        ) from error
    except SkillInvocationError as error:
        raise _skill_invocation_error(error) from error
    except EngineeringInvestigationError as error:
        raise _investigation_error(error) from error

    return ApiSuccess(
        data=EngineeringInvestigationResponse.from_result(
            workspace_id=workflow.workspace_scope.workspace_id.value,
            focus_paths=request.focus_paths,
            result=result,
        )
    )


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
    return _workflow_response(service, binding)


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


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApiSuccess[EngineeringOwnerWorkflowResponse],
    status_code=status.HTTP_200_OK,
)
def approve_engineering_proposal(
    approval_id: Annotated[str, Path(min_length=1)],
    payload: EngineeringOwnerDecisionRequest,
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
        binding = service.approve(
            conversation_id=payload.conversation_id,
            approval_id=approval_id,
            proposal_digest=payload.proposal_digest,
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
    return _workflow_response(service, binding)


@router.post(
    "/approvals/{approval_id}/deny",
    response_model=ApiSuccess[EngineeringOwnerWorkflowResponse],
    status_code=status.HTTP_200_OK,
)
def deny_engineering_proposal(
    approval_id: Annotated[str, Path(min_length=1)],
    payload: EngineeringOwnerDecisionRequest,
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
        binding = service.deny(
            conversation_id=payload.conversation_id,
            approval_id=approval_id,
            proposal_digest=payload.proposal_digest,
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
    return _workflow_response(service, binding)


@router.post(
    "/approvals/{approval_id}/apply",
    response_model=ApiSuccess[EngineeringOwnerWorkflowResponse],
    status_code=status.HTTP_200_OK,
)
def apply_engineering_proposal(
    approval_id: Annotated[str, Path(min_length=1)],
    payload: EngineeringOwnerDecisionRequest,
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
        binding = service.apply(
            conversation_id=payload.conversation_id,
            approval_id=approval_id,
            proposal_digest=payload.proposal_digest,
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
    return _workflow_response(service, binding)


__all__ = [
    "LOCAL_REQUEST_HEADER_VALUE",
    "apply_engineering_proposal",
    "approve_engineering_proposal",
    "create_engineering_ai_draft",
    "create_engineering_investigation",
    "invoke_engineering_skill",
    "create_engineering_proposal",
    "deny_engineering_proposal",
    "get_active_engineering_workflow",
    "read_engineering_repository",
    "require_local_engineering_owner_request_marker",
    "router",
]
