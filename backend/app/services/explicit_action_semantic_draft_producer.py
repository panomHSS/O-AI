"""D176 deterministic explicit /action syntax -> D174 semantic draft producer."""

from __future__ import annotations

from uuid import UUID

from app.contracts.explicit_action_semantic_draft_producer import (
    ExplicitActionSemanticDraftProductionOutcome,
)
from app.contracts.structured_action_semantic_lineage import StructuredActionSemanticDraft

ACTION_PREFIX = "/action"

_FIXED_SEMANTICS: dict[str, str] = {
    "system info": "system_info",
    "system health": "system_health",
    "workspace overview": "workspace_overview",
    "project snapshot": "project_snapshot",
}

_REMAINDER_SEMANTICS: dict[str, tuple[str, str]] = {
    "echo": ("echo", "value"),
    "list": ("workspace_list", "path"),
    "stat": ("workspace_stat", "path"),
    "read": ("workspace_read_text", "path"),
}


def _outcome(
    status: str,
    draft: StructuredActionSemanticDraft | None = None,
) -> ExplicitActionSemanticDraftProductionOutcome:
    reason = {
        "not_applicable": "no_explicit_action_directive",
        "invalid": "explicit_action_directive_invalid",
        "semantic_ready": "structured_action_semantic_draft_ready",
    }[status]
    return ExplicitActionSemanticDraftProductionOutcome(
        status=status,  # type: ignore[arg-type]
        reason_code=reason,
        draft=draft,
    )


class ExplicitActionDirectiveSemanticDraftProducer:
    """Project only the exact historical explicit /action grammar into semantics."""

    def produce(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
    ) -> ExplicitActionSemanticDraftProductionOutcome:
        if type(message) is not str:
            raise TypeError("message must be an exact str.")
        if project_id is not None and not isinstance(project_id, UUID):
            raise TypeError("project_id must be a UUID or None.")

        normalized = message.strip()
        if not self._is_explicit_boundary(normalized):
            return _outcome("not_applicable")

        payload = normalized[len(ACTION_PREFIX):].lstrip()

        semantic_action = _FIXED_SEMANTICS.get(payload)
        if semantic_action is not None:
            if semantic_action == "project_snapshot":
                if project_id is None:
                    draft = StructuredActionSemanticDraft(
                        semantic_action=semantic_action,
                        missing_information=("project_id",),
                    )
                else:
                    draft = StructuredActionSemanticDraft(
                        semantic_action=semantic_action,
                        parameters={"project_id": str(project_id)},
                    )
            else:
                draft = StructuredActionSemanticDraft(semantic_action=semantic_action)
            return _outcome("semantic_ready", draft)

        for verb, (semantic_action, parameter_name) in _REMAINDER_SEMANTICS.items():
            prefix = f"{verb} "
            if not payload.startswith(prefix):
                continue
            remainder = payload[len(prefix):].lstrip()
            if not remainder:
                return _outcome("invalid")
            return _outcome(
                "semantic_ready",
                StructuredActionSemanticDraft(
                    semantic_action=semantic_action,
                    parameters={parameter_name: remainder},
                ),
            )

        return _outcome("invalid")

    @staticmethod
    def _is_explicit_boundary(normalized: str) -> bool:
        if normalized == ACTION_PREFIX:
            return True
        if not normalized.startswith(ACTION_PREFIX):
            return False
        if len(normalized) <= len(ACTION_PREFIX):
            return False
        return normalized[len(ACTION_PREFIX)].isspace()


__all__ = ["ACTION_PREFIX", "ExplicitActionDirectiveSemanticDraftProducer"]
