from fastapi import APIRouter, status

from app.core.config import get_settings
from app.schemas.api import ApiSuccess
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiSuccess[HealthResponse], status_code=status.HTTP_200_OK)
def health_check() -> ApiSuccess[HealthResponse]:
    """Return process liveness information without exposing sensitive settings."""
    settings = get_settings()
    return ApiSuccess(data=HealthResponse(status="ok", service=settings.app_name, environment=settings.environment))
