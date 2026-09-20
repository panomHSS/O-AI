"""Read-only D102 Local AI runtime/model visibility API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_local_ai_visibility_service
from app.schemas.api import ApiSuccess
from app.schemas.local_ai_visibility import LocalAIRuntimeVisibilityResponse
from app.services.local_ai_visibility import LocalAIRuntimeVisibilityService


router = APIRouter(prefix="/local-ai", tags=["local-ai"])


@router.get(
    "/runtime",
    response_model=ApiSuccess[LocalAIRuntimeVisibilityResponse],
    status_code=status.HTTP_200_OK,
)
def local_ai_runtime_visibility(
    service: Annotated[
        LocalAIRuntimeVisibilityService,
        Depends(get_local_ai_visibility_service),
    ],
) -> ApiSuccess[LocalAIRuntimeVisibilityResponse]:
    """Return allowlisted Local AI visibility without execution authority."""
    visibility = service.get_visibility()
    return ApiSuccess(
        data=LocalAIRuntimeVisibilityResponse.from_contract(visibility)
    )
