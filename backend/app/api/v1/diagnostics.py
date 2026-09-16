"""D70 local-owner safe runtime diagnostics API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_runtime_diagnostics_service
from app.db.verification import TARGET_REVISION
from app.schemas.api import ApiSuccess
from app.schemas.diagnostics import RuntimeDiagnosticsResponse
from app.services.runtime_diagnostics import RuntimeDiagnosticsService


router = APIRouter(tags=["diagnostics"])


@router.get(
    "/diagnostics",
    response_model=ApiSuccess[RuntimeDiagnosticsResponse],
    status_code=status.HTTP_200_OK,
)
def runtime_diagnostics(
    request: Request,
    service: Annotated[
        RuntimeDiagnosticsService,
        Depends(get_runtime_diagnostics_service),
    ],
) -> ApiSuccess[RuntimeDiagnosticsResponse]:
    """Return allowlisted read-only status without execution or secret access."""
    revision = getattr(
        request.app.state,
        "database_revision",
        TARGET_REVISION,
    )
    return ApiSuccess(
        data=service.snapshot(database_revision=revision)
    )
