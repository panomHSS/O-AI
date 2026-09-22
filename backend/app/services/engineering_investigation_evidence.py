"""D113 deterministic D106-backed Engineering investigation evidence builder.

This service performs repository reads only through EngineeringRepositoryReader.
Repository observations are untrusted data and grant no proposal, approval,
apply, provider, Tool/Module, connector, shell/process, Git, network, credential,
or Skill execution authority.
"""

from __future__ import annotations

import json

from app.contracts.engineering_investigation import (
    ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS,
    ENGINEERING_INVESTIGATION_MAX_TEXT_ITEMS,
    EngineeringInvestigationEvidenceItem,
    EngineeringInvestigationEvidencePack,
    EngineeringInvestigationRequest,
)
from app.contracts.engineering_read import (
    EngineeringDirectoryListing,
    EngineeringPathStat,
    EngineeringReadOperation,
    EngineeringReadRequest,
    EngineeringRepositoryOverview,
    EngineeringTextRead,
)
from app.contracts.workspace import WorkspaceScope
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)


class EngineeringInvestigationEvidenceError(Exception):
    """Bounded D113 evidence-build failure with a stable safe code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EngineeringInvestigationEvidenceBuilder:
    """Build one bounded deterministic evidence pack through D106 only."""

    def __init__(
        self,
        repository_reader: EngineeringRepositoryReader,
    ) -> None:
        if not isinstance(repository_reader, EngineeringRepositoryReader):
            raise TypeError(
                "repository_reader must be EngineeringRepositoryReader."
            )
        self._reader = repository_reader

    def build(
        self,
        *,
        workspace_scope: WorkspaceScope,
        request: EngineeringInvestigationRequest,
    ) -> EngineeringInvestigationEvidencePack:
        if not isinstance(workspace_scope, WorkspaceScope):
            raise EngineeringInvestigationEvidenceError(
                "engineering_investigation_request_invalid"
            )
        if not isinstance(request, EngineeringInvestigationRequest):
            raise EngineeringInvestigationEvidenceError(
                "engineering_investigation_request_invalid"
            )

        try:
            overview = self._read(
                workspace_scope,
                EngineeringReadOperation.REPOSITORY_OVERVIEW,
            )
        except EngineeringReadError:
            raise EngineeringInvestigationEvidenceError(
                "engineering_investigation_evidence_unavailable"
            ) from None

        if not isinstance(overview, EngineeringRepositoryOverview):
            raise EngineeringInvestigationEvidenceError(
                "engineering_investigation_evidence_unavailable"
            )

        items: list[EngineeringInvestigationEvidenceItem] = [
            EngineeringInvestigationEvidenceItem(
                evidence_id="overview:0",
                kind="repository_overview",
                relative_path=None,
                content=self._entries_json(overview.entries),
            )
        ]
        omitted_paths: list[str] = []
        admitted_text_chars = 0
        admitted_text_items = 0

        for index, relative_path in enumerate(
            request.focus_paths,
            start=1,
        ):
            try:
                stat = self._read(
                    workspace_scope,
                    EngineeringReadOperation.STAT_PATH,
                    relative_path,
                )
            except EngineeringReadError:
                raise EngineeringInvestigationEvidenceError(
                    "engineering_investigation_evidence_unavailable"
                ) from None

            if not isinstance(stat, EngineeringPathStat):
                raise EngineeringInvestigationEvidenceError(
                    "engineering_investigation_evidence_unavailable"
                )

            items.append(
                EngineeringInvestigationEvidenceItem(
                    evidence_id=f"stat:{index}",
                    kind="path_stat",
                    relative_path=relative_path,
                    content=self._entry_json(stat.entry),
                    size_bytes=stat.entry.size_bytes,
                )
            )

            if stat.entry.kind == "directory":
                try:
                    listing = self._read(
                        workspace_scope,
                        EngineeringReadOperation.LIST_DIRECTORY,
                        relative_path,
                    )
                except EngineeringReadError:
                    raise EngineeringInvestigationEvidenceError(
                        "engineering_investigation_evidence_unavailable"
                    ) from None

                if not isinstance(listing, EngineeringDirectoryListing):
                    raise EngineeringInvestigationEvidenceError(
                        "engineering_investigation_evidence_unavailable"
                    )

                items.append(
                    EngineeringInvestigationEvidenceItem(
                        evidence_id=f"list:{index}",
                        kind="directory_listing",
                        relative_path=relative_path,
                        content=self._entries_json(listing.entries),
                    )
                )
                continue

            try:
                text = self._read(
                    workspace_scope,
                    EngineeringReadOperation.READ_TEXT,
                    relative_path,
                )
            except EngineeringReadError:
                raise EngineeringInvestigationEvidenceError(
                    "engineering_investigation_evidence_unavailable"
                ) from None

            if not isinstance(text, EngineeringTextRead):
                raise EngineeringInvestigationEvidenceError(
                    "engineering_investigation_evidence_unavailable"
                )

            fits_item_count = (
                admitted_text_items
                < ENGINEERING_INVESTIGATION_MAX_TEXT_ITEMS
            )
            fits_char_budget = (
                admitted_text_chars + len(text.content)
                <= ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS
            )

            if not fits_item_count or not fits_char_budget:
                omitted_paths.append(relative_path)
                continue

            items.append(
                EngineeringInvestigationEvidenceItem(
                    evidence_id=f"text:{index}",
                    kind="text",
                    relative_path=relative_path,
                    content=text.content,
                    size_bytes=text.size_bytes,
                    content_sha256=text.content_sha256,
                )
            )
            admitted_text_items += 1
            admitted_text_chars += len(text.content)

        return EngineeringInvestigationEvidencePack(
            workspace_scope=workspace_scope,
            conversation_id=request.conversation_id,
            instruction=request.instruction,
            focus_paths=request.focus_paths,
            evidence_items=tuple(items),
            omitted_paths=tuple(omitted_paths),
            admitted_text_chars=admitted_text_chars,
        )

    def _read(
        self,
        workspace_scope: WorkspaceScope,
        operation: EngineeringReadOperation,
        relative_path: str | None = None,
    ):
        return self._reader.read(
            EngineeringReadRequest(
                workspace_scope=workspace_scope,
                operation=operation,
                relative_path=relative_path,
            )
        )

    @staticmethod
    def _entry_json(entry) -> str:
        return json.dumps(
            {
                "kind": entry.kind,
                "relative_path": entry.relative_path,
                "size_bytes": entry.size_bytes,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _entries_json(entries) -> str:
        return json.dumps(
            [
                {
                    "kind": entry.kind,
                    "relative_path": entry.relative_path,
                    "size_bytes": entry.size_bytes,
                }
                for entry in entries
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


__all__ = [
    "EngineeringInvestigationEvidenceBuilder",
    "EngineeringInvestigationEvidenceError",
]