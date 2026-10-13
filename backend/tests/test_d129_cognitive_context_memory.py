from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
import unittest
from uuid import UUID

from pydantic import ValidationError

from app.contracts.cognitive_brain import (
    CognitiveArtifactEnvelope,
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_context_memory import (
    D129_CONTEXT_ARTIFACT_TYPE,
    D129_CONTEXT_CONTRACT_VERSION,
    D129_MAX_STABILIZATION_REACQUISITIONS,
    D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE,
    D129_MEMORY_RETRIEVAL_CONTRACT_VERSION,
    D129_STABILIZATION_POLICY,
    CognitiveContextArtifact,
    CognitiveContextFreezeResult,
    CognitiveMemoryRetrievalArtifact,
)
from app.contracts.context import (
    ContextBundle,
    ContextItem,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_provenance import (
    ContextSnapshot,
    ContextSnapshotItem,
    ContextSourceProvenance,
    compute_context_snapshot_digest,
    context_text_sha256,
)
from app.contracts.context_resolution import ContextResolveRequest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.intelligence.context import (
    CognitiveWorkingState,
    ConversationContext,
    ExecutionContext,
    IntelligenceContext,
    KnowledgeContext,
    RequestContext,
    ResponseContext,
)
from app.services.cognitive_context_memory import (
    CognitiveContextMemoryProjector,
    CognitiveContextStabilizer,
    CognitiveContextUnstableError,
)
from app.services.cognitive_working_state import CognitiveTurnGuard
from app.services.context_resolver import ContextResolutionError
from app.services.context_snapshot import ContextSnapshotError

from tests.test_d128_cognitive_working_state import (
    CONVERSATION_ID,
    TURN_ID,
    make_attention,
    make_binding,
    make_envelope as make_d128_envelope,
    make_perception,
    make_task,
)


NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def make_context_envelope(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str,
    organ: CognitiveOrgan = CognitiveOrgan.CONTEXT_INTELLIGENCE,
    artifact_type: str = D129_CONTEXT_ARTIFACT_TYPE,
    contract_version: str = D129_CONTEXT_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    model_binding_reference: str | None = None,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=digest,
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def make_memory_envelope(
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    digest: str,
    organ: CognitiveOrgan = CognitiveOrgan.MEMORY_RETRIEVAL,
    artifact_type: str = D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE,
    contract_version: str = D129_MEMORY_RETRIEVAL_CONTRACT_VERSION,
    status: CognitiveOrganStatus = CognitiveOrganStatus.READY,
    model_binding_reference: str | None = None,
) -> CognitiveArtifactEnvelope:
    return CognitiveArtifactEnvelope(
        turn_id=turn_id,
        artifact_type=artifact_type,
        contract_version=contract_version,
        producer_organ=organ,
        workspace_id=workspace_id,
        context_snapshot_digest=digest,
        created_at=NOW,
        status=status,
        model_binding_reference=model_binding_reference,
    )


def make_item(
    *,
    layer: ContextLayer = ContextLayer.CONVERSATION,
    source_id: str = "source-1",
    text: str = "context text",
    label: str | None = "context",
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextItem:
    return ContextItem(
        source=ContextSourceRef(
            workspace_id=workspace_id,
            layer=layer,
            source_id=source_id,
        ),
        text=text,
        label=label,
    )


def make_bundle_snapshot(
    *,
    items: tuple[ContextItem, ...] | None = None,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
    captured_at: datetime = NOW,
) -> tuple[ContextBundle, ContextSnapshot]:
    actual_items = (
        items
        if items is not None
        else (
            make_item(
                workspace_id=workspace_id,
                source_id="source-1",
                label="conversation_user",
            ),
        )
    )
    scope = WorkspaceScope(workspace_id)
    bundle = ContextBundle(
        workspace_scope=scope,
        items=actual_items,
    )
    snapshot_items = tuple(
        ContextSnapshotItem(
            item=item,
            provenance=ContextSourceProvenance(
                source=item.source,
                content_sha256=context_text_sha256(item.text),
            ),
        )
        for item in actual_items
    )
    digest = compute_context_snapshot_digest(
        workspace_scope=scope,
        captured_at=captured_at,
        items=snapshot_items,
    )
    snapshot = ContextSnapshot(
        workspace_scope=scope,
        captured_at=captured_at,
        items=snapshot_items,
        snapshot_digest=digest,
    )
    return bundle, snapshot


def make_context_artifact(
    *,
    snapshot: ContextSnapshot | None = None,
    count: int = 0,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> CognitiveContextArtifact:
    if snapshot is None:
        _, snapshot = make_bundle_snapshot(workspace_id=workspace_id)
    envelope = make_context_envelope(
        turn_id=turn_id,
        workspace_id=workspace_id,
        digest=snapshot.snapshot_digest,
    )
    return CognitiveContextArtifact(
        envelope=envelope,
        snapshot=snapshot,
        stabilization_reacquisitions=count,
    )


def make_memory_artifact(
    context: CognitiveContextArtifact,
    *,
    turn_id: str = TURN_ID,
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> CognitiveMemoryRetrievalArtifact:
    selected = tuple(
        entry.item.source
        for entry in context.snapshot.items
        if entry.item.source.layer is ContextLayer.MEMORY
    )
    return CognitiveMemoryRetrievalArtifact(
        envelope=make_memory_envelope(
            turn_id=turn_id,
            workspace_id=workspace_id,
            digest=context.snapshot.snapshot_digest,
        ),
        selected_sources=selected,
    )


def make_working_state(
    *,
    context: CognitiveContextArtifact | None = None,
    memory_retrieval: CognitiveMemoryRetrievalArtifact | None = None,
    working_digest: str | None = None,
    perception=None,
    attention=None,
    task=None,
) -> CognitiveWorkingState:
    binding = make_binding()
    return CognitiveWorkingState(
        request=RequestContext(
            request_id=binding.turn_id,
            question="hello",
            conversation_id=binding.conversation_id,
            project_id=binding.project_id,
        ),
        conversation=ConversationContext(),
        knowledge=KnowledgeContext(),
        intelligence=IntelligenceContext(),
        response=ResponseContext(),
        binding=binding,
        working_memory_envelope=make_d128_envelope(digest=working_digest),
        perception=perception,
        attention=attention,
        task=task,
        context=context,
        memory_retrieval=memory_retrieval,
    )


class SequenceResolver:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[ContextResolveRequest] = []

    def resolve(self, request: ContextResolveRequest) -> object:
        self.calls.append(request)
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class SequenceSnapshotService:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[ContextBundle] = []

    def capture(self, bundle: ContextBundle) -> object:
        self.calls.append(bundle)
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_request(
    workspace_id: WorkspaceId = WorkspaceId.PERSONAL,
) -> ContextResolveRequest:
    return ContextResolveRequest(
        workspace_scope=WorkspaceScope(workspace_id),
        query="hello",
        conversation_id=str(CONVERSATION_ID),
    )


def memory_snapshot() -> tuple[ContextBundle, ContextSnapshot]:
    items = (
        make_item(
            layer=ContextLayer.CONVERSATION,
            source_id="source-1",
            label="conversation_user",
        ),
        make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-1",
            text='{"key":"one","value":"x","value_type":"STRING"}',
            label="memory",
        ),
        make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-2",
            text='{"key":"two","value":"y","value_type":"STRING"}',
            label="memory",
        ),
    )
    return make_bundle_snapshot(items=items)


class D129CognitiveContextMemoryFunctionalTests(unittest.TestCase):
    def test_f01_exact_d129_constants(self) -> None:
        self.assertEqual(D129_CONTEXT_ARTIFACT_TYPE, "cognitive.context")
        self.assertEqual(
            D129_CONTEXT_CONTRACT_VERSION,
            "o-ai.cognitive-context.v1",
        )
        self.assertEqual(
            D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE,
            "cognitive.memory_retrieval",
        )
        self.assertEqual(
            D129_MEMORY_RETRIEVAL_CONTRACT_VERSION,
            "o-ai.cognitive-memory-retrieval.v1",
        )
        self.assertEqual(
            D129_STABILIZATION_POLICY,
            "single_full_reacquisition_on_source_change.v1",
        )
        self.assertEqual(D129_MAX_STABILIZATION_REACQUISITIONS, 1)

    def test_f02_valid_freeze_result_zero_reacquisition(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        self.assertEqual(result.stabilization_reacquisitions, 0)

    def test_f03_valid_freeze_result_one_reacquisition(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 1)
        self.assertEqual(result.stabilization_reacquisitions, 1)

    def test_f04_freeze_result_preserves_exact_successful_bundle(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        self.assertIs(result.bundle, bundle)

    def test_f05_freeze_result_preserves_exact_successful_snapshot(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        self.assertIs(result.snapshot, snapshot)

    def test_f06_valid_context_artifact_zero_reacquisition(self) -> None:
        artifact = make_context_artifact(count=0)
        self.assertEqual(artifact.stabilization_reacquisitions, 0)

    def test_f07_valid_context_artifact_one_reacquisition(self) -> None:
        artifact = make_context_artifact(count=1)
        self.assertEqual(artifact.stabilization_reacquisitions, 1)

    def test_f08_context_artifact_retains_exact_d96_snapshot(self) -> None:
        _, snapshot = make_bundle_snapshot()
        artifact = make_context_artifact(snapshot=snapshot)
        self.assertIs(artifact.snapshot, snapshot)

    def test_f09_valid_empty_memory_retrieval_artifact(self) -> None:
        context = make_context_artifact()
        artifact = make_memory_artifact(context)
        self.assertEqual(artifact.selected_sources, ())

    def test_f10_valid_memory_retrieval_artifact_one_source(self) -> None:
        item = make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-1",
            label="memory",
        )
        _, snapshot = make_bundle_snapshot(items=(item,))
        context = make_context_artifact(snapshot=snapshot)
        artifact = make_memory_artifact(context)
        self.assertEqual(artifact.selected_sources, (item.source,))

    def test_f11_memory_selected_sources_normalize_to_tuple(self) -> None:
        item = make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-1",
            label="memory",
        )
        _, snapshot = make_bundle_snapshot(items=(item,))
        artifact = CognitiveMemoryRetrievalArtifact(
            envelope=make_memory_envelope(digest=snapshot.snapshot_digest),
            selected_sources=[item.source],
        )
        self.assertIsInstance(artifact.selected_sources, tuple)

    def test_f12_memory_selected_source_order_preserved(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        artifact = make_memory_artifact(context)
        self.assertEqual(
            [source.source_id for source in artifact.selected_sources],
            ["memory-1", "memory-2"],
        )

    def test_f13_first_attempt_stable_resolution_succeeds(self) -> None:
        request = make_request()
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle),  # type: ignore[arg-type]
            SequenceSnapshotService(snapshot),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIs(result.snapshot, snapshot)

    def test_f14_stable_path_calls_resolver_exactly_once(self) -> None:
        request = make_request()
        bundle, snapshot = make_bundle_snapshot()
        resolver = SequenceResolver(bundle)
        CognitiveContextStabilizer(
            resolver,  # type: ignore[arg-type]
            SequenceSnapshotService(snapshot),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 1)

    def test_f15_stable_path_calls_snapshot_service_exactly_once(self) -> None:
        request = make_request()
        bundle, snapshot = make_bundle_snapshot()
        snapshots = SequenceSnapshotService(snapshot)
        CognitiveContextStabilizer(
            SequenceResolver(bundle),  # type: ignore[arg-type]
            snapshots,  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(len(snapshots.calls), 1)

    def test_f16_stable_path_reports_zero_reacquisition(self) -> None:
        request = make_request()
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle),  # type: ignore[arg-type]
            SequenceSnapshotService(snapshot),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(result.stabilization_reacquisitions, 0)

    def test_f17_stable_path_returns_exact_first_bundle_snapshot(self) -> None:
        request = make_request()
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle),  # type: ignore[arg-type]
            SequenceSnapshotService(snapshot),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIs(result.bundle, bundle)
        self.assertIs(result.snapshot, snapshot)

    def test_f18_first_source_change_triggers_second_resolve(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(
                make_item(
                    source_id="source-2",
                    text="new context",
                    label="conversation_user",
                ),
            )
        )
        resolver = SequenceResolver(bundle1, bundle2)
        CognitiveContextStabilizer(
            resolver,  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 2)

    def test_f19_stabilization_reuses_exact_same_request_object(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        resolver = SequenceResolver(bundle1, bundle2)
        CognitiveContextStabilizer(
            resolver,  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIs(resolver.calls[0], request)
        self.assertIs(resolver.calls[1], request)

    def test_f20_stabilization_uses_exact_same_resolver_instance(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        resolver = SequenceResolver(bundle1, bundle2)
        stabilizer = CognitiveContextStabilizer(
            resolver,  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        )
        stabilizer.resolve_and_freeze(request)
        self.assertIs(stabilizer._resolver, resolver)

    def test_f21_stabilization_uses_exact_same_snapshot_service_instance(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        snapshots = SequenceSnapshotService(
            ContextSnapshotError("context_snapshot_source_changed"),
            snapshot2,
        )
        stabilizer = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            snapshots,  # type: ignore[arg-type]
        )
        stabilizer.resolve_and_freeze(request)
        self.assertIs(stabilizer._snapshot_service, snapshots)

    def test_f22_successful_second_attempt_reports_one_reacquisition(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(result.stabilization_reacquisitions, 1)

    def test_f23_failed_first_bundle_is_not_returned(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIsNot(result.bundle, bundle1)

    def test_f24_successful_second_bundle_returned_exactly(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIs(result.bundle, bundle2)

    def test_f25_successful_second_snapshot_returned_exactly(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertIs(result.snapshot, snapshot2)

    def test_f26_no_third_resolution_after_second_attempt_success(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        resolver = SequenceResolver(bundle1, bundle2, AssertionError("third"))
        CognitiveContextStabilizer(
            resolver,  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 2)

    def test_f27_second_source_change_raises_context_unstable(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, _ = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        with self.assertRaises(CognitiveContextUnstableError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
                SequenceSnapshotService(
                    ContextSnapshotError("context_snapshot_source_changed"),
                    ContextSnapshotError("context_snapshot_source_changed"),
                ),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_f28_unstable_error_exposes_context_unstable(self) -> None:
        error = CognitiveContextUnstableError()
        self.assertIs(
            error.failure_code,
            CognitiveFailureCode.CONTEXT_UNSTABLE,
        )

    def test_f29_first_resolver_error_propagates_without_stabilization(self) -> None:
        request = make_request()
        error = ContextResolutionError("context_memory_unavailable")
        resolver = SequenceResolver(error)
        with self.assertRaises(ContextResolutionError) as caught:
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(resolver.calls), 1)

    def test_f30_first_non_source_change_snapshot_error_propagates(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        error = ContextSnapshotError("context_snapshot_source_unavailable")
        with self.assertRaises(ContextSnapshotError) as caught:
            CognitiveContextStabilizer(
                SequenceResolver(bundle),  # type: ignore[arg-type]
                SequenceSnapshotService(error),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertIs(caught.exception, error)

    def test_f31_second_resolver_error_after_first_conflict_propagates(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        error = ContextResolutionError("context_memory_unavailable")
        resolver = SequenceResolver(bundle, error)
        with self.assertRaises(ContextResolutionError) as caught:
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(
                    ContextSnapshotError("context_snapshot_source_changed")
                ),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertIs(caught.exception, error)

    def test_f32_second_non_source_change_snapshot_error_propagates(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, _ = make_bundle_snapshot(
            items=(make_item(source_id="source-2", text="new"),)
        )
        error = ContextSnapshotError("context_snapshot_source_unavailable")
        with self.assertRaises(ContextSnapshotError) as caught:
            CognitiveContextStabilizer(
                SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
                SequenceSnapshotService(
                    ContextSnapshotError("context_snapshot_source_changed"),
                    error,
                ),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertIs(caught.exception, error)

    def test_f33_context_projector_uses_final_snapshot_digest_exactly(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        artifact = CognitiveContextMemoryProjector.project_context(
            make_context_envelope(digest=snapshot.snapshot_digest),
            result,
        )
        self.assertEqual(
            artifact.envelope.context_snapshot_digest,
            snapshot.snapshot_digest,
        )

    def test_f34_context_projector_preserves_stabilization_metadata(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 1)
        artifact = CognitiveContextMemoryProjector.project_context(
            make_context_envelope(digest=snapshot.snapshot_digest),
            result,
        )
        self.assertEqual(artifact.stabilization_reacquisitions, 1)
        self.assertEqual(
            artifact.stabilization_policy,
            D129_STABILIZATION_POLICY,
        )

    def test_f35_context_projector_performs_pure_projection(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        artifact = CognitiveContextMemoryProjector.project_context(
            make_context_envelope(digest=snapshot.snapshot_digest),
            result,
        )
        self.assertIs(artifact.snapshot, snapshot)
        self.assertIs(result.bundle, bundle)

    def test_f36_memory_projector_selects_only_memory_layer(self) -> None:
        _, snapshot = memory_snapshot()
        artifact = CognitiveContextMemoryProjector.project_memory(
            make_memory_envelope(digest=snapshot.snapshot_digest),
            snapshot,
        )
        self.assertTrue(
            all(
                source.layer is ContextLayer.MEMORY
                for source in artifact.selected_sources
            )
        )

    def test_f37_memory_projector_preserves_frozen_snapshot_memory_order(self) -> None:
        _, snapshot = memory_snapshot()
        artifact = CognitiveContextMemoryProjector.project_memory(
            make_memory_envelope(digest=snapshot.snapshot_digest),
            snapshot,
        )
        self.assertEqual(
            [source.source_id for source in artifact.selected_sources],
            ["memory-1", "memory-2"],
        )

    def test_f38_memory_projector_empty_when_snapshot_has_no_memory(self) -> None:
        _, snapshot = make_bundle_snapshot()
        artifact = CognitiveContextMemoryProjector.project_memory(
            make_memory_envelope(digest=snapshot.snapshot_digest),
            snapshot,
        )
        self.assertEqual(artifact.selected_sources, ())

    def test_f39_memory_projector_does_not_copy_memory_content(self) -> None:
        _, snapshot = memory_snapshot()
        artifact = CognitiveContextMemoryProjector.project_memory(
            make_memory_envelope(digest=snapshot.snapshot_digest),
            snapshot,
        )
        self.assertEqual(
            {item.name for item in fields(CognitiveMemoryRetrievalArtifact)},
            {"envelope", "selected_sources"},
        )
        self.assertNotIn("value", repr(artifact.selected_sources))

    def test_f40_working_state_constructible_with_d129_slots_none(self) -> None:
        state = make_working_state()
        self.assertIsNone(state.context)
        self.assertIsNone(state.memory_retrieval)

    def test_f41_working_state_constructs_with_valid_context(self) -> None:
        context = make_context_artifact()
        state = make_working_state(context=context)
        self.assertEqual(state.context, context)

    def test_f42_context_may_attach_once_after_state_construction(self) -> None:
        state = make_working_state()
        context = make_context_artifact()
        state.context = context
        self.assertEqual(state.context, context)

    def test_f43_memory_retrieval_may_attach_after_context(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        state = make_working_state(context=context)
        memory = make_memory_artifact(context)
        state.memory_retrieval = memory
        self.assertEqual(state.memory_retrieval, memory)

    def test_f44_state_constructs_with_valid_context_and_memory(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        memory = make_memory_artifact(context)
        state = make_working_state(
            context=context,
            memory_retrieval=memory,
        )
        self.assertEqual(state.context, context)
        self.assertEqual(state.memory_retrieval, memory)

    def test_f45_null_working_memory_digest_remains_compatible(self) -> None:
        context = make_context_artifact()
        state = make_working_state(
            context=context,
            working_digest=None,
        )
        self.assertEqual(state.context, context)

    def test_f46_matching_working_memory_digest_remains_compatible(self) -> None:
        context = make_context_artifact()
        state = make_working_state(
            context=context,
            working_digest=context.snapshot.snapshot_digest,
        )
        self.assertEqual(state.context, context)

    def test_f47_null_perception_digest_compatible_after_freeze(self) -> None:
        context = make_context_artifact()
        state = make_working_state(
            context=context,
            perception=make_perception(digest=None),
        )
        self.assertIsNotNone(state.perception)

    def test_f48_null_task_digest_compatible_after_freeze(self) -> None:
        context = make_context_artifact()
        state = make_working_state(
            context=context,
            task=make_task(digest=None),
        )
        self.assertIsNotNone(state.task)

    def test_f49_matching_d127_context_digest_remains_compatible(self) -> None:
        context = make_context_artifact()
        digest = context.snapshot.snapshot_digest
        state = make_working_state(
            context=context,
            perception=make_perception(digest=digest),
            task=make_task(digest=digest),
        )
        self.assertEqual(
            state.perception.envelope.context_snapshot_digest,  # type: ignore[union-attr]
            digest,
        )

    def test_f50_matching_attention_selected_source_order_accepted(self) -> None:
        context = make_context_artifact()
        digest = context.snapshot.snapshot_digest
        attention = make_attention(digest=digest)
        state = make_working_state(
            context=context,
            attention=attention,
        )
        self.assertEqual(state.attention, attention)

    def test_f51_idempotent_equal_context_assignment_accepted(self) -> None:
        context = make_context_artifact()
        state = make_working_state(context=context)
        state.context = context
        self.assertEqual(state.context, context)

    def test_f52_idempotent_equal_memory_assignment_accepted(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        memory = make_memory_artifact(context)
        state = make_working_state(
            context=context,
            memory_retrieval=memory,
        )
        state.memory_retrieval = memory
        self.assertEqual(state.memory_retrieval, memory)

    def test_f53_historical_d128_working_state_behavior_compatible(self) -> None:
        state = make_working_state()
        self.assertIsInstance(state, ExecutionContext)
        state.response.answer = "changed"
        self.assertEqual(state.response.answer, "changed")

    def test_f54_historical_d128_turn_guard_behavior_compatible(self) -> None:
        guard = CognitiveTurnGuard()
        lease = guard.acquire(make_binding())
        self.assertEqual(
            guard.active_turn_id(
                WorkspaceId.PERSONAL,
                CONVERSATION_ID,
            ),
            TURN_ID,
        )
        guard.release(lease)
        self.assertIsNone(
            guard.active_turn_id(
                WorkspaceId.PERSONAL,
                CONVERSATION_ID,
            )
        )


if __name__ == "__main__":
    unittest.main()
