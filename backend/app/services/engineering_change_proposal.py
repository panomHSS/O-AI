"""D107 deterministic Engineering Change Proposal construction service.

The service consumes the D106 read-only repository boundary to derive one exact
base snapshot and returns one immutable D107 proposal. It performs no repository
mutation and grants no approval, authorization, claim, or apply authority.
"""

from __future__ import annotations

from app.contracts.engineering_change_proposal import (
    EngineeringChangeBaseState,
    EngineeringChangeDraft,
    EngineeringChangeOperation,
    EngineeringChangeProposal,
)
from app.contracts.engineering_read import (
    EngineeringReadOperation,
    EngineeringReadRequest,
)
from app.services.engineering_repository_reader import (
    EngineeringReadError,
    EngineeringRepositoryReader,
)


class EngineeringChangeProposalError(Exception):
    """Bounded D107 proposal-construction failure with a stable safe code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EngineeringChangeProposalService:
    """Construct one exact D107 proposal from D106 read-only observations."""

    def __init__(self, repository_reader: EngineeringRepositoryReader) -> None:
        if not isinstance(repository_reader, EngineeringRepositoryReader):
            raise ValueError("engineering_change_request_invalid")
        self._reader = repository_reader

    def propose(
        self,
        draft: EngineeringChangeDraft,
    ) -> EngineeringChangeProposal:
        if not isinstance(draft, EngineeringChangeDraft):
            raise EngineeringChangeProposalError(
                "engineering_change_request_invalid"
            )

        if draft.operation is EngineeringChangeOperation.CREATE_TEXT:
            return self._propose_create(draft)
        if draft.operation is EngineeringChangeOperation.REPLACE_TEXT:
            return self._propose_replace(draft)

        raise EngineeringChangeProposalError(
            "engineering_change_operation_invalid"
        )

    def _propose_create(
        self,
        draft: EngineeringChangeDraft,
    ) -> EngineeringChangeProposal:
        self._require_target_absent(draft)
        self._require_create_parent(draft)

        try:
            return EngineeringChangeProposal(
                workspace_scope=draft.workspace_scope,
                operation=draft.operation,
                relative_path=draft.relative_path,
                base_state=EngineeringChangeBaseState.ABSENT,
                base_content=None,
                base_sha256=None,
                base_size_bytes=None,
                proposed_content=draft.proposed_content,
            )
        except ValueError as exc:
            raise self._map_contract_error(exc) from None

    def _propose_replace(
        self,
        draft: EngineeringChangeDraft,
    ) -> EngineeringChangeProposal:
        request = EngineeringReadRequest(
            workspace_scope=draft.workspace_scope,
            operation=EngineeringReadOperation.READ_TEXT,
            relative_path=draft.relative_path,
        )

        try:
            observed = self._reader.read(request)
        except EngineeringReadError as exc:
            raise self._map_replace_read_error(exc) from None

        try:
            return EngineeringChangeProposal(
                workspace_scope=draft.workspace_scope,
                operation=draft.operation,
                relative_path=draft.relative_path,
                base_state=EngineeringChangeBaseState.PRESENT,
                base_content=observed.content,
                base_sha256=observed.content_sha256,
                base_size_bytes=observed.size_bytes,
                proposed_content=draft.proposed_content,
            )
        except ValueError as exc:
            raise self._map_contract_error(exc) from None

    def _require_target_absent(
        self,
        draft: EngineeringChangeDraft,
    ) -> None:
        request = EngineeringReadRequest(
            workspace_scope=draft.workspace_scope,
            operation=EngineeringReadOperation.STAT_PATH,
            relative_path=draft.relative_path,
        )

        try:
            self._reader.read(request)
        except EngineeringReadError as exc:
            if exc.code == "engineering_path_not_found":
                return
            raise self._map_common_read_error(exc) from None

        raise EngineeringChangeProposalError(
            "engineering_change_target_exists"
        )

    def _require_create_parent(
        self,
        draft: EngineeringChangeDraft,
    ) -> None:
        if "/" not in draft.relative_path:
            # The server-owned repository root is the parent.
            return

        parent = draft.relative_path.rsplit("/", 1)[0]
        request = EngineeringReadRequest(
            workspace_scope=draft.workspace_scope,
            operation=EngineeringReadOperation.STAT_PATH,
            relative_path=parent,
        )

        try:
            observed = self._reader.read(request)
        except EngineeringReadError as exc:
            if exc.code == "engineering_path_not_found":
                raise EngineeringChangeProposalError(
                    "engineering_change_parent_not_found"
                ) from None
            if exc.code == "engineering_path_not_directory":
                raise EngineeringChangeProposalError(
                    "engineering_change_parent_not_directory"
                ) from None
            raise self._map_common_read_error(exc) from None

        if observed.entry.kind != "directory":
            raise EngineeringChangeProposalError(
                "engineering_change_parent_not_directory"
            )

    @staticmethod
    def _map_common_read_error(
        exc: EngineeringReadError,
    ) -> EngineeringChangeProposalError:
        mapping = {
            "engineering_path_invalid": "engineering_change_path_invalid",
            "engineering_path_not_allowed": "engineering_change_path_not_allowed",
            "engineering_read_unavailable": (
                "engineering_change_observation_unavailable"
            ),
            "engineering_workspace_invalid": (
                "engineering_change_workspace_invalid"
            ),
        }
        return EngineeringChangeProposalError(
            mapping.get(
                exc.code,
                "engineering_change_observation_unavailable",
            )
        )

    @classmethod
    def _map_replace_read_error(
        cls,
        exc: EngineeringReadError,
    ) -> EngineeringChangeProposalError:
        mapping = {
            "engineering_path_not_found": (
                "engineering_change_target_not_found"
            ),
            "engineering_path_not_file": "engineering_change_base_not_text",
            "engineering_file_not_text": "engineering_change_base_not_text",
            "engineering_file_too_large": (
                "engineering_change_base_too_large"
            ),
        }
        if exc.code in mapping:
            return EngineeringChangeProposalError(mapping[exc.code])
        return cls._map_common_read_error(exc)

    @staticmethod
    def _map_contract_error(exc: ValueError) -> EngineeringChangeProposalError:
        code = str(exc)
        allowed = {
            "engineering_change_request_invalid",
            "engineering_change_operation_invalid",
            "engineering_change_path_invalid",
            "engineering_change_path_not_allowed",
            "engineering_change_base_not_text",
            "engineering_change_base_too_large",
            "engineering_change_proposed_content_invalid",
            "engineering_change_proposed_content_too_large",
            "engineering_change_noop",
            "engineering_change_canonicalization_failed",
            "engineering_change_workspace_invalid",
            "engineering_change_base_state_invalid",
            "engineering_change_base_digest_invalid",
            "engineering_change_base_size_invalid",
            "engineering_change_proposed_digest_invalid",
            "engineering_change_proposed_size_invalid",
            "engineering_change_contract_version_invalid",
        }
        if code in allowed:
            return EngineeringChangeProposalError(code)
        return EngineeringChangeProposalError(
            "engineering_change_observation_unavailable"
        )


__all__ = [
    "EngineeringChangeProposalError",
    "EngineeringChangeProposalService",
]
