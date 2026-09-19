"""D94 immutable workspace-safe Context Layer contracts.

Context is provider-neutral background data only. It grants no command,
approval, authorization, credential, connector, AI-provider, or execution
authority.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from app.contracts.workspace import WorkspaceId, WorkspaceScope


CONTEXT_SOURCE_ID_MAX_BYTES = 512
CONTEXT_LABEL_MAX_BYTES = 256
CONTEXT_ITEM_TEXT_MAX_BYTES = 262144
CONTEXT_BUNDLE_MAX_ITEMS = 256


class ContextLayer(Enum):
    """The four exact D94 Context layers."""

    CONVERSATION = "conversation"
    PROJECT = "project"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"


def _validate_identifier(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _validate_context_text(value: object) -> str:
    if (
        type(value) is not str
        or not value.strip()
        or "\x00" in value
        or len(value.encode("utf-8")) > CONTEXT_ITEM_TEXT_MAX_BYTES
    ):
        raise ValueError("context_item_text_invalid")
    return value


@dataclass(frozen=True, slots=True)
class ContextSourceRef:
    """Opaque source identity for one workspace-bound Context item."""

    workspace_id: WorkspaceId
    layer: ContextLayer
    source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise ValueError("workspace_id_invalid")
        if not isinstance(self.layer, ContextLayer):
            raise ValueError("context_layer_invalid")
        _validate_identifier(
            self.source_id,
            code="context_source_id_invalid",
            max_bytes=CONTEXT_SOURCE_ID_MAX_BYTES,
        )


@dataclass(frozen=True, slots=True)
class ContextItem:
    """One bounded provider-neutral Context datum; text is never authority."""

    source: ContextSourceRef
    text: str
    label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ContextSourceRef):
            raise ValueError("context_source_invalid")
        _validate_context_text(self.text)
        if self.label is not None:
            _validate_identifier(
                self.label,
                code="context_label_invalid",
                max_bytes=CONTEXT_LABEL_MAX_BYTES,
            )


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Immutable Context collection bound to one exact workspace scope."""

    workspace_scope: WorkspaceScope
    items: tuple[ContextItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")
        if type(self.items) is not tuple:
            raise ValueError("context_items_invalid")
        if len(self.items) > CONTEXT_BUNDLE_MAX_ITEMS:
            raise ValueError("context_bundle_too_many_items")

        workspace_id = self.workspace_scope.workspace_id
        for item in self.items:
            if not isinstance(item, ContextItem):
                raise ValueError("context_item_invalid")
            if item.source.workspace_id is not workspace_id:
                raise ValueError("context_workspace_mismatch")


__all__ = [
    "CONTEXT_BUNDLE_MAX_ITEMS",
    "CONTEXT_ITEM_TEXT_MAX_BYTES",
    "CONTEXT_LABEL_MAX_BYTES",
    "CONTEXT_SOURCE_ID_MAX_BYTES",
    "ContextBundle",
    "ContextItem",
    "ContextLayer",
    "ContextSourceRef",
]
