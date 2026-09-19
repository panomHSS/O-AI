from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.contracts.context import ContextLayer, ContextSourceRef
from app.contracts.context_resolution import (
    ContextBudgetPolicy,
    ContextLayerBudget,
    ContextResolveRequest,
    Utf8ByteBudgetCounter,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.services.context_resolver import ContextResolutionError, ContextResolver
from app.services.context_sources import (
    ContextCandidate,
    ConversationContextSource,
    KnowledgeContextSource,
    MemoryContextSource,
    ProjectContextSource,
)
from app.services.project_context import ProjectContext


def _budget(*, candidate_limit: int = 8, max_items: int = 4, max_units: int = 4_000, max_item_units: int = 2_000) -> ContextLayerBudget:
    return ContextLayerBudget(
        candidate_limit=candidate_limit,
        max_items=max_items,
        max_units=max_units,
        max_item_units=max_item_units,
    )


def _policy(*, conversation=None, project=None, memory=None, knowledge=None) -> ContextBudgetPolicy:
    conversation = conversation or _budget()
    project = project or _budget(candidate_limit=1, max_items=1)
    memory = memory or _budget()
    knowledge = knowledge or _budget()
    return ContextBudgetPolicy(
        total_units=conversation.max_units + project.max_units + memory.max_units + knowledge.max_units,
        conversation=conversation,
        project=project,
        memory=memory,
        knowledge=knowledge,
    )


def _candidate(layer: ContextLayer, source_id: str, text: str, *, workspace_id: WorkspaceId = WorkspaceId.PERSONAL, order_key=(1,), label=None) -> ContextCandidate:
    return ContextCandidate(
        source=ContextSourceRef(
            workspace_id=workspace_id,
            layer=layer,
            source_id=source_id,
        ),
        text=text,
        label=label,
        relevance=None,
        order_key=order_key,
    )


class FakeSource:
    def __init__(self, items=()) -> None:
        self.items = tuple(items)
        self.calls = []

    def candidates(self, request, candidate_limit):
        self.calls.append((request, candidate_limit))
        return self.items


def _request() -> ContextResolveRequest:
    return ContextResolveRequest(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        query="alpha project knowledge",
        conversation_id="conversation-1",
        project_id="project-1",
    )


def _resolver(*, conversation=None, project=None, memory=None, knowledge=None, policy=None) -> ContextResolver:
    return ContextResolver(
        conversation_source=conversation or FakeSource(),
        project_source=project or FakeSource(),
        memory_source=memory or FakeSource(),
        knowledge_source=knowledge or FakeSource(),
        policy=policy or _policy(),
        counter=Utf8ByteBudgetCounter(),
    )


def test_resolver_emits_exact_layer_order_and_layer_order_keys() -> None:
    bundle = _resolver(
        conversation=FakeSource((
            _candidate(ContextLayer.CONVERSATION, "m2", "new", order_key=(2,)),
            _candidate(ContextLayer.CONVERSATION, "m1", "old", order_key=(1,)),
        )),
        project=FakeSource((_candidate(ContextLayer.PROJECT, "p1", "project"),)),
        memory=FakeSource((
            _candidate(ContextLayer.MEMORY, "mem2", "memory two", order_key=(2,)),
            _candidate(ContextLayer.MEMORY, "mem1", "memory one", order_key=(1,)),
        )),
        knowledge=FakeSource((
            _candidate(ContextLayer.KNOWLEDGE, "k2", "knowledge two", order_key=(2,)),
            _candidate(ContextLayer.KNOWLEDGE, "k1", "knowledge one", order_key=(1,)),
        )),
    ).resolve(_request())

    assert [(item.source.layer, item.source.source_id) for item in bundle.items] == [
        (ContextLayer.CONVERSATION, "m1"),
        (ContextLayer.CONVERSATION, "m2"),
        (ContextLayer.PROJECT, "p1"),
        (ContextLayer.MEMORY, "mem1"),
        (ContextLayer.MEMORY, "mem2"),
        (ContextLayer.KNOWLEDGE, "k1"),
        (ContextLayer.KNOWLEDGE, "k2"),
    ]


def test_whole_item_budget_skips_oversized_candidate_without_truncation() -> None:
    source = FakeSource((
        _candidate(ContextLayer.MEMORY, "too-big", "x" * 11),
        _candidate(ContextLayer.MEMORY, "fits", "exactly10"),
    ))
    budget = _budget(candidate_limit=2, max_items=2, max_units=10, max_item_units=10)
    bundle = _resolver(
        memory=source,
        policy=_policy(memory=budget),
    ).resolve(_request())
    memory_items = [item for item in bundle.items if item.source.layer is ContextLayer.MEMORY]

    assert [item.source.source_id for item in memory_items] == ["fits"]
    assert memory_items[0].text == "exactly10"
    assert source.items[0].text == "x" * 11


def test_exact_duplicate_collapses_once_and_equal_text_different_ids_remains() -> None:
    same = _candidate(ContextLayer.KNOWLEDGE, "chunk-1", "same")
    bundle = _resolver(
        knowledge=FakeSource((
            same,
            same,
            _candidate(ContextLayer.KNOWLEDGE, "chunk-2", "same"),
        ))
    ).resolve(_request())
    ids = [item.source.source_id for item in bundle.items if item.source.layer is ContextLayer.KNOWLEDGE]
    assert ids == ["chunk-1", "chunk-2"]


def test_conflicting_projection_for_same_source_identity_fails_closed() -> None:
    with pytest.raises(ContextResolutionError, match="context_candidate_identity_conflict"):
        _resolver(
            knowledge=FakeSource((
                _candidate(ContextLayer.KNOWLEDGE, "chunk-1", "one"),
                _candidate(ContextLayer.KNOWLEDGE, "chunk-1", "two"),
            ))
        ).resolve(_request())


def test_cross_workspace_candidate_fails_before_bundle_creation() -> None:
    with pytest.raises(ContextResolutionError, match="context_candidate_workspace_mismatch"):
        _resolver(
            knowledge=FakeSource((
                _candidate(
                    ContextLayer.KNOWLEDGE,
                    "chunk-company",
                    "company data",
                    workspace_id=WorkspaceId.COMPANY,
                ),
            ))
        ).resolve(_request())


def test_empty_sources_produce_valid_empty_exact_workspace_bundle() -> None:
    request = _request()
    bundle = _resolver().resolve(request)
    assert bundle.items == ()
    assert bundle.workspace_scope is request.workspace_scope


def test_candidate_limit_is_passed_to_each_source() -> None:
    conversation = FakeSource()
    project = FakeSource()
    memory = FakeSource()
    knowledge = FakeSource()
    policy = ContextBudgetPolicy(
        total_units=4_000,
        conversation=_budget(
            candidate_limit=2,
            max_items=2,
            max_units=1_000,
            max_item_units=1_000,
        ),
        project=_budget(
            candidate_limit=1,
            max_items=1,
            max_units=1_000,
            max_item_units=1_000,
        ),
        memory=_budget(
            candidate_limit=3,
            max_items=2,
            max_units=1_000,
            max_item_units=1_000,
        ),
        knowledge=_budget(
            candidate_limit=4,
            max_items=2,
            max_units=1_000,
            max_item_units=1_000,
        ),
    )
    request = _request()
    _resolver(
        conversation=conversation,
        project=project,
        memory=memory,
        knowledge=knowledge,
        policy=policy,
    ).resolve(request)

    assert conversation.calls == [(request, 2)]
    assert project.calls == [(request, 1)]
    assert memory.calls == [(request, 3)]
    assert knowledge.calls == [(request, 4)]


class FakeConversationReader:
    def __init__(self) -> None:
        self.requested_limit = None

    def get(self, conversation_id):
        return SimpleNamespace(id=conversation_id)

    def recent_messages(self, conversation_id, limit):
        del conversation_id
        self.requested_limit = limit
        return (
            SimpleNamespace(id="m1", role="user", content="old", created_at=datetime(2026, 1, 1, tzinfo=UTC)),
            SimpleNamespace(id="m2", role="assistant", content="new", created_at=datetime(2026, 1, 2, tzinfo=UTC)),
        )


def test_conversation_source_prioritizes_recent_but_keeps_chronological_order_key() -> None:
    reader = FakeConversationReader()
    candidates = ConversationContextSource(reader).candidates(_request(), 2)  # type: ignore[arg-type]

    assert reader.requested_limit == 2
    assert [item.source.source_id for item in candidates] == ["m2", "m1"]
    assert sorted(candidates, key=lambda item: item.order_key)[0].source.source_id == "m1"
    assert all('"role":' in item.text for item in candidates)


class FakeProjectResolver:
    def resolve(self, project_id):
        assert project_id == "project-1"
        return ProjectContext(
            title="Alpha",
            objective="Ship safely",
            status="ACTIVE",
            current_summary="Current",
            next_action="Test",
            current_revision=3,
        )


def test_project_source_emits_deterministic_data_without_legacy_prompt_header() -> None:
    candidates = ProjectContextSource(FakeProjectResolver()).candidates(_request(), 1)  # type: ignore[arg-type]
    assert len(candidates) == 1
    assert candidates[0].source.source_id == "project-1"
    assert '"current_revision":3' in candidates[0].text
    assert "OWNER-CONTROLLED PROJECT CONTEXT" not in candidates[0].text


class FakeMemoryReader:
    def confirmed_versions_for_context(self):
        return (
            SimpleNamespace(id="version-2", memory_id="memory-2", version=1, key="other.topic", value='"alpha"', value_type="STRING"),
            SimpleNamespace(id="version-1", memory_id="memory-1", version=2, key="alpha.project", value='"knowledge"', value_type="STRING"),
            SimpleNamespace(id="version-zero", memory_id="memory-zero", version=1, key="unrelated", value='"nothing"', value_type="STRING"),
        )


def test_memory_source_uses_existing_relevance_semantics_without_legacy_budget() -> None:
    candidates = MemoryContextSource(FakeMemoryReader()).candidates(_request(), 8)  # type: ignore[arg-type]
    assert [item.source.source_id for item in candidates] == ["version-1", "version-2"]
    assert candidates[0].relevance > candidates[1].relevance
    assert all(item.source.layer is ContextLayer.MEMORY for item in candidates)


class FakeKnowledgeSearch:
    def __init__(self) -> None:
        self.calls = []

    def search(self, workspace_id, query, limit):
        self.calls.append((workspace_id, query, limit))
        return [
            {"chunk_id": "chunk-2", "content": "second", "relevance_score": 0.9},
            {"chunk_id": "chunk-1", "content": "first", "relevance_score": 0.8},
        ]


def test_knowledge_source_passes_exact_workspace_and_preserves_search_rank() -> None:
    search = FakeKnowledgeSearch()
    candidates = KnowledgeContextSource(search).candidates(_request(), 5)  # type: ignore[arg-type]
    assert search.calls == [("personal", "alpha project knowledge", 5)]
    assert [item.source.source_id for item in candidates] == ["chunk-2", "chunk-1"]
    assert [item.order_key[0] for item in candidates] == [1, 2]


def test_knowledge_source_does_not_search_without_searchable_terms() -> None:
    search = FakeKnowledgeSearch()
    request = ContextResolveRequest(
        workspace_scope=WorkspaceScope(WorkspaceId.PERSONAL),
        query="--- !!!",
    )
    candidates = KnowledgeContextSource(search).candidates(request, 5)  # type: ignore[arg-type]
    assert candidates == ()
    assert search.calls == []
