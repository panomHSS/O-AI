"""Pure D28 classification of orchestration outcomes into safe error codes."""

from __future__ import annotations

from app.adapters.local_ai import LocalAIResponseError, LocalAIUnavailableError
from app.contracts.ai_route import AIRouteDecision, LOCAL_AI_ADAPTER_ID
from app.contracts.command import Result
from app.contracts.execution_authorization import ExecutionAuthorization
from app.contracts.execution_planning import ExecutionPlanningOutcome
from app.contracts.response_composition import NormalizedError
from app.contracts.tool_module_route import ToolModuleRouteDecision
from app.providers.base import ChatConfigurationError, ChatProviderError


class OrchestrationErrorNormalizer:
    """Classify known D24-D27 outcomes without retaining untrusted details."""

    def normalize_ai_route(self, route: object) -> NormalizedError | None:
        """Normalize a terminal D24 route result, or return none when selected."""
        if not isinstance(route, AIRouteDecision):
            return self._internal(getattr(route, "request_id", ""))
        if route.status == "selected":
            return None
        if route.status == "rejected":
            return NormalizedError(route.request_id, "AI_ROUTE_REJECTED", "failed")
        if route.status == "unavailable":
            code = (
                "LOCAL_AI_UNAVAILABLE"
                if route.adapter_id == LOCAL_AI_ADAPTER_ID
                else "AI_ROUTE_UNAVAILABLE"
            )
            return NormalizedError(route.request_id, code, "failed")
        return self._internal(route.request_id)

    def normalize_execution_planning(
        self,
        planning: object,
    ) -> NormalizedError | None:
        """Normalize D35 normal-chat planning without exposing provider detail."""
        if not isinstance(planning, ExecutionPlanningOutcome):
            return self._internal(getattr(planning, "request_id", ""))
        if planning.status == "planned":
            return None
        if planning.status == "rejected":
            return NormalizedError(
                planning.request_id,
                "AI_ROUTE_REJECTED",
                "failed",
            )
        if planning.status == "unavailable":
            code = (
                "LOCAL_AI_UNAVAILABLE"
                if planning.reason_code == "local_ai_unavailable"
                else "AI_ROUTE_UNAVAILABLE"
            )
            return NormalizedError(
                planning.request_id,
                code,
                "failed",
            )
        return self._internal(planning.request_id)

    def normalize_tool_route(self, route: object) -> NormalizedError | None:
        """Normalize a terminal D27 route result, or return none when selected."""
        if not isinstance(route, ToolModuleRouteDecision):
            return self._internal(getattr(route, "request_id", ""))
        if route.status == "selected":
            return None
        if route.status == "unavailable":
            return NormalizedError(route.request_id, "TOOL_ROUTE_UNAVAILABLE", "failed")
        if route.status == "blocked":
            return NormalizedError(route.request_id, "OWNER_APPROVAL_REQUIRED", "blocked")
        if route.status == "rejected":
            return NormalizedError(route.request_id, "TOOL_ROUTE_REJECTED", "failed")
        return self._internal(route.request_id)

    def normalize_execution_authorization(
        self,
        authorization: object,
    ) -> NormalizedError | None:
        'Normalize D36 authorization without exposing approval/plan details.'
        if not isinstance(authorization, ExecutionAuthorization):
            return self._internal(
                getattr(authorization, "request_id", "")
            )
        if authorization.status == "authorized":
            return None
        if authorization.status == "blocked":
            if authorization.reason_code == "owner_approval_required":
                return NormalizedError(
                    authorization.request_id,
                    "OWNER_APPROVAL_REQUIRED",
                    "blocked",
                )
            if authorization.reason_code == "owner_approval_denied":
                return NormalizedError(
                    authorization.request_id,
                    "OWNER_APPROVAL_DENIED",
                    "blocked",
                )
            return self._internal(authorization.request_id)
        if authorization.status == "rejected":
            return NormalizedError(
                authorization.request_id,
                "EXECUTION_AUTHORIZATION_REJECTED",
                "failed",
            )
        return self._internal(authorization.request_id)

    def normalize_result(self, result: object) -> NormalizedError | None:
        """Normalize terminal Tool/Module results without exposing adapter detail."""
        if not isinstance(result, Result):
            return self._internal(getattr(result, "request_id", ""))
        if result.status == "succeeded":
            return None
        if result.status == "blocked":
            return NormalizedError(result.request_id, "OWNER_APPROVAL_REQUIRED", "blocked")
        if result.status == "failed":
            return NormalizedError(result.request_id, "TOOL_EXECUTION_FAILED", "failed")
        return self._internal(result.request_id)

    def normalize_exception(self, request_id: str, error: BaseException) -> NormalizedError:
        """Normalize known adapter errors and fail closed for every other error."""
        if isinstance(error, ChatConfigurationError):
            return NormalizedError(request_id, "CHATGPT_NOT_CONFIGURED", "failed")
        if isinstance(error, ChatProviderError):
            return NormalizedError(request_id, "CHATGPT_UNAVAILABLE", "failed")
        if isinstance(error, LocalAIUnavailableError):
            return NormalizedError(request_id, "LOCAL_AI_UNAVAILABLE", "failed")
        if isinstance(error, LocalAIResponseError):
            return NormalizedError(request_id, "LOCAL_AI_RESPONSE_FAILED", "failed")
        return self._internal(request_id)

    @staticmethod
    def _internal(request_id: object) -> NormalizedError:
        return NormalizedError(
            request_id=request_id if isinstance(request_id, str) else "",
            code="INTERNAL_ERROR",
            status="failed",
        )
