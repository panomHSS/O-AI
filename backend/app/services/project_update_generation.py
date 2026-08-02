from dataclasses import dataclass

from app.schemas.project_update_generation import (
    ProjectUpdateGenerationResult,
    ProjectUpdateProposalCandidate,
)
from app.services.project_context import ProjectContext


@dataclass(frozen=True)
class ProjectUpdateGenerationInput:
    """Provider-neutral inputs for one Project update analysis."""

    user_message: str
    assistant_reply: str
    project_context: ProjectContext | None


class ProjectUpdateProposalGenerator:
    """Conservatively detect explicit Project progress from one chat turn."""

    def generate(
        self,
        input_data: ProjectUpdateGenerationInput,
    ) -> ProjectUpdateGenerationResult:
        context = input_data.project_context

        if context is None:
            return ProjectUpdateGenerationResult()

        user_message = self._normalize(input_data.user_message)

        if not user_message:
            return ProjectUpdateGenerationResult()

        summary = self._explicit_summary(user_message)
        next_action = self._explicit_next_action(user_message)

        if summary is None and next_action is None:
            return ProjectUpdateGenerationResult()

        if summary == context.current_summary:
            summary = None

        if next_action == context.next_action:
            next_action = None

        if summary is None and next_action is None:
            return ProjectUpdateGenerationResult()

        return ProjectUpdateGenerationResult(
            candidate=ProjectUpdateProposalCandidate(
                proposed_summary=summary,
                proposed_next_action=next_action,
                reason=(
                    "The owner explicitly stated Project progress "
                    "or a next action in the conversation."
                ),
            )
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.split())

    def _explicit_summary(self, message: str) -> str | None:
        prefixes = (
            "progress:",
            "project progress:",
            "summary:",
        )
        return self._extract_prefixed_value(message, prefixes, 4000)

    def _explicit_next_action(self, message: str) -> str | None:
        prefixes = (
            "next action:",
            "next:",
        )
        return self._extract_prefixed_value(message, prefixes, 512)

    @staticmethod
    def _extract_prefixed_value(
        message: str,
        prefixes: tuple[str, ...],
        limit: int,
    ) -> str | None:
        lowered = message.lower()

        for prefix in prefixes:
            if lowered.startswith(prefix):
                value = message[len(prefix):].strip()
                return value[:limit] or None

        return None