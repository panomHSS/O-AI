"""Dispatch validated Project action execution steps."""

from typing import Protocol
from app.services.project_action_execution_context import (
    ProjectActionExecutionContext,
)


class ProjectActionExecutionHandler(Protocol):
    """Execute one validated Project action execution context."""

    def execute(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        ...


class ProjectActionExecutionDispatcher:
    """Dispatch an execution context to its action-type handler."""

    def __init__(
        self,
        *,
        handlers: dict[
            str,
            ProjectActionExecutionHandler,
        ],
    ) -> None:
        self._handlers = dict(
            handlers
        )

    def dispatch(
        self,
        context: ProjectActionExecutionContext,
    ) -> None:
        action_type = context.step.get(
            "action_type"
        )

        handler = self._handlers.get(
            action_type
        )

        if handler is None:
            raise ValueError(
                "Unsupported execution action type."
            )

        handler.execute(
            context,
        )