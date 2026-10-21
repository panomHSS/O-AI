"""D172 deterministic structured semantic action -> D168 candidate producer."""

from __future__ import annotations

from uuid import UUID

from app.contracts.structured_action_candidate_producer import (
    StructuredActionCandidateProductionOutcome,
    StructuredActionSemanticInput,
)
from app.contracts.structured_action_intent_proposal import (
    StructuredActionIntentCandidate,
)


# Server-owned semantic-to-route catalog. This is deliberately separate from
# D44 capability permission policy and grants no permission or execution right.
_ROUTE_CATALOG: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "echo": ("tool", "tool.standard.echo", "echo", ("value",)),
    "project_snapshot": (
        "module",
        "module.project.snapshot",
        "get_snapshot",
        ("project_id",),
    ),
    "system_health": ("tool", "tool.system.health", "check", ()),
    "system_info": ("tool", "tool.system.info", "get_info", ()),
    "workspace_list": ("tool", "tool.filesystem.list", "list", ("path",)),
    "workspace_overview": (
        "module",
        "module.workspace.overview",
        "inspect",
        (),
    ),
    "workspace_read_text": (
        "tool",
        "tool.filesystem.read_text",
        "read_text",
        ("path",),
    ),
    "workspace_stat": ("tool", "tool.filesystem.stat", "stat", ("path",)),
}


def _validate_parameter(
    semantic_action: str,
    name: str,
    value: object,
) -> None:
    if semantic_action == "project_snapshot" and name == "project_id":
        if type(value) is not str:
            raise ValueError("structured_action_semantic_parameter_invalid")
        try:
            parsed = UUID(value)
        except (ValueError, AttributeError):
            raise ValueError(
                "structured_action_semantic_parameter_invalid"
            ) from None
        if str(parsed) != value:
            raise ValueError("structured_action_semantic_parameter_invalid")
        return

    if name == "path":
        if type(value) is not str or not value:
            raise ValueError("structured_action_semantic_parameter_invalid")
        return

    if semantic_action == "echo" and name == "value":
        if type(value) is not str:
            raise ValueError("structured_action_semantic_parameter_invalid")
        return

    raise ValueError("structured_action_semantic_parameter_invalid")


class StructuredActionCandidateProducer:
    """Project structured semantic actions into D168 candidates only."""

    def produce(
        self,
        semantic: StructuredActionSemanticInput | None,
    ) -> StructuredActionCandidateProductionOutcome:
        if semantic is None:
            return StructuredActionCandidateProductionOutcome(
                status="not_applicable",
                reason_code="no_structured_action_semantics",
            )
        if not isinstance(semantic, StructuredActionSemanticInput):
            raise TypeError(
                "semantic must be a StructuredActionSemanticInput or None."
            )

        route = _ROUTE_CATALOG.get(semantic.semantic_action)
        if route is None:
            return StructuredActionCandidateProductionOutcome(
                status="unsupported",
                reason_code="structured_action_semantic_unsupported",
            )

        target_kind, adapter_id, operation, required_parameters = route
        allowed = frozenset(required_parameters)
        actual = frozenset(semantic.parameters)

        unexpected = actual - allowed
        if unexpected:
            raise ValueError("structured_action_semantic_parameters_unexpected")

        missing = set(semantic.missing_information)
        for name in required_parameters:
            if name not in semantic.parameters:
                missing.add(name)
                continue
            _validate_parameter(
                semantic.semantic_action,
                name,
                semantic.parameters[name],
            )

        candidate = StructuredActionIntentCandidate(
            source_turn_id=semantic.source_turn_id,
            source_artifact_digest=semantic.source_artifact_digest,
            target_kind=target_kind,
            adapter_id=adapter_id,
            operation=operation,
            parameters=semantic.parameters,
            missing_information=tuple(sorted(missing)),
        )

        if candidate.missing_information:
            return StructuredActionCandidateProductionOutcome(
                status="needs_clarification",
                reason_code="structured_action_information_missing",
                candidate=candidate,
            )

        return StructuredActionCandidateProductionOutcome(
            status="candidate_ready",
            reason_code="structured_action_candidate_ready",
            candidate=candidate,
        )


__all__ = ["StructuredActionCandidateProducer"]