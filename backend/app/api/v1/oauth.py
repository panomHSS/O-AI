"""D64/D66 local-owner Google Calendar OAuth control API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    get_google_oauth_lifecycle_service,
    get_google_oauth_runtime_config,
    get_owner_ui_redirect_config,
)
from app.core.config import Settings, get_settings
from app.schemas.api import ApiSuccess
from app.schemas.oauth import OAuthConnectionStatusResponse
from app.services.google_oauth_config import GoogleOAuthRuntimeConfig
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
    GoogleOAuthStatus,
)
from app.services.owner_ui_redirect import OwnerUIRedirectConfig

router = APIRouter(
    prefix="/oauth/google-calendar",
    tags=["oauth"],
)

OAUTH_STATE_COOKIE = "oai_google_calendar_oauth_state"
LOCAL_REQUEST_HEADER_VALUE = "1"


def _status_response(
    snapshot: GoogleOAuthStatus,
    *,
    runtime_config: GoogleOAuthRuntimeConfig,
    settings: Settings,
) -> OAuthConnectionStatusResponse:
    return OAuthConnectionStatusResponse(
        connector_enabled=settings.oai_google_calendar_connector_enabled,
        configuration_present=runtime_config.configuration_present,
        connected=snapshot.connected,
        status=snapshot.status,
        scope=snapshot.scope,
        owner_timezone=settings.oai_owner_timezone,
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


def _callback_redirect(
    owner_ui_config: OwnerUIRedirectConfig,
    *,
    connected: bool,
    reason_code: str | None = None,
) -> RedirectResponse:
    destination = (
        owner_ui_config.google_calendar_connected_url()
        if connected
        else owner_ui_config.google_calendar_error_url(
            reason_code or "oauth_unavailable"
        )
    )
    response = RedirectResponse(
        destination,
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(
        OAUTH_STATE_COOKIE,
        path="/api/v1/oauth/google-calendar/callback",
    )
    return response


@router.get("/callback")
def google_calendar_oauth_callback(
    service: Annotated[
        GoogleOAuthLifecycleService,
        Depends(get_google_oauth_lifecycle_service),
    ],
    owner_ui_config: Annotated[
        OwnerUIRedirectConfig,
        Depends(get_owner_ui_redirect_config),
    ],
    state_value: Annotated[str | None, Query(alias="state")] = None,
    code: Annotated[str | None, Query()] = None,
    oauth_error: Annotated[str | None, Query(alias="error")] = None,
    cookie_state: Annotated[
        str | None,
        Cookie(alias=OAUTH_STATE_COOKIE),
    ] = None,
) -> RedirectResponse:
    if (
        not isinstance(state_value, str)
        or not state_value
        or len(state_value) > 256
    ):
        return _callback_redirect(
            owner_ui_config,
            connected=False,
            reason_code=OAUTH_LIFECYCLE_ERROR_STATE_INVALID,
        )
    if (
        oauth_error is None
        and code is not None
        and (
            not isinstance(code, str)
            or not code
            or len(code.encode("utf-8")) > 8192
            or "\r" in code
            or "\n" in code
        )
    ):
        return _callback_redirect(
            owner_ui_config,
            connected=False,
            reason_code=OAUTH_LIFECYCLE_ERROR_INVALID_CODE,
        )

    try:
        service.complete_authorization(
            query_state=state_value,
            cookie_state=cookie_state,
            code=code,
            oauth_error=oauth_error,
        )
    except GoogleOAuthLifecycleError as error:
        return _callback_redirect(
            owner_ui_config,
            connected=False,
            reason_code=error.code,
        )
    except Exception:
        return _callback_redirect(
            owner_ui_config,
            connected=False,
            reason_code="oauth_unavailable",
        )

    return _callback_redirect(
        owner_ui_config,
        connected=True,
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
    runtime_config: Annotated[
        GoogleOAuthRuntimeConfig,
        Depends(get_google_oauth_runtime_config),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApiSuccess[OAuthConnectionStatusResponse]:
    return ApiSuccess(
        data=_status_response(
            service.status(),
            runtime_config=runtime_config,
            settings=settings,
        )
    )


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
    runtime_config: Annotated[
        GoogleOAuthRuntimeConfig,
        Depends(get_google_oauth_runtime_config),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApiSuccess[OAuthConnectionStatusResponse]:
    try:
        snapshot = service.disconnect()
    except GoogleOAuthLifecycleError as error:
        _raise_safe(error)
    return ApiSuccess(
        data=_status_response(
            snapshot,
            runtime_config=runtime_config,
            settings=settings,
        )
    )
