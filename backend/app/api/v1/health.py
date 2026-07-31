from fastapi import APIRouter, Request, status

from app.core.config import get_settings
from app.db.verification import TARGET_REVISION
from app.schemas.api import ApiSuccess
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiSuccess[HealthResponse], status_code=status.HTTP_200_OK)
def health_check(request: Request) -> ApiSuccess[HealthResponse]:
    """Return process liveness information without exposing sensitive settings."""
    settings = get_settings()
    revision = getattr(request.app.state, "database_revision", TARGET_REVISION)
    return ApiSuccess(data=HealthResponse(status="ok", service=settings.app_name, environment=settings.environment, database_revision=revision))
