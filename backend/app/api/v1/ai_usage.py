"""D155 read-only AI usage/token/cost API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_ai_usage_summary_service
from app.schemas.ai_usage import AIUsageSummaryResponse
from app.schemas.api import ApiSuccess
from app.services.ai_usage_summary import AIUsageSummaryService


router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


@router.get(
    "/summary",
    response_model=ApiSuccess[AIUsageSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def ai_usage_summary(
    service: Annotated[
        AIUsageSummaryService,
        Depends(get_ai_usage_summary_service),
    ],
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    model_id: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
) -> ApiSuccess[AIUsageSummaryResponse]:
    """Return allowlisted aggregate usage only; never prompts or completions."""
    try:
        summary = service.summarize(
            since=since,
            until=until,
            model_id=model_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI usage summary filters.",
        ) from None
    return ApiSuccess(data=AIUsageSummaryResponse.from_contract(summary))
