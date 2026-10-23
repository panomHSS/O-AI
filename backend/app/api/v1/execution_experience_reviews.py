from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_execution_experience_review_lifecycle_service,
    get_execution_experience_trust_lifecycle_service,
)
from app.schemas.api import ApiSuccess
from app.schemas.execution_experience_reviews import (
    ExecutionExperienceReviewDecisionRequest,
    ExecutionExperienceReviewHistoryResponse,
    ExecutionExperienceReviewListResponse,
    ExecutionExperienceReviewResponse,
    ExecutionExperienceReviewState,
)
from app.services.execution_experience_review_lifecycle import (
    ExecutionExperienceReviewLifecycleService,
)
from app.schemas.trusted_execution_experiences import (
    ExecutionExperienceTrustEligibilityResponse,
    ExecutionExperienceTrustPromotionRequest,
    TrustedExecutionExperienceResponse,
)
from app.services.execution_experience_trust_lifecycle import (
    ExecutionExperienceTrustLifecycleService,
)


router = APIRouter(
    prefix="/execution-experience-reviews",
    tags=["execution-experience-reviews"],
)


@router.get(
    "",
    response_model=ApiSuccess[ExecutionExperienceReviewListResponse],
    status_code=status.HTTP_200_OK,
)
def list_execution_experience_reviews(
    service: Annotated[
        ExecutionExperienceReviewLifecycleService,
        Depends(get_execution_experience_review_lifecycle_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    state: ExecutionExperienceReviewState | None = None,
) -> ApiSuccess[ExecutionExperienceReviewListResponse]:
    return ApiSuccess(data=service.list(state, page, page_size))


@router.get(
    "/{review_id}",
    response_model=ApiSuccess[ExecutionExperienceReviewResponse],
    status_code=status.HTTP_200_OK,
)
def get_execution_experience_review(
    review_id: UUID,
    service: Annotated[
        ExecutionExperienceReviewLifecycleService,
        Depends(get_execution_experience_review_lifecycle_service),
    ],
) -> ApiSuccess[ExecutionExperienceReviewResponse]:
    return ApiSuccess(data=service.get(review_id))


@router.get(
    "/{review_id}/history",
    response_model=ApiSuccess[ExecutionExperienceReviewHistoryResponse],
    status_code=status.HTTP_200_OK,
)
def execution_experience_review_history(
    review_id: UUID,
    service: Annotated[
        ExecutionExperienceReviewLifecycleService,
        Depends(get_execution_experience_review_lifecycle_service),
    ],
) -> ApiSuccess[ExecutionExperienceReviewHistoryResponse]:
    return ApiSuccess(data=service.history(review_id))


def _decide(
    *,
    action: str,
    review_id: UUID,
    revision: int,
    payload: ExecutionExperienceReviewDecisionRequest,
    service: ExecutionExperienceReviewLifecycleService,
) -> ExecutionExperienceReviewResponse:
    if action == "accept":
        return service.accept(review_id, revision, payload.source_review_fingerprint)
    if action == "reject":
        return service.reject(review_id, revision, payload.source_review_fingerprint)
    raise RuntimeError("execution_experience_review_action_invalid")


@router.post(
    "/{review_id}/revisions/{revision}/accept",
    response_model=ApiSuccess[ExecutionExperienceReviewResponse],
    status_code=status.HTTP_200_OK,
)
def accept_execution_experience_review(
    review_id: UUID,
    revision: int,
    payload: ExecutionExperienceReviewDecisionRequest,
    service: Annotated[
        ExecutionExperienceReviewLifecycleService,
        Depends(get_execution_experience_review_lifecycle_service),
    ],
) -> ApiSuccess[ExecutionExperienceReviewResponse]:
    return ApiSuccess(
        data=_decide(
            action="accept",
            review_id=review_id,
            revision=revision,
            payload=payload,
            service=service,
        )
    )


@router.post(
    "/{review_id}/revisions/{revision}/reject",
    response_model=ApiSuccess[ExecutionExperienceReviewResponse],
    status_code=status.HTTP_200_OK,
)
def reject_execution_experience_review(
    review_id: UUID,
    revision: int,
    payload: ExecutionExperienceReviewDecisionRequest,
    service: Annotated[
        ExecutionExperienceReviewLifecycleService,
        Depends(get_execution_experience_review_lifecycle_service),
    ],
) -> ApiSuccess[ExecutionExperienceReviewResponse]:
    return ApiSuccess(
        data=_decide(
            action="reject",
            review_id=review_id,
            revision=revision,
            payload=payload,
            service=service,
        )
    )
@router.get(
    "/{review_id}/trust-eligibility",
    response_model=ApiSuccess[ExecutionExperienceTrustEligibilityResponse],
    status_code=status.HTTP_200_OK,
)
def get_execution_experience_trust_eligibility(
    review_id: UUID,
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
) -> ApiSuccess[ExecutionExperienceTrustEligibilityResponse]:
    return ApiSuccess(data=service.evaluate(review_id))


@router.post(
    "/{review_id}/revisions/{revision}/promote-trust",
    response_model=ApiSuccess[TrustedExecutionExperienceResponse],
    status_code=status.HTTP_200_OK,
)
def promote_execution_experience_trust(
    review_id: UUID,
    revision: int,
    payload: ExecutionExperienceTrustPromotionRequest,
    service: Annotated[
        ExecutionExperienceTrustLifecycleService,
        Depends(get_execution_experience_trust_lifecycle_service),
    ],
) -> ApiSuccess[TrustedExecutionExperienceResponse]:
    return ApiSuccess(
        data=service.promote(
            review_id=review_id,
            expected_revision=revision,
            source_record_fingerprint=payload.source_record_fingerprint,
            promotion_fingerprint=payload.promotion_fingerprint,
        )
    )
