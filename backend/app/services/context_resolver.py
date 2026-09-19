"""D95 deterministic workspace-safe Context resolution and budgeting."""

from __future__ import annotations

from collections.abc import Sequence

from app.contracts.context import ContextBundle, ContextItem, ContextLayer
from app.contracts.context_resolution import (
    ContextBudgetCounter,
    ContextBudgetPolicy,
    ContextLayerBudget,
    ContextResolveRequest,
)
from app.services.context_sources import (
    ContextCandidate,
    ContextSourcePort,
    ContextSourceReadError,
)


class ContextResolutionError(Exception):
    """Bounded internal D95 resolution failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ContextResolver:
    """Resolve four D94 Context layers deterministically under one budget."""

    def __init__(
        self,
        *,
        conversation_source: ContextSourcePort,
        project_source: ContextSourcePort,
        memory_source: ContextSourcePort,
        knowledge_source: ContextSourcePort,
        policy: ContextBudgetPolicy,
        counter: ContextBudgetCounter,
    ) -> None:
        self._conversation_source = conversation_source
        self._project_source = project_source
        self._memory_source = memory_source
        self._knowledge_source = knowledge_source
        self._policy = policy
        self._counter = counter

    def resolve(self, request: ContextResolveRequest) -> ContextBundle:
        if not isinstance(request, ContextResolveRequest):
            raise ContextResolutionError("context_resolve_request_invalid")

        selected_items: list[ContextItem] = []
        layers = (
            (ContextLayer.CONVERSATION, self._conversation_source, self._policy.conversation),
            (ContextLayer.PROJECT, self._project_source, self._policy.project),
            (ContextLayer.MEMORY, self._memory_source, self._policy.memory),
            (ContextLayer.KNOWLEDGE, self._knowledge_source, self._policy.knowledge),
        )

        for layer, source, budget in layers:
            candidates = self._read_candidates(
                source=source,
                layer=layer,
                request=request,
                candidate_limit=budget.candidate_limit,
            )
            candidates = self._validate_and_dedupe(
                candidates=candidates,
                expected_layer=layer,
                request=request,
            )
            admitted = self._admit_whole_items(candidates, budget)
            admitted.sort(key=lambda item: item.order_key)
            selected_items.extend(
                ContextItem(
                    source=item.source,
                    text=item.text,
                    label=item.label,
                )
                for item in admitted
            )

        try:
            return ContextBundle(
                workspace_scope=request.workspace_scope,
                items=tuple(selected_items),
            )
        except (TypeError, ValueError) as error:
            raise ContextResolutionError("context_bundle_invalid") from error

    def _read_candidates(
        self,
        *,
        source: ContextSourcePort,
        layer: ContextLayer,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]:
        try:
            candidates = source.candidates(request, candidate_limit)
        except ContextSourceReadError as error:
            raise ContextResolutionError(error.code) from None
        except Exception:
            raise ContextResolutionError(
                f"context_{layer.value}_unavailable"
            ) from None

        if not isinstance(candidates, Sequence):
            raise ContextResolutionError(
                f"context_{layer.value}_candidates_invalid"
            )
        return candidates[:candidate_limit]

    @staticmethod
    def _validate_and_dedupe(
        *,
        candidates: Sequence[ContextCandidate],
        expected_layer: ContextLayer,
        request: ContextResolveRequest,
    ) -> list[ContextCandidate]:
        unique: list[ContextCandidate] = []
        seen: dict[
            tuple[object, ContextLayer, str],
            tuple[str, str | None],
        ] = {}

        for candidate in candidates:
            if not isinstance(candidate, ContextCandidate):
                raise ContextResolutionError("context_candidate_invalid")
            if candidate.source.layer is not expected_layer:
                raise ContextResolutionError("context_candidate_layer_mismatch")
            if (
                candidate.source.workspace_id
                is not request.workspace_scope.workspace_id
            ):
                raise ContextResolutionError(
                    "context_candidate_workspace_mismatch"
                )

            identity = (
                candidate.source.workspace_id,
                candidate.source.layer,
                candidate.source.source_id,
            )
            projection = (candidate.text, candidate.label)
            previous = seen.get(identity)

            if previous is None:
                seen[identity] = projection
                unique.append(candidate)
            elif previous != projection:
                raise ContextResolutionError(
                    "context_candidate_identity_conflict"
                )

        return unique

    def _admit_whole_items(
        self,
        candidates: Sequence[ContextCandidate],
        budget: ContextLayerBudget,
    ) -> list[ContextCandidate]:
        selected: list[ContextCandidate] = []
        consumed = 0

        for candidate in candidates:
            if len(selected) >= budget.max_items:
                break

            try:
                cost = self._counter.count(candidate.text)
            except Exception:
                raise ContextResolutionError(
                    "context_budget_counter_failed"
                ) from None

            if type(cost) is not int or cost < 0:
                raise ContextResolutionError(
                    "context_budget_counter_invalid"
                )

            if cost > budget.max_item_units:
                continue
            if consumed + cost > budget.max_units:
                continue

            selected.append(candidate)
            consumed += cost

        return selected


__all__ = ["ContextResolutionError", "ContextResolver"]
