"""D129 immutable Brain-facing Context and Memory Retrieval contracts.

These contracts project the existing D94-D97 Context substrate into bounded
cognitive metadata. They grant no authentication, authorization, approval,
provider/model selection, credential access, persistence, Memory mutation,
tool permission, or execution authority.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.context import (
    ContextBundle,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_provenance import ContextSnapshot


D129_CONTEXT_ARTIFACT_TYPE = "cognitive.context"
D129_CONTEXT_CONTRACT_VERSION = "o-ai.cognitive-context.v1"
D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE = "cognitive.memory_retrieval"
D129_MEMORY_RETRIEVAL_CONTRACT_VERSION = "o-ai.cognitive-memory-retrieval.v1"
D129_STABILIZATION_POLICY = "single_full_reacquisition_on_source_change.v1"
D129_MAX_STABILIZATION_REACQUISITIONS = 1


def _validate_reacquisitions(value: object) -> int:
    if type(value) is not int or value not in {0, 1}:
        raise ValueError("cognitive_context_reacquisitions_invalid")
    return value


def _validate_policy(value: object) -> str:
    if value != D129_STABILIZATION_POLICY:
        raise ValueError("cognitive_context_stabilization_policy_invalid")
    return D129_STABILIZATION_POLICY


def _require_envelope(
    envelope: object,
    *,
    organ: CognitiveOrgan,
    artifact_type: str,
    contract_version: str,
    code: str,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        raise ValueError(code)
    if (
        envelope.producer_organ is not organ
        or envelope.artifact_type != artifact_type
        or envelope.contract_version != contract_version
        or envelope.status is not CognitiveOrganStatus.READY
        or envelope.context_snapshot_digest is None
        or envelope.model_binding_reference is not None
    ):
        raise ValueError(code)
    return envelope


def _snapshot_items(snapshot: ContextSnapshot) -> tuple[object, ...]:
    return tuple(snapshot_item.item for snapshot_item in snapshot.items)


@dataclass(frozen=True, slots=True)
class CognitiveContextFreezeResult:
    """Successful final D129 Context selection and verified frozen snapshot."""

    bundle: ContextBundle
    snapshot: ContextSnapshot
    stabilization_reacquisitions: int
    stabilization_policy: str = D129_STABILIZATION_POLICY

    def __post_init__(self) -> None:
        if not isinstance(self.bundle, ContextBundle):
            raise ValueError("cognitive_context_bundle_invalid")
        if not isinstance(self.snapshot, ContextSnapshot):
            raise ValueError("cognitive_context_snapshot_invalid")
        _validate_reacquisitions(self.stabilization_reacquisitions)
        _validate_policy(self.stabilization_policy)
        if self.bundle.workspace_scope != self.snapshot.workspace_scope:
            raise ValueError("cognitive_context_workspace_mismatch")
        if self.bundle.items != _snapshot_items(self.snapshot):
            raise ValueError("cognitive_context_snapshot_items_mismatch")


@dataclass(frozen=True, slots=True)
class CognitiveContextArtifact:
    """Brain-facing reference to one existing verified D96 ContextSnapshot."""

    envelope: CognitiveArtifactEnvelope
    snapshot: ContextSnapshot
    stabilization_reacquisitions: int
    stabilization_policy: str = D129_STABILIZATION_POLICY

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.CONTEXT_INTELLIGENCE,
            artifact_type=D129_CONTEXT_ARTIFACT_TYPE,
            contract_version=D129_CONTEXT_CONTRACT_VERSION,
            code="cognitive_context_envelope_invalid",
        )
        if not isinstance(self.snapshot, ContextSnapshot):
            raise ValueError("cognitive_context_snapshot_invalid")
        _validate_reacquisitions(self.stabilization_reacquisitions)
        _validate_policy(self.stabilization_policy)
        if (
            envelope.workspace_id
            is not self.snapshot.workspace_scope.workspace_id
        ):
            raise ValueError("cognitive_context_workspace_mismatch")
        if envelope.context_snapshot_digest != self.snapshot.snapshot_digest:
            raise ValueError("cognitive_context_digest_mismatch")


@dataclass(frozen=True, slots=True)
class CognitiveMemoryRetrievalArtifact:
    """Memory source identities admitted into one final frozen ContextSnapshot."""

    envelope: CognitiveArtifactEnvelope
    selected_sources: (
        tuple[ContextSourceRef, ...] | Sequence[ContextSourceRef]
    ) = ()

    def __post_init__(self) -> None:
        envelope = _require_envelope(
            self.envelope,
            organ=CognitiveOrgan.MEMORY_RETRIEVAL,
            artifact_type=D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE,
            contract_version=D129_MEMORY_RETRIEVAL_CONTRACT_VERSION,
            code="cognitive_memory_retrieval_envelope_invalid",
        )
        if (
            isinstance(self.selected_sources, (str, bytes, bytearray))
            or not isinstance(self.selected_sources, Sequence)
        ):
            raise ValueError("cognitive_memory_retrieval_sources_invalid")

        selected_sources = tuple(self.selected_sources)
        seen: set[tuple[object, object, str]] = set()
        for source in selected_sources:
            if not isinstance(source, ContextSourceRef):
                raise ValueError("cognitive_memory_retrieval_sources_invalid")
            if source.layer is not ContextLayer.MEMORY:
                raise ValueError("cognitive_memory_retrieval_layer_invalid")
            if source.workspace_id is not envelope.workspace_id:
                raise ValueError("cognitive_memory_retrieval_workspace_mismatch")
            identity = (
                source.workspace_id,
                source.layer,
                source.source_id,
            )
            if identity in seen:
                raise ValueError("cognitive_memory_retrieval_duplicate_source")
            seen.add(identity)

        object.__setattr__(self, "selected_sources", selected_sources)


__all__ = [
    "D129_CONTEXT_ARTIFACT_TYPE",
    "D129_CONTEXT_CONTRACT_VERSION",
    "D129_MAX_STABILIZATION_REACQUISITIONS",
    "D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE",
    "D129_MEMORY_RETRIEVAL_CONTRACT_VERSION",
    "D129_STABILIZATION_POLICY",
    "CognitiveContextArtifact",
    "CognitiveContextFreezeResult",
    "CognitiveMemoryRetrievalArtifact",
]
