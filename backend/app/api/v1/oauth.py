"""D64 local-owner Google Calendar OAuth control API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_google_oauth_lifecycle_service
from app.schemas.api import ApiSuccess
from app.schemas.oauth import OAuthConnectionStatusResponse
from app.services.google_oauth_lifecycle import (
    OAUTH_LIFECYCLE_ERROR_CONFIGURATION,
    OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED,
    OAUTH_LIFECYCLE_ERROR_EXCHANGE_FAILED,
    OAUTH_LIFECYCLE_ERROR_INVALID_CODE,
    OAUTH_LIFECYCLE_ERROR_PERSISTENCE,
    OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING,
    OAUTH_LIFECYCLE_ERROR_REVOCATION,
    OAUTH_LIFECYCLE_ERROR_STATE_INVALID,
    OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH,
    GoogleOAuthLifecycleError,
    GoogleOAuthLifecycleService,
)

router = APIRouter(
    prefix="/oauth/google-calendar",
    tags=["oauth"],
)

OAUTH_STATE_COOKIE = "oai_google_calendar_oauth_state"
LOCAL_REQUEST_HEADER_VALUE = "1"


def _status_response(service: GoogleOAuthLifecycleService):
    snapshot = service.status()
    return OAuthConnectionStatusResponse(
        connected=snapshot.connected,
        status=snapshot.status,
        scope=snapshot.scope,
    )


def _raise_safe(error: GoogleOAuthLifecycleError) -> None:
    if error.code == OAUTH_LIFECYCLE_ERROR_CONFIGURATION:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error.code,
        )
    if error.code in {
        OAUTH_LIFECYCLE_ERROR_STATE_MISMATCH,
        OAUTH_LIFECYCLE_ERROR_STATE_INVALID,
        OAUTH_LIFECYCLE_ERROR_CONSENT_DENIED,
        OAUTH_LIFECYCLE_ERROR_INVALID_CODE,
        OAUTH_LIFECYCLE_ERROR_REFRESH_TOKEN_MISSING,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error.code,
        )
    if error.code in {
        OAUTH_LIFECYCLE_ERROR_EXCHANGE_FAILED,
        OAUTH_LIFECYCLE_ERROR_REVOCATION,
    }:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error.code,
        )
    if error.code == OAUTH_LIFECYCLE_ERROR_PERSISTENCE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error.code,
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="oauth_unavailable",
    )


def require_local_oauth_request_marker(
    x_oai_local_request: Annotated[str | None, Header()] = None,
) -> None:
    if x_oai_local_request != LOCAL_REQUEST_HEADER_VALUE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.get("/start")
def start_google_calendar_oauth(
    service: Annotated[
        GoogleOAuthLifecycleService,
        Depends(get_google_oauth_lifecycle_service),
    ],
) -> RedirectResponse:
    try:
        authorization_url, state_value = service.start_authorization()
    except GoogleOAuthLifecycleError as error:
        _raise_safe(error)
    response = RedirectResponse(
        authorization_url,
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state_value,
        max_age=600,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/api/v1/oauth/google-calendar/callback",
    )
    return response


@router.get(
    "/callback",
    response_model=ApiSuccess[OAuthConnectionStatusResponse],
)
def google_calendar_oauth_callback(
    response: Response,
    state_value: Annotated[str, Query(alias="state", min_length=1, max_length=256)],
    service: Annotated[
        GoogleOAuthLifecycleService,
        Depends(get_google_oauth_lifecycle_service),
    ],
    code: Annotated[str | None, Query(max_length=8192)] = None,
    oauth_error: Annotated[str | None, Query(alias="error", max_length=256)] = None,
    cookie_state: Annotated[str | None, Cookie(alias=OAUTH_STATE_COOKIE)] = None,
) -> ApiSuccess[OAuthConnectionStatusResponse]:
    try:
        snapshot = service.complete_authorization(
            query_state=state_value,
            cookie_state=cookie_state,
            code=code,
            oauth_error=oauth_error,
        )
    except GoogleOAuthLifecycleError as error:
        _raise_safe(error)
    response.delete_cookie(
        OAUTH_STATE_COOKIE,
        path="/api/v1/oauth/google-calendar/callback",
    )
    return ApiSuccess(
        data=OAuthConnectionStatusResponse(
            connected=snapshot.connected,
            status=snapshot.status,
            scope=snapshot.scope,
        )
    )


@router.get(
    "/status",
    response_model=ApiSuccess[OAuthConnectionStatusResponse],
)
def google_calendar_oauth_status(
    service: Annotated[
        GoogleOAuthLifecycleService,
        Depends(get_google_oauth_lifecycle_service),
    ],
) -> ApiSuccess[OAuthConnectionStatusResponse]:
    return ApiSuccess(data=_status_response(service))


@router.post(
    "/disconnect",
    response_model=ApiSuccess[OAuthConnectionStatusResponse],
)
def disconnect_google_calendar_oauth(
    _: Annotated[
        None,
        Depends(require_local_oauth_request_marker),
    ],
    service: Annotated[
        GoogleOAuthLifecycleService,
        Depends(get_google_oauth_lifecycle_service),
    ],
) -> ApiSuccess[OAuthConnectionStatusResponse]:
    try:
        snapshot = service.disconnect()
    except GoogleOAuthLifecycleError as error:
        _raise_safe(error)
    return ApiSuccess(
        data=OAuthConnectionStatusResponse(
            connected=snapshot.connected,
            status=snapshot.status,
            scope=snapshot.scope,
        )
    )
