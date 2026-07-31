import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.api import ApiError, ApiErrorDetail
from app.services.chat import ChatConfigurationError, ChatProviderError

logger = logging.getLogger(__name__)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Create a safe, consistent API error response."""
    body = ApiError(error=ApiErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def unexpected_error_response(request: Request, error: Exception) -> JSONResponse:
    """Log internal detail while returning a safe public response."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unexpected API error [request_id=%s]", request_id, exc_info=error)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception mappings at the API boundary."""

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "Request validation failed.",
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
        messages = {
            status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
            status.HTTP_405_METHOD_NOT_ALLOWED: "The requested method is not allowed.",
        }
        return error_response(error.status_code, f"HTTP_{error.status_code}", messages.get(error.status_code, "The request could not be completed."))

    @app.exception_handler(ChatConfigurationError)
    async def handle_chat_configuration_error(_: Request, error: ChatConfigurationError) -> JSONResponse:
        return error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "CHAT_NOT_CONFIGURED", str(error))

    @app.exception_handler(ChatProviderError)
    async def handle_chat_provider_error(_: Request, error: ChatProviderError) -> JSONResponse:
        return error_response(status.HTTP_502_BAD_GATEWAY, "CHAT_PROVIDER_UNAVAILABLE", str(error))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        return unexpected_error_response(request, error)
