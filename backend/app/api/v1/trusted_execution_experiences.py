from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_execution_experience_trust_lifecycle_service
from app.schemas.api import ApiSuccess
from app.schemas.trusted_execution_experiences import (
    TrustedExecutionExperienceHistoryResponse,
    TrustedExecutionExperienceListResponse,
    TrustedExecutionExperienceResponse,
    TrustedExecutionExperienceRevokeRequest,
    TrustedExecutionExperienceState,
)
from app.services.execution_experience_trust_lifecycle import (
    ExecutionExperienceTrustLifecycleService,
)


router = APIRouter(
    prefix="/trusted-execution-experiences",
    tags=["trusted-execution-experiences"],
)


@router.get(
    "",
    response_model=ApiSuccess[TrustedExecutionExperienceListResponse],
    status_code=status.HTTP_200_OK,
)
def list_trusted_execution_experiences(
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    state: TrustedExecutionExperienceState | None = None,
) -> ApiSuccess[TrustedExecutionExperienceListResponse]:
    return ApiSuccess(data=service.list(state, page, page_size))


@router.get(
    "/{trusted_id}",
    response_model=ApiSuccess[TrustedExecutionExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def get_trusted_execution_experience(
    trusted_id: UUID,
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExecutionExperienceResponse]:
    return ApiSuccess(data=service.get(trusted_id))


@router.get(
    "/{trusted_id}/history",
    response_model=ApiSuccess[TrustedExecutionExperienceHistoryResponse],
    status_code=status.HTTP_200_OK,
)
def trusted_execution_experience_history(
    trusted_id: UUID,
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExecutionExperienceHistoryResponse]:
    return ApiSuccess(data=service.history(trusted_id))


@router.post(
    "/{trusted_id}/revisions/{revision}/revoke",
    response_model=ApiSuccess[TrustedExecutionExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def revoke_trusted_execution_experience(
    trusted_id: UUID,
    revision: int,
    payload: TrustedExecutionExperienceRevokeRequest,
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExecutionExperienceResponse]:
    return ApiSuccess(
        data=service.revoke(
            trusted_id=trusted_id,
            expected_revision=revision,
            promotion_fingerprint=payload.promotion_fingerprint,
        )
    )
