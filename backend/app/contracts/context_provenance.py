"""D96 immutable Context provenance and snapshot contracts.

Provenance and snapshot values are integrity metadata only. They grant no
authentication, authorization, owner approval, credential, connector, provider,
cloud-egress, or execution authority.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.contracts.context import (
    CONTEXT_BUNDLE_MAX_ITEMS,
    ContextItem,
    ContextSourceRef,
)
from app.contracts.workspace import WorkspaceScope


CONTEXT_SNAPSHOT_CONTRACT_VERSION = "1"
CONTEXT_PROVENANCE_PARENT_ID_MAX_BYTES = 512
CONTEXT_PROVENANCE_VERSION_REF_MAX_BYTES = 512
CONTEXT_PROVENANCE_LOCATOR_MAX_BYTES = 1024

_HEX_LOWER = frozenset("0123456789abcdef")


def _validate_optional_text(
    value: object,
    *,
    code: str,
    max_bytes: int,
) -> str | None:
    if value is None:
        return None
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > max_bytes
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise ValueError(code)
    return value


def _validate_sha256(value: object, *, code: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _HEX_LOWER for character in value)
    ):
        raise ValueError(code)
    return value


def _require_utc_datetime(
    value: object,
    *,
    code: str,
) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(code)
    offset = value.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError(code)
    return value


def _utc_z(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat().replace("+00:00", "Z")


def context_text_sha256(text: str) -> str:
    """Return lowercase SHA-256 for exact ContextItem UTF-8 text."""

    if type(text) is not str:
        raise ValueError("context_snapshot_text_invalid")
    try:
        payload = text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("context_snapshot_text_invalid") from None
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextSourceProvenance:
    """Typed source provenance for one exact D94 Context source."""

    source: ContextSourceRef
    content_sha256: str
    parent_source_id: str | None = None
    version_ref: str | None = None
    source_locator: str | None = None
    source_timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, ContextSourceRef):
            raise ValueError("context_provenance_source_invalid")
        _validate_sha256(
            self.content_sha256,
            code="context_provenance_content_sha256_invalid",
        )
        _validate_optional_text(
            self.parent_source_id,
            code="context_provenance_parent_source_id_invalid",
            max_bytes=CONTEXT_PROVENANCE_PARENT_ID_MAX_BYTES,
        )
        _validate_optional_text(
            self.version_ref,
            code="context_provenance_version_ref_invalid",
            max_bytes=CONTEXT_PROVENANCE_VERSION_REF_MAX_BYTES,
        )
        _validate_optional_text(
            self.source_locator,
            code="context_provenance_source_locator_invalid",
            max_bytes=CONTEXT_PROVENANCE_LOCATOR_MAX_BYTES,
        )
        if self.source_timestamp is not None:
            _require_utc_datetime(
                self.source_timestamp,
                code="context_provenance_source_timestamp_invalid",
            )


@dataclass(frozen=True, slots=True)
class ContextSnapshotItem:
    """One immutable ContextItem plus verified source provenance."""

    item: ContextItem
    provenance: ContextSourceProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.item, ContextItem):
            raise ValueError("context_snapshot_item_invalid")
        if not isinstance(self.provenance, ContextSourceProvenance):
            raise ValueError("context_snapshot_provenance_invalid")
        if self.item.source != self.provenance.source:
            raise ValueError("context_snapshot_source_mismatch")
        if context_text_sha256(self.item.text) != self.provenance.content_sha256:
            raise ValueError("context_snapshot_content_digest_mismatch")


def _canonical_manifest(
    *,
    workspace_scope: WorkspaceScope,
    captured_at: datetime,
    items: tuple[ContextSnapshotItem, ...],
    contract_version: str,
) -> dict[str, object]:
    return {
        "captured_at": _utc_z(captured_at),
        "contract_version": contract_version,
        "items": [
            {
                "content_sha256": snapshot_item.provenance.content_sha256,
                "label": snapshot_item.item.label,
                "layer": snapshot_item.item.source.layer.value,
                "parent_source_id": snapshot_item.provenance.parent_source_id,
                "source_id": snapshot_item.item.source.source_id,
                "source_locator": snapshot_item.provenance.source_locator,
                "source_timestamp": (
                    _utc_z(snapshot_item.provenance.source_timestamp)
                    if snapshot_item.provenance.source_timestamp is not None
                    else None
                ),
                "version_ref": snapshot_item.provenance.version_ref,
            }
            for snapshot_item in items
        ],
        "workspace_id": workspace_scope.workspace_id.value,
    }


def compute_context_snapshot_digest(
    *,
    workspace_scope: WorkspaceScope,
    captured_at: datetime,
    items: tuple[ContextSnapshotItem, ...],
    contract_version: str = CONTEXT_SNAPSHOT_CONTRACT_VERSION,
) -> str:
    """Compute deterministic SHA-256 for one canonical D96 snapshot manifest."""

    if not isinstance(workspace_scope, WorkspaceScope):
        raise ValueError("workspace_scope_invalid")
    _require_utc_datetime(
        captured_at,
        code="context_snapshot_captured_at_invalid",
    )
    if type(items) is not tuple:
        raise ValueError("context_snapshot_items_invalid")
    if len(items) > CONTEXT_BUNDLE_MAX_ITEMS:
        raise ValueError("context_snapshot_too_many_items")
    if contract_version != CONTEXT_SNAPSHOT_CONTRACT_VERSION:
        raise ValueError("context_snapshot_contract_version_invalid")

    for snapshot_item in items:
        if not isinstance(snapshot_item, ContextSnapshotItem):
            raise ValueError("context_snapshot_item_invalid")
        if (
            snapshot_item.item.source.workspace_id
            is not workspace_scope.workspace_id
        ):
            raise ValueError("context_snapshot_workspace_mismatch")

    manifest = _canonical_manifest(
        workspace_scope=workspace_scope,
        captured_at=captured_at,
        items=items,
        contract_version=contract_version,
    )
    payload = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    """Immutable, integrity-checked Context snapshot value."""

    workspace_scope: WorkspaceScope
    captured_at: datetime
    items: tuple[ContextSnapshotItem, ...]
    snapshot_digest: str
    contract_version: str = CONTEXT_SNAPSHOT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("workspace_scope_invalid")
        _require_utc_datetime(
            self.captured_at,
            code="context_snapshot_captured_at_invalid",
        )
        if type(self.items) is not tuple:
            raise ValueError("context_snapshot_items_invalid")
        if len(self.items) > CONTEXT_BUNDLE_MAX_ITEMS:
            raise ValueError("context_snapshot_too_many_items")
        if self.contract_version != CONTEXT_SNAPSHOT_CONTRACT_VERSION:
            raise ValueError("context_snapshot_contract_version_invalid")
        _validate_sha256(
            self.snapshot_digest,
            code="context_snapshot_digest_invalid",
        )

        expected = compute_context_snapshot_digest(
            workspace_scope=self.workspace_scope,
            captured_at=self.captured_at,
            items=self.items,
            contract_version=self.contract_version,
        )
        if self.snapshot_digest != expected:
            raise ValueError("context_snapshot_digest_mismatch")


@runtime_checkable
class ContextSnapshotClock(Protocol):
    """Narrow UTC clock boundary for D96 snapshot capture."""

    def now_utc(self) -> datetime:
        """Return one timezone-aware UTC datetime."""
        ...


class SystemContextSnapshotClock:
    """Standard-library UTC clock with no scheduler or Automation authority."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


__all__ = [
    "CONTEXT_PROVENANCE_LOCATOR_MAX_BYTES",
    "CONTEXT_PROVENANCE_PARENT_ID_MAX_BYTES",
    "CONTEXT_PROVENANCE_VERSION_REF_MAX_BYTES",
    "CONTEXT_SNAPSHOT_CONTRACT_VERSION",
    "ContextSnapshot",
    "ContextSnapshotClock",
    "ContextSnapshotItem",
    "ContextSourceProvenance",
    "SystemContextSnapshotClock",
    "compute_context_snapshot_digest",
    "context_text_sha256",
]
