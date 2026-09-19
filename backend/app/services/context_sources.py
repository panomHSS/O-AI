"""D95 read-only adapters from authoritative sources into Context candidates."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.contracts.context import ContextItem, ContextLayer, ContextSourceRef
from app.contracts.context_resolution import ContextResolveRequest
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.memory_version import MemoryVersion
from app.search.base import KnowledgeSearchPort
from app.services.memory_resolver import (
    ConfirmedMemoryReader,
    decode_memory_context_value,
    memory_context_key_is_valid,
    memory_context_score,
    memory_context_terms,
)
from app.services.project_context import (
    ProjectContext,
    ProjectContextResolver,
    ProjectContextUnavailableError,
)


class ContextSourceReadError(Exception):
    """Bounded internal source-read error; raw storage details stay private."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    """Ephemeral selection metadata around one valid D94 Context item."""

    source: ContextSourceRef
    text: str
    label: str | None
    relevance: int | float | None
    order_key: tuple[int | float | str, ...]

    def __post_init__(self) -> None:
        ContextItem(source=self.source, text=self.text, label=self.label)
        if self.relevance is not None:
            if (
                isinstance(self.relevance, bool)
                or not isinstance(self.relevance, (int, float))
                or not math.isfinite(float(self.relevance))
            ):
                raise ValueError("context_candidate_relevance_invalid")
        if (
            type(self.order_key) is not tuple
            or not self.order_key
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float, str))
                for value in self.order_key
            )
        ):
            raise ValueError("context_candidate_order_key_invalid")


class ContextSourcePort(Protocol):
    """One read-only D95 candidate source."""

    def candidates(
        self,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]: ...


class ConversationContextReaderPort(Protocol):
    """Narrow read-only Conversation operations needed by D95."""

    def get(self, conversation_id: str) -> Conversation | None: ...

    def recent_messages(
        self,
        conversation_id: str,
        limit: int,
    ) -> Sequence[Message]: ...


def conversation_context_projection(
    role: str,
    content: str,
) -> tuple[str, str]:
    """Return the exact deterministic D95 Conversation data projection."""

    if role not in {"user", "assistant"} or type(content) is not str:
        raise ValueError("conversation_context_projection_invalid")
    return (
        json.dumps(
            {"content": content, "role": role},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        (
            "conversation_user"
            if role == "user"
            else "conversation_assistant"
        ),
    )


def project_context_projection(context: ProjectContext) -> str:
    """Return the exact deterministic D95 Project data projection."""

    if not isinstance(context, ProjectContext):
        raise ValueError("project_context_projection_invalid")
    payload: dict[str, object] = {
        "current_revision": context.current_revision,
        "objective": context.objective,
        "status": context.status,
        "title": context.title,
    }
    if context.current_summary is not None:
        payload["current_summary"] = context.current_summary
    if context.next_action is not None:
        payload["next_action"] = context.next_action
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def memory_context_projection(
    *,
    key: str,
    value: object,
    value_type: str,
) -> str:
    """Return the exact deterministic D95 Memory data projection."""

    if (
        type(key) is not str
        or not key
        or type(value_type) is not str
        or not value_type
    ):
        raise ValueError("memory_context_projection_invalid")
    return json.dumps(
        {
            "key": key,
            "value": value,
            "value_type": value_type,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def knowledge_context_projection(content: str) -> tuple[str, str]:
    """Return the exact D95 Knowledge projection and descriptive label."""

    if type(content) is not str or not content.strip():
        raise ValueError("knowledge_context_projection_invalid")
    return content, "knowledge"


class ConversationContextSource:
    """Project persisted Conversation messages into data-only D94 candidates."""

    def __init__(self, reader: ConversationContextReaderPort) -> None:
        self._reader = reader

    def candidates(
        self,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]:
        conversation_id = request.conversation_id
        if conversation_id is None:
            return ()

        try:
            if self._reader.get(conversation_id) is None:
                raise ContextSourceReadError("context_conversation_unavailable")
            rows = self._reader.recent_messages(conversation_id, candidate_limit)
            chronological: list[ContextCandidate] = []
            for row in rows:
                if type(row.id) is not str or not row.id:
                    raise ValueError("conversation_candidate_invalid")
                text, label = conversation_context_projection(
                    row.role,
                    row.content,
                )
                chronological.append(
                    ContextCandidate(
                        source=ContextSourceRef(
                            workspace_id=request.workspace_scope.workspace_id,
                            layer=ContextLayer.CONVERSATION,
                            source_id=row.id,
                        ),
                        text=text,
                        label=label,
                        relevance=None,
                        order_key=(row.created_at.isoformat(), row.id),
                    )
                )
            return tuple(reversed(chronological))
        except ContextSourceReadError:
            raise
        except Exception as error:
            raise ContextSourceReadError(
                "context_conversation_unavailable"
            ) from error


class ProjectContextSource:
    """Adapt validated current Project state into one D94 Context candidate."""

    def __init__(self, resolver: ProjectContextResolver) -> None:
        self._resolver = resolver

    def candidates(
        self,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]:
        del candidate_limit
        project_id = request.project_id
        if project_id is None:
            return ()

        try:
            context = self._resolver.resolve(project_id)
            if context is None:
                raise ContextSourceReadError("context_project_unavailable")
            return (
                ContextCandidate(
                    source=ContextSourceRef(
                        workspace_id=request.workspace_scope.workspace_id,
                        layer=ContextLayer.PROJECT,
                        source_id=project_id,
                    ),
                    text=project_context_projection(context),
                    label="project_current",
                    relevance=None,
                    order_key=(project_id,),
                ),
            )
        except ContextSourceReadError:
            raise
        except ProjectContextUnavailableError as error:
            raise ContextSourceReadError(
                "context_project_unavailable"
            ) from error
        except Exception as error:
            raise ContextSourceReadError(
                "context_project_unavailable"
            ) from error


class MemoryContextSource:
    """Rank confirmed Memories once, without legacy budget pre-filtering."""

    def __init__(self, reader: ConfirmedMemoryReader) -> None:
        self._reader = reader

    def candidates(
        self,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]:
        terms = memory_context_terms(request.query)
        if not terms:
            return ()

        try:
            ranked: list[tuple[int, MemoryVersion, object]] = []
            seen: set[tuple[str, int]] = set()

            for memory in self._reader.confirmed_versions_for_context():
                identity = (memory.memory_id, memory.version)
                if identity in seen:
                    continue
                seen.add(identity)
                if not memory_context_key_is_valid(memory.key):
                    continue

                value = decode_memory_context_value(memory.value)
                if value is None:
                    continue

                score = memory_context_score(memory.key, memory.value, terms)
                if score <= 0:
                    continue
                ranked.append((score, memory, value))

            ranked.sort(
                key=lambda item: (
                    -item[0],
                    item[1].key.casefold(),
                    item[1].memory_id,
                    item[1].version,
                    item[1].id,
                )
            )

            candidates: list[ContextCandidate] = []
            for score, memory, value in ranked[:candidate_limit]:
                try:
                    text = memory_context_projection(
                        key=memory.key,
                        value=value,
                        value_type=memory.value_type,
                    )
                    candidate = ContextCandidate(
                        source=ContextSourceRef(
                            workspace_id=request.workspace_scope.workspace_id,
                            layer=ContextLayer.MEMORY,
                            source_id=memory.id,
                        ),
                        text=text,
                        label="memory",
                        relevance=score,
                        order_key=(
                            -score,
                            memory.key.casefold(),
                            memory.memory_id,
                            memory.version,
                            memory.id,
                        ),
                    )
                except (TypeError, UnicodeError, ValueError):
                    continue
                candidates.append(candidate)

            return tuple(candidates)
        except Exception as error:
            raise ContextSourceReadError(
                "context_memory_unavailable"
            ) from error


class KnowledgeContextSource:
    """Adapt exact-workspace ranked Knowledge chunks into D94 candidates."""

    _TERM_PATTERN = re.compile(r"[\w]+", flags=re.UNICODE)

    def __init__(self, search: KnowledgeSearchPort) -> None:
        self._search = search

    def candidates(
        self,
        request: ContextResolveRequest,
        candidate_limit: int,
    ) -> Sequence[ContextCandidate]:
        terms = self._TERM_PATTERN.findall(request.query)
        if not terms:
            return ()

        normalized_query = " ".join(terms)
        try:
            records = self._search.search(
                request.workspace_scope.workspace_id.value,
                normalized_query,
                candidate_limit,
            )
            candidates: list[ContextCandidate] = []
            for rank, record in enumerate(records, start=1):
                chunk_id = record.get("chunk_id")
                content = record.get("content")
                if type(chunk_id) is not str or not chunk_id:
                    raise ValueError("knowledge_candidate_invalid")
                text, label = knowledge_context_projection(content)  # type: ignore[arg-type]

                relevance_raw = record.get("relevance_score")
                relevance: int | float | None = None
                if (
                    not isinstance(relevance_raw, bool)
                    and isinstance(relevance_raw, (int, float))
                    and math.isfinite(float(relevance_raw))
                ):
                    relevance = relevance_raw

                candidates.append(
                    ContextCandidate(
                        source=ContextSourceRef(
                            workspace_id=request.workspace_scope.workspace_id,
                            layer=ContextLayer.KNOWLEDGE,
                            source_id=chunk_id,
                        ),
                        text=text,
                        label=label,
                        relevance=relevance,
                        order_key=(rank, chunk_id),
                    )
                )
            return tuple(candidates)
        except Exception as error:
            raise ContextSourceReadError(
                "context_knowledge_unavailable"
            ) from error


__all__ = [
    "ContextCandidate",
    "ContextSourcePort",
    "ContextSourceReadError",
    "ConversationContextReaderPort",
    "ConversationContextSource",
    "KnowledgeContextSource",
    "MemoryContextSource",
    "ProjectContextSource",
    "conversation_context_projection",
    "knowledge_context_projection",
    "memory_context_projection",
    "project_context_projection",
]
