from __future__ import annotations

import ast
from dataclasses import fields
import inspect
import unittest

from pydantic import ValidationError

from app.contracts.cognitive_brain import (
    CognitiveFailureCode,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_context_memory import (
    D129_CONTEXT_ARTIFACT_TYPE,
    D129_CONTEXT_CONTRACT_VERSION,
    D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE,
    D129_MEMORY_RETRIEVAL_CONTRACT_VERSION,
    CognitiveContextArtifact,
    CognitiveContextFreezeResult,
    CognitiveMemoryRetrievalArtifact,
)
from app.contracts.context import (
    ContextBundle,
    ContextLayer,
    ContextSourceRef,
)
from app.contracts.context_resolution import ContextResolveRequest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
import app.contracts.cognitive_context_memory as d129_contract_module
import app.intelligence.context.cognitive as cognitive_state_module
import app.services.cognitive_context_memory as d129_service_module
from app.services.cognitive_context_memory import (
    CognitiveContextContractError,
    CognitiveContextMemoryProjector,
    CognitiveContextStabilizer,
    CognitiveContextUnstableError,
)
from app.services.context_resolver import ContextResolutionError
from app.services.context_snapshot import ContextSnapshotError

from tests.test_d128_cognitive_working_state import (
    TURN_ID,
    make_attention,
    make_perception,
    make_task,
)
from tests.test_d129_cognitive_context_memory import (
    SequenceResolver,
    SequenceSnapshotService,
    make_bundle_snapshot,
    make_context_artifact,
    make_context_envelope,
    make_item,
    make_memory_artifact,
    make_memory_envelope,
    make_request,
    make_working_state,
    memory_snapshot,
)


def imported_modules(module: object) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


class D129CognitiveContextMemorySecurityTests(unittest.TestCase):
    def test_s01_wrong_context_envelope_object_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=object(),  # type: ignore[arg-type]
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s02_wrong_context_producer_organ_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    organ=CognitiveOrgan.MEMORY_RETRIEVAL,
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s03_wrong_context_artifact_type_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    artifact_type="cognitive.other",
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s04_wrong_context_contract_version_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    contract_version="o-ai.other.v1",
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s05_non_ready_context_status_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    status=CognitiveOrganStatus.INSUFFICIENT,
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s06_context_model_binding_reference_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    model_binding_reference="c" * 64,
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s07_null_context_snapshot_digest_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=None,  # type: ignore[arg-type]
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s08_context_snapshot_digest_mismatch_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(digest="b" * 64),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s09_context_cross_workspace_snapshot_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                envelope=make_context_envelope(
                    digest=snapshot.snapshot_digest,
                    workspace_id=WorkspaceId.PERSONAL,
                ),
                snapshot=snapshot,
                stabilization_reacquisitions=0,
            )

    def test_s10_bool_stabilization_count_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                make_context_envelope(digest=snapshot.snapshot_digest),
                snapshot,
                True,  # type: ignore[arg-type]
            )

    def test_s11_negative_stabilization_count_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                make_context_envelope(digest=snapshot.snapshot_digest),
                snapshot,
                -1,
            )

    def test_s12_stabilization_count_above_one_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                make_context_envelope(digest=snapshot.snapshot_digest),
                snapshot,
                2,
            )

    def test_s13_wrong_stabilization_policy_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextArtifact(
                make_context_envelope(digest=snapshot.snapshot_digest),
                snapshot,
                0,
                "other",
            )

    def test_s14_wrong_freeze_result_bundle_type_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextFreezeResult(
                object(),  # type: ignore[arg-type]
                snapshot,
                0,
            )

    def test_s15_wrong_freeze_result_snapshot_type_rejected(self) -> None:
        bundle, _ = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveContextFreezeResult(
                bundle,
                object(),  # type: ignore[arg-type]
                0,
            )

    def test_s16_freeze_result_workspace_mismatch_rejected(self) -> None:
        bundle, _ = make_bundle_snapshot()
        _, company_snapshot = make_bundle_snapshot(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises(ValueError):
            CognitiveContextFreezeResult(
                bundle,
                company_snapshot,
                0,
            )

    def test_s17_freeze_result_item_mismatch_rejected(self) -> None:
        bundle, _ = make_bundle_snapshot()
        _, other_snapshot = make_bundle_snapshot(
            items=(make_item(source_id="other", text="other"),),
        )
        with self.assertRaises(ValueError):
            CognitiveContextFreezeResult(
                bundle,
                other_snapshot,
                0,
            )

    def test_s18_wrong_memory_envelope_object_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                object(),  # type: ignore[arg-type]
                (),
            )

    def test_s19_wrong_memory_producer_organ_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    organ=CognitiveOrgan.CONTEXT_INTELLIGENCE,
                ),
                (),
            )

    def test_s20_wrong_memory_artifact_type_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    artifact_type="cognitive.other",
                ),
                (),
            )

    def test_s21_wrong_memory_contract_version_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    contract_version="o-ai.other.v1",
                ),
                (),
            )

    def test_s22_non_ready_memory_status_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    status=CognitiveOrganStatus.FAILED,
                ),
                (),
            )

    def test_s23_memory_model_binding_reference_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    model_binding_reference="c" * 64,
                ),
                (),
            )

    def test_s24_null_memory_context_digest_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=None,  # type: ignore[arg-type]
                ),
                (),
            )

    def test_s25_non_context_source_ref_memory_source_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(digest=snapshot.snapshot_digest),
                (object(),),  # type: ignore[arg-type]
            )

    def test_s26_non_memory_layer_source_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        source = make_item().source
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(digest=snapshot.snapshot_digest),
                (source,),
            )

    def test_s27_cross_workspace_memory_source_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        source = make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-company",
            workspace_id=WorkspaceId.COMPANY,
        ).source
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    workspace_id=WorkspaceId.PERSONAL,
                ),
                (source,),
            )

    def test_s28_duplicate_memory_source_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        source = make_item(
            layer=ContextLayer.MEMORY,
            source_id="memory-1",
        ).source
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(digest=snapshot.snapshot_digest),
                (source, source),
            )

    def test_s29_invalid_memory_selected_source_collection_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(ValueError):
            CognitiveMemoryRetrievalArtifact(
                make_memory_envelope(digest=snapshot.snapshot_digest),
                "memory-1",  # type: ignore[arg-type]
            )

    def test_s30_context_projector_rejects_wrong_envelope(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_context(
                object(),  # type: ignore[arg-type]
                result,
            )

    def test_s31_context_projector_rejects_wrong_freeze_result(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_context(
                make_context_envelope(digest=snapshot.snapshot_digest),
                object(),  # type: ignore[arg-type]
            )

    def test_s32_context_projector_rejects_digest_mismatch(self) -> None:
        bundle, snapshot = make_bundle_snapshot()
        result = CognitiveContextFreezeResult(bundle, snapshot, 0)
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_context(
                make_context_envelope(digest="b" * 64),
                result,
            )

    def test_s33_memory_projector_rejects_wrong_envelope(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_memory(
                object(),  # type: ignore[arg-type]
                snapshot,
            )

    def test_s34_memory_projector_rejects_wrong_snapshot(self) -> None:
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_memory(
                make_memory_envelope(digest="a" * 64),
                object(),  # type: ignore[arg-type]
            )

    def test_s35_memory_projector_rejects_digest_mismatch(self) -> None:
        _, snapshot = make_bundle_snapshot()
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_memory(
                make_memory_envelope(digest="b" * 64),
                snapshot,
            )

    def test_s36_memory_projector_rejects_cross_workspace_snapshot(self) -> None:
        _, snapshot = make_bundle_snapshot(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextMemoryProjector.project_memory(
                make_memory_envelope(
                    digest=snapshot.snapshot_digest,
                    workspace_id=WorkspaceId.PERSONAL,
                ),
                snapshot,
            )

    def test_s37_stabilizer_rejects_wrong_request_type(self) -> None:
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(),  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(object())  # type: ignore[arg-type]

    def test_s38_resolver_non_context_bundle_fails_contract(self) -> None:
        request = make_request()
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(object()),  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_s39_resolver_wrong_workspace_bundle_fails_contract(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle),  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_s40_snapshot_non_context_snapshot_fails_contract(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle),  # type: ignore[arg-type]
                SequenceSnapshotService(object()),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_s41_snapshot_wrong_workspace_fails_contract(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        _, company_snapshot = make_bundle_snapshot(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle),  # type: ignore[arg-type]
                SequenceSnapshotService(company_snapshot),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_s42_snapshot_not_exact_resolved_bundle_fails_contract(self) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        _, other_snapshot = make_bundle_snapshot(
            items=(make_item(source_id="other", text="other"),),
        )
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle),  # type: ignore[arg-type]
                SequenceSnapshotService(other_snapshot),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)

    def test_s43_dependency_contract_failure_not_retried(self) -> None:
        request = make_request()
        resolver = SequenceResolver(object(), object())
        with self.assertRaises(CognitiveContextContractError):
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 1)

    def test_s44_resolver_failure_not_retried(self) -> None:
        request = make_request()
        resolver = SequenceResolver(
            ContextResolutionError("context_memory_unavailable")
        )
        with self.assertRaises(ContextResolutionError):
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 1)

    def test_s45_source_unavailable_not_retried(self) -> None:
        self._assert_snapshot_code_not_reacquired(
            "context_snapshot_source_unavailable"
        )

    def test_s46_source_mismatch_not_retried(self) -> None:
        self._assert_snapshot_code_not_reacquired(
            "context_snapshot_source_mismatch"
        )

    def test_s47_timestamp_invalid_not_retried(self) -> None:
        self._assert_snapshot_code_not_reacquired(
            "context_snapshot_timestamp_invalid"
        )

    def test_s48_snapshot_invalid_not_retried(self) -> None:
        self._assert_snapshot_code_not_reacquired(
            "context_snapshot_invalid"
        )

    def test_s49_only_exact_source_changed_triggers_stabilization(self) -> None:
        self._assert_snapshot_code_not_reacquired(
            "context_snapshot_source_changed "
        )

    def test_s50_first_source_change_yields_at_most_two_resolver_calls(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, _ = make_bundle_snapshot(
            items=(make_item(source_id="two", text="two"),)
        )
        resolver = SequenceResolver(bundle1, bundle2)
        with self.assertRaises(CognitiveContextUnstableError):
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(
                    ContextSnapshotError("context_snapshot_source_changed"),
                    ContextSnapshotError("context_snapshot_source_changed"),
                ),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 2)

    def test_s51_second_source_change_yields_no_third_resolver_call(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, _ = make_bundle_snapshot(
            items=(make_item(source_id="two", text="two"),)
        )
        resolver = SequenceResolver(bundle1, bundle2, AssertionError("third"))
        with self.assertRaises(CognitiveContextUnstableError):
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                SequenceSnapshotService(
                    ContextSnapshotError("context_snapshot_source_changed"),
                    ContextSnapshotError("context_snapshot_source_changed"),
                ),  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(len(resolver.calls), 2)

    def test_s52_second_source_change_yields_no_third_capture_call(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, _ = make_bundle_snapshot(
            items=(make_item(source_id="two", text="two"),)
        )
        snapshots = SequenceSnapshotService(
            ContextSnapshotError("context_snapshot_source_changed"),
            ContextSnapshotError("context_snapshot_source_changed"),
            AssertionError("third"),
        )
        with self.assertRaises(CognitiveContextUnstableError):
            CognitiveContextStabilizer(
                SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
                snapshots,  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(len(snapshots.calls), 2)

    def test_s53_stabilizer_contains_no_sleep_wait_backoff_queue(self) -> None:
        source = inspect.getsource(
            CognitiveContextStabilizer.resolve_and_freeze
        ).casefold()
        for token in ("sleep", ".wait", "backoff", "queue"):
            self.assertNotIn(token, source)

    def test_s54_stabilizer_contains_no_general_retry_fallback_loop(self) -> None:
        source = inspect.getsource(
            CognitiveContextStabilizer.resolve_and_freeze
        )
        lowered = source.casefold()
        self.assertNotIn("retry", lowered)
        self.assertNotIn("fallback", lowered)
        tree = ast.parse(inspect.cleandoc(source))
        self.assertFalse(
            any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
        )

    def test_s55_stabilization_reuses_exact_request_object(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="two", text="two"),)
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

    def test_s56_stabilization_does_not_mutate_request(self) -> None:
        request = make_request()
        before = (
            request.workspace_scope,
            request.query,
            request.conversation_id,
            request.project_id,
        )
        bundle1, _ = make_bundle_snapshot()
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="two", text="two"),)
        )
        CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        after = (
            request.workspace_scope,
            request.query,
            request.conversation_id,
            request.project_id,
        )
        self.assertEqual(before, after)

    def test_s57_failed_first_bundle_cannot_contribute_items(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot(
            items=(make_item(source_id="old", text="old"),)
        )
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="new", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(
            [item.source.source_id for item in result.bundle.items],
            ["new"],
        )

    def test_s58_failed_first_bundle_cannot_contribute_provenance(self) -> None:
        request = make_request()
        bundle1, _ = make_bundle_snapshot(
            items=(make_item(source_id="old", text="old"),)
        )
        bundle2, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="new", text="new"),)
        )
        result = CognitiveContextStabilizer(
            SequenceResolver(bundle1, bundle2),  # type: ignore[arg-type]
            SequenceSnapshotService(
                ContextSnapshotError("context_snapshot_source_changed"),
                snapshot2,
            ),  # type: ignore[arg-type]
        ).resolve_and_freeze(request)
        self.assertEqual(
            [
                item.provenance.source.source_id
                for item in result.snapshot.items
            ],
            ["new"],
        )

    def test_s59_working_state_context_turn_mismatch_rejected(self) -> None:
        context = make_context_artifact(turn_id="other-turn")
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(context=context)

    def test_s60_working_state_context_workspace_mismatch_rejected(self) -> None:
        context = make_context_artifact(
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(context=context)

    def test_s61_context_digest_conflicting_working_memory_rejected(self) -> None:
        context = make_context_artifact()
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                working_digest="f" * 64,
            )

    def test_s62_context_digest_conflicting_perception_rejected(self) -> None:
        context = make_context_artifact()
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                perception=make_perception(digest="f" * 64),
            )

    def test_s63_context_digest_conflicting_attention_rejected(self) -> None:
        context = make_context_artifact()
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                attention=make_attention(digest="f" * 64),
            )

    def test_s64_context_digest_conflicting_task_rejected(self) -> None:
        context = make_context_artifact()
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                task=make_task(digest="f" * 64),
            )

    def test_s65_attention_selected_source_mismatch_rejected(self) -> None:
        _, snapshot = make_bundle_snapshot(
            items=(make_item(source_id="different", text="different"),)
        )
        context = make_context_artifact(snapshot=snapshot)
        attention = make_attention(
            digest=snapshot.snapshot_digest,
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                attention=attention,
            )

    def test_s66_memory_retrieval_without_context_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        memory = make_memory_artifact(context)
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(memory_retrieval=memory)

    def test_s67_memory_retrieval_turn_mismatch_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        memory = make_memory_artifact(
            context,
            turn_id="other-turn",
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                memory_retrieval=memory,
            )

    def test_s68_memory_retrieval_workspace_mismatch_rejected(self) -> None:
        context = make_context_artifact()
        company_item = make_item(
            layer=ContextLayer.MEMORY,
            source_id="company-memory",
            workspace_id=WorkspaceId.COMPANY,
        )
        _, company_snapshot = make_bundle_snapshot(
            items=(company_item,),
            workspace_id=WorkspaceId.COMPANY,
        )
        company_context = make_context_artifact(
            snapshot=company_snapshot,
            workspace_id=WorkspaceId.COMPANY,
        )
        company_memory = make_memory_artifact(
            company_context,
            workspace_id=WorkspaceId.COMPANY,
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                memory_retrieval=company_memory,
            )

    def test_s69_memory_retrieval_digest_mismatch_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        selected = tuple(
            item.item.source
            for item in snapshot.items
            if item.item.source.layer is ContextLayer.MEMORY
        )
        memory = CognitiveMemoryRetrievalArtifact(
            envelope=make_memory_envelope(digest="f" * 64),
            selected_sources=selected,
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                memory_retrieval=memory,
            )

    def test_s70_memory_retrieval_selected_source_mismatch_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        wrong = ContextSourceRef(
            workspace_id=WorkspaceId.PERSONAL,
            layer=ContextLayer.MEMORY,
            source_id="wrong-memory",
        )
        memory = CognitiveMemoryRetrievalArtifact(
            envelope=make_memory_envelope(
                digest=snapshot.snapshot_digest,
            ),
            selected_sources=(wrong,),
        )
        with self.assertRaises((ValueError, ValidationError)):
            make_working_state(
                context=context,
                memory_retrieval=memory,
            )

    def test_s71_different_context_replacement_after_freeze_rejected(self) -> None:
        state = make_working_state()
        first = make_context_artifact()
        _, snapshot2 = make_bundle_snapshot(
            items=(make_item(source_id="second", text="second"),)
        )
        second = make_context_artifact(snapshot=snapshot2)
        state.context = first
        with self.assertRaises((ValueError, ValidationError)):
            state.context = second

    def test_s72_context_removal_after_freeze_rejected(self) -> None:
        state = make_working_state()
        state.context = make_context_artifact()
        with self.assertRaises((ValueError, ValidationError)):
            state.context = None

    def test_s73_different_memory_retrieval_replacement_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        first = make_memory_artifact(context)
        second = CognitiveMemoryRetrievalArtifact(
            envelope=first.envelope,
            selected_sources=tuple(reversed(first.selected_sources)),
        )
        state = make_working_state(
            context=context,
            memory_retrieval=first,
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.memory_retrieval = second

    def test_s74_memory_retrieval_removal_after_freeze_rejected(self) -> None:
        _, snapshot = memory_snapshot()
        context = make_context_artifact(snapshot=snapshot)
        memory = make_memory_artifact(context)
        state = make_working_state(
            context=context,
            memory_retrieval=memory,
        )
        with self.assertRaises((ValueError, ValidationError)):
            state.memory_retrieval = None

    def test_s75_no_owner_approval_execution_authorization_fields(self) -> None:
        direct = {
            item.name for item in fields(CognitiveContextArtifact)
        } | {
            item.name for item in fields(CognitiveMemoryRetrievalArtifact)
        }
        self.assertTrue(
            {"owner_approval", "execution_authorization"}.isdisjoint(direct)
        )

    def test_s76_no_provider_model_profile_credential_tool_authority_fields(self) -> None:
        direct = {
            item.name for item in fields(CognitiveContextArtifact)
        } | {
            item.name for item in fields(CognitiveMemoryRetrievalArtifact)
        }
        self.assertTrue(
            {
                "provider",
                "model",
                "profile",
                "credential",
                "tool_permission",
            }.isdisjoint(direct)
        )

    def test_s77_no_raw_prompt_system_prompt_hidden_reasoning_cot_fields(self) -> None:
        direct = {
            item.name for item in fields(CognitiveContextArtifact)
        } | {
            item.name for item in fields(CognitiveMemoryRetrievalArtifact)
        }
        self.assertTrue(
            {
                "raw_prompt",
                "system_prompt",
                "hidden_reasoning",
                "cot",
            }.isdisjoint(direct)
        )

    def test_s78_no_memory_project_conversation_repository_write_behavior(self) -> None:
        modules = (
            imported_modules(d129_contract_module)
            | imported_modules(d129_service_module)
            | imported_modules(cognitive_state_module)
        )
        self.assertFalse(
            any(name.startswith("app.repositories") for name in modules)
        )
        source = inspect.getsource(d129_service_module)
        for token in (".add(", ".delete(", ".commit(", ".flush("):
            self.assertNotIn(token, source)

    def test_s79_no_provider_ai_runtime_execution_guard_call(self) -> None:
        modules = imported_modules(d129_service_module)
        self.assertFalse(
            any(name.startswith("app.providers") for name in modules)
        )
        self.assertNotIn("app.services.ai_runtime", modules)
        self.assertNotIn("app.services.execution_guard", modules)

    def test_s80_d126_failure_vocabulary_unchanged(self) -> None:
        self.assertEqual(
            CognitiveFailureCode.CONTEXT_UNSTABLE.value,
            "context_unstable",
        )
        self.assertEqual(
            CognitiveFailureCode.CONTRACT_VIOLATION.value,
            "contract_violation",
        )

    def _assert_snapshot_code_not_reacquired(self, code: str) -> None:
        request = make_request()
        bundle, _ = make_bundle_snapshot()
        resolver = SequenceResolver(bundle, bundle)
        snapshots = SequenceSnapshotService(ContextSnapshotError(code))
        with self.assertRaises(ContextSnapshotError) as caught:
            CognitiveContextStabilizer(
                resolver,  # type: ignore[arg-type]
                snapshots,  # type: ignore[arg-type]
            ).resolve_and_freeze(request)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(len(resolver.calls), 1)
        self.assertEqual(len(snapshots.calls), 1)


if __name__ == "__main__":
    unittest.main()
