"""Dispatch validated Project action execution steps."""

from typing import Protocol


class ProjectActionExecutionHandler(Protocol):
    """Execute one validated Project action execution step."""

    def execute(
        self,
        step: dict,
    ) -> None:
        ...


class ProjectActionExecutionDispatcher:
    """Dispatch an execution step to its action-type handler."""

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
        step: dict,
    ) -> None:
        action_type = step.get(
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
            step,
        )