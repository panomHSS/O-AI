"""D129 deterministic Context stabilization and Brain-facing projections."""

from __future__ import annotations

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
)
from app.contracts.cognitive_context_memory import (
    CognitiveContextArtifact,
    CognitiveContextFreezeResult,
    CognitiveMemoryRetrievalArtifact,
)
from app.contracts.context import ContextBundle, ContextLayer
from app.contracts.context_provenance import ContextSnapshot
from app.contracts.context_resolution import ContextResolveRequest
from app.services.context_resolver import ContextResolver
from app.services.context_snapshot import ContextSnapshotError, ContextSnapshotService


class CognitiveContextContractError(Exception):
    """Bounded D129 dependency or projection contract failure."""

    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION

    def __init__(self) -> None:
        super().__init__(self.code)


class CognitiveContextUnstableError(Exception):
    """Bounded D129 terminal failure after one full reacquisition."""

    code = "context_unstable"
    failure_code = CognitiveFailureCode.CONTEXT_UNSTABLE

    def __init__(self) -> None:
        super().__init__(self.code)


def _require_bundle(
    value: object,
    request: ContextResolveRequest,
) -> ContextBundle:
    if not isinstance(value, ContextBundle):
        raise CognitiveContextContractError()
    if value.workspace_scope != request.workspace_scope:
        raise CognitiveContextContractError()
    return value


def _require_snapshot(
    value: object,
    *,
    request: ContextResolveRequest,
    bundle: ContextBundle,
) -> ContextSnapshot:
    if not isinstance(value, ContextSnapshot):
        raise CognitiveContextContractError()
    if value.workspace_scope != request.workspace_scope:
        raise CognitiveContextContractError()
    if tuple(item.item for item in value.items) != bundle.items:
        raise CognitiveContextContractError()
    return value


class CognitiveContextStabilizer:
    """Resolve and verify one Context truth with one bounded reacquisition."""

    def __init__(
        self,
        resolver: ContextResolver,
        snapshot_service: ContextSnapshotService,
    ) -> None:
        self._resolver = resolver
        self._snapshot_service = snapshot_service

    def resolve_and_freeze(
        self,
        request: ContextResolveRequest,
    ) -> CognitiveContextFreezeResult:
        if not isinstance(request, ContextResolveRequest):
            raise CognitiveContextContractError()

        first_bundle = _require_bundle(
            self._resolver.resolve(request),
            request,
        )

        try:
            first_snapshot = self._snapshot_service.capture(first_bundle)
        except ContextSnapshotError as error:
            if error.code != "context_snapshot_source_changed":
                raise
        else:
            snapshot = _require_snapshot(
                first_snapshot,
                request=request,
                bundle=first_bundle,
            )
            return CognitiveContextFreezeResult(
                bundle=first_bundle,
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

        second_bundle = _require_bundle(
            self._resolver.resolve(request),
            request,
        )
        try:
            second_snapshot = self._snapshot_service.capture(second_bundle)
        except ContextSnapshotError as error:
            if error.code == "context_snapshot_source_changed":
                raise CognitiveContextUnstableError() from None
            raise

        snapshot = _require_snapshot(
            second_snapshot,
            request=request,
            bundle=second_bundle,
        )
        return CognitiveContextFreezeResult(
            bundle=second_bundle,
            snapshot=snapshot,
            stabilization_reacquisitions=1,
        )


class CognitiveContextMemoryProjector:
    """Pure D129 projections from final verified Context values."""

    @staticmethod
    def project_context(
        envelope: CognitiveArtifactEnvelope,
        freeze_result: CognitiveContextFreezeResult,
    ) -> CognitiveContextArtifact:
        if not isinstance(freeze_result, CognitiveContextFreezeResult):
            raise CognitiveContextContractError()
        try:
            return CognitiveContextArtifact(
                envelope=envelope,
                snapshot=freeze_result.snapshot,
                stabilization_reacquisitions=(
                    freeze_result.stabilization_reacquisitions
                ),
                stabilization_policy=freeze_result.stabilization_policy,
            )
        except (TypeError, ValueError) as error:
            raise CognitiveContextContractError() from error

    @staticmethod
    def project_memory(
        envelope: CognitiveArtifactEnvelope,
        snapshot: ContextSnapshot,
    ) -> CognitiveMemoryRetrievalArtifact:
        if not isinstance(snapshot, ContextSnapshot):
            raise CognitiveContextContractError()
        if (
            not isinstance(envelope, CognitiveArtifactEnvelope)
            or envelope.workspace_id
            is not snapshot.workspace_scope.workspace_id
            or envelope.context_snapshot_digest != snapshot.snapshot_digest
        ):
            raise CognitiveContextContractError()

        selected_sources = tuple(
            item.item.source
            for item in snapshot.items
            if item.item.source.layer is ContextLayer.MEMORY
        )
        try:
            return CognitiveMemoryRetrievalArtifact(
                envelope=envelope,
                selected_sources=selected_sources,
            )
        except (TypeError, ValueError) as error:
            raise CognitiveContextContractError() from error


__all__ = [
    "CognitiveContextContractError",
    "CognitiveContextMemoryProjector",
    "CognitiveContextStabilizer",
    "CognitiveContextUnstableError",
]
