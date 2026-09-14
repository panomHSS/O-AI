"""Pure D28 response composition over safe, internal contracts."""

from __future__ import annotations

from app.contracts.ai import AIResult
from app.contracts.command import Response, Result
from app.contracts.response_composition import NormalizedError
from app.services.orchestration_error_normalizer import OrchestrationErrorNormalizer


class ResponseComposer:
    """Render deterministic, safe responses without side effects or execution."""

    _MESSAGES = {
        "AI_ROUTE_UNAVAILABLE": "The selected AI service is unavailable.",
        "AI_ROUTE_REJECTED": "This AI request cannot be processed.",
        "CHATGPT_NOT_CONFIGURED": "The ChatGPT service is not configured.",
        "CHATGPT_UNAVAILABLE": "The ChatGPT service is unavailable.",
        "LOCAL_AI_UNAVAILABLE": "The Local AI service is unavailable.",
        "LOCAL_AI_RESPONSE_FAILED": "The Local AI service could not complete the request.",
        "TOOL_ROUTE_UNAVAILABLE": "The requested tool is unavailable.",
        "OWNER_APPROVAL_REQUIRED": "Owner approval is required before this operation can continue.",
        "OWNER_APPROVAL_DENIED": "Owner approval was denied for this operation.",
        "EXECUTION_AUTHORIZATION_REJECTED": "This execution request cannot be authorized.",
        "TOOL_ROUTE_REJECTED": "This tool request cannot be processed.",
        "TOOL_EXECUTION_FAILED": "The requested operation could not be completed.",
        "INTERNAL_ERROR": "An internal error occurred. Please try again later.",
    }

    def __init__(self, normalizer: OrchestrationErrorNormalizer | None = None) -> None:
        self._normalizer = normalizer or OrchestrationErrorNormalizer()

    def compose_ai_success(self, request_id: str, result: AIResult) -> Response:
        """Compose a successful AI response while preserving the request ID."""
        command_result = Result(
            request_id=request_id,
            status="succeeded",
            output={"content": result.content},
        )
        return Response(request_id=request_id, message=result.content, result=command_result)

    def compose_tool_result(self, result: object) -> Response:
        """Compose successful Tool/Module output or a safe normalized failure."""
        normalized = self._normalizer.normalize_result(result)
        if normalized is not None:
            return self.compose_error(normalized)
        assert isinstance(result, Result)
        return Response(
            request_id=result.request_id,
            message="The requested operation completed.",
            result=Result(
                request_id=result.request_id,
                status="succeeded",
                output=result.output,
            ),
        )

    def compose_error(self, error: NormalizedError) -> Response:
        """Compose a safe error response without propagating raw error details."""
        return Response(
            request_id=error.request_id,
            message=self._MESSAGES[error.code],
            result=Result(
                request_id=error.request_id,
                status=error.status,
                error=error.code,
            ),
        )
