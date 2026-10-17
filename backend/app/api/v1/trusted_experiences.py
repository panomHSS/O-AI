from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_trusted_experience_lifecycle_service
from app.schemas.api import ApiSuccess
from app.schemas.trusted_experiences import (
    TrustedExperienceDecisionRequest,
    TrustedExperienceHistoryResponse,
    TrustedExperienceListResponse,
    TrustedExperienceResponse,
    TrustedExperienceState,
)
from app.services.trusted_experience_lifecycle import (
    TrustedExperienceLifecycleService,
)


router = APIRouter(
    prefix="/trusted-experiences",
    tags=["trusted-experiences"],
)


@router.get(
    "",
    response_model=ApiSuccess[TrustedExperienceListResponse],
    status_code=status.HTTP_200_OK,
)
def list_trusted_experiences(
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    state: TrustedExperienceState | None = None,
) -> ApiSuccess[TrustedExperienceListResponse]:
    return ApiSuccess(data=service.list(state, page, page_size))


@router.get(
    "/{trusted_experience_id}",
    response_model=ApiSuccess[TrustedExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def get_trusted_experience(
    trusted_experience_id: UUID,
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExperienceResponse]:
    return ApiSuccess(data=service.get(trusted_experience_id))


@router.get(
    "/{trusted_experience_id}/history",
    response_model=ApiSuccess[TrustedExperienceHistoryResponse],
    status_code=status.HTTP_200_OK,
)
def trusted_experience_history(
    trusted_experience_id: UUID,
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExperienceHistoryResponse]:
    return ApiSuccess(data=service.history(trusted_experience_id))


def _decide(
    *,
    action: str,
    trusted_experience_id: UUID,
    revision: int,
    payload: TrustedExperienceDecisionRequest,
    service: TrustedExperienceLifecycleService,
) -> TrustedExperienceResponse:
    if action == "approve":
        return service.approve(
            trusted_experience_id,
            revision,
            payload.decision_comment,
        )
    if action == "reject":
        return service.reject(
            trusted_experience_id,
            revision,
            payload.decision_comment,
        )
    if action == "revoke":
        return service.revoke(
            trusted_experience_id,
            revision,
            payload.decision_comment,
        )
    raise RuntimeError("trusted_experience_action_invalid")


@router.post(
    "/{trusted_experience_id}/revisions/{revision}/approve",
    response_model=ApiSuccess[TrustedExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def approve_trusted_experience(
    trusted_experience_id: UUID,
    revision: int,
    payload: TrustedExperienceDecisionRequest,
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExperienceResponse]:
    return ApiSuccess(
        data=_decide(
            action="approve",
            trusted_experience_id=trusted_experience_id,
            revision=revision,
            payload=payload,
            service=service,
        )
    )


@router.post(
    "/{trusted_experience_id}/revisions/{revision}/reject",
    response_model=ApiSuccess[TrustedExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def reject_trusted_experience(
    trusted_experience_id: UUID,
    revision: int,
    payload: TrustedExperienceDecisionRequest,
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExperienceResponse]:
    return ApiSuccess(
        data=_decide(
            action="reject",
            trusted_experience_id=trusted_experience_id,
            revision=revision,
            payload=payload,
            service=service,
        )
    )


@router.post(
    "/{trusted_experience_id}/revisions/{revision}/revoke",
    response_model=ApiSuccess[TrustedExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def revoke_trusted_experience(
    trusted_experience_id: UUID,
    revision: int,
    payload: TrustedExperienceDecisionRequest,
    service: Annotated[
        TrustedExperienceLifecycleService,
        Depends(get_trusted_experience_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExperienceResponse]:
    return ApiSuccess(
        data=_decide(
            action="revoke",
            trusted_experience_id=trusted_experience_id,
            revision=revision,
            payload=payload,
            service=service,
        )
    )
