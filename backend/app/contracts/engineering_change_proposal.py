"""D107 immutable Engineering Change Proposal contracts.

These contracts describe one reviewable proposed text-file change only.
They grant no owner approval, authorization, claim, filesystem mutation,
Tool/Module execution, shell/process, Git, network, credential, or apply authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.contracts.engineering_read import (
    ENGINEERING_TEXT_MAX_BYTES,
    validate_engineering_relative_path,
)
from app.contracts.workspace import WorkspaceScope


ENGINEERING_CHANGE_CONTRACT_VERSION = "d107.v1"


class EngineeringChangeOperation(Enum):
    """The exact D107 v1 proposal operations."""

    CREATE_TEXT = "create_text"
    REPLACE_TEXT = "replace_text"


class EngineeringChangeBaseState(Enum):
    """Observed base-state shape bound into one proposal."""

    ABSENT = "absent"
    PRESENT = "present"


def validate_engineering_change_content(value: object) -> str:
    """Validate exact bounded UTF-8 proposal text without normalization."""

    if type(value) is not str:
        raise ValueError("engineering_change_proposed_content_invalid")
    if "\x00" in value:
        raise ValueError("engineering_change_proposed_content_invalid")
    try:
        raw = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("engineering_change_proposed_content_invalid") from None
    if len(raw) > ENGINEERING_TEXT_MAX_BYTES:
        raise ValueError("engineering_change_proposed_content_too_large")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_sha256(value: object, *, code: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(code)
    return value


@dataclass(frozen=True, slots=True)
class EngineeringChangeDraft:
    """Untrusted D107 proposal input.

    No repository root, base state, digest, approval, or apply fields exist here.
    """

    workspace_scope: WorkspaceScope
    operation: EngineeringChangeOperation
    relative_path: str
    proposed_content: str

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_change_workspace_invalid")
        if not isinstance(self.operation, EngineeringChangeOperation):
            raise ValueError("engineering_change_operation_invalid")
        try:
            validate_engineering_relative_path(self.relative_path)
        except ValueError:
            raise ValueError("engineering_change_path_invalid") from None
        validate_engineering_change_content(self.proposed_content)


def canonical_engineering_change_projection(
    *,
    contract_version: str,
    workspace_scope: WorkspaceScope,
    operation: EngineeringChangeOperation,
    relative_path: str,
    base_state: EngineeringChangeBaseState,
    base_content: str | None,
    base_sha256: str | None,
    base_size_bytes: int | None,
    proposed_content: str,
    proposed_sha256: str,
    proposed_size_bytes: int,
) -> dict[str, Any]:
    """Return the exact authoritative D107 canonical projection."""

    if contract_version != ENGINEERING_CHANGE_CONTRACT_VERSION:
        raise ValueError("engineering_change_contract_version_invalid")
    if not isinstance(workspace_scope, WorkspaceScope):
        raise ValueError("engineering_change_workspace_invalid")
    if not isinstance(operation, EngineeringChangeOperation):
        raise ValueError("engineering_change_operation_invalid")
    if not isinstance(base_state, EngineeringChangeBaseState):
        raise ValueError("engineering_change_base_state_invalid")

    try:
        validate_engineering_relative_path(relative_path)
    except ValueError:
        raise ValueError("engineering_change_path_invalid") from None

    validate_engineering_change_content(proposed_content)
    proposed_raw = proposed_content.encode("utf-8")
    _validate_sha256(
        proposed_sha256,
        code="engineering_change_proposed_digest_invalid",
    )
    if proposed_sha256 != hashlib.sha256(proposed_raw).hexdigest():
        raise ValueError("engineering_change_proposed_digest_invalid")
    if (
        type(proposed_size_bytes) is not int
        or proposed_size_bytes != len(proposed_raw)
    ):
        raise ValueError("engineering_change_proposed_size_invalid")

    if base_state is EngineeringChangeBaseState.ABSENT:
        if (
            base_content is not None
            or base_sha256 is not None
            or base_size_bytes is not None
        ):
            raise ValueError("engineering_change_base_state_invalid")
    else:
        if type(base_content) is not str:
            raise ValueError("engineering_change_base_state_invalid")
        try:
            base_raw = base_content.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("engineering_change_base_not_text") from None
        if b"\x00" in base_raw:
            raise ValueError("engineering_change_base_not_text")
        if len(base_raw) > ENGINEERING_TEXT_MAX_BYTES:
            raise ValueError("engineering_change_base_too_large")
        _validate_sha256(
            base_sha256,
            code="engineering_change_base_digest_invalid",
        )
        if base_sha256 != hashlib.sha256(base_raw).hexdigest():
            raise ValueError("engineering_change_base_digest_invalid")
        if (
            type(base_size_bytes) is not int
            or base_size_bytes != len(base_raw)
        ):
            raise ValueError("engineering_change_base_size_invalid")

    return {
        "contract_version": contract_version,
        "workspace_id": workspace_scope.workspace_id.value,
        "operation": operation.value,
        "relative_path": relative_path,
        "base_state": base_state.value,
        "base_content": base_content,
        "base_sha256": base_sha256,
        "base_size_bytes": base_size_bytes,
        "proposed_content": proposed_content,
        "proposed_sha256": proposed_sha256,
        "proposed_size_bytes": proposed_size_bytes,
    }


def canonical_engineering_change_bytes(projection: dict[str, Any]) -> bytes:
    """Serialize one exact canonical proposal projection."""

    try:
        return json.dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise ValueError("engineering_change_canonicalization_failed") from None


def engineering_change_digest(projection: dict[str, Any]) -> str:
    """Return lowercase SHA-256 over canonical D107 proposal bytes."""

    return hashlib.sha256(
        canonical_engineering_change_bytes(projection)
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class EngineeringChangeProposal:
    """One immutable exact before/after engineering change review artifact."""

    workspace_scope: WorkspaceScope
    operation: EngineeringChangeOperation
    relative_path: str
    base_state: EngineeringChangeBaseState
    base_content: str | None
    base_sha256: str | None
    base_size_bytes: int | None
    proposed_content: str

    contract_version: str = field(
        default=ENGINEERING_CHANGE_CONTRACT_VERSION,
        init=False,
    )
    proposed_sha256: str = field(init=False)
    proposed_size_bytes: int = field(init=False)
    proposal_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_change_workspace_invalid")
        if not isinstance(self.operation, EngineeringChangeOperation):
            raise ValueError("engineering_change_operation_invalid")
        if not isinstance(self.base_state, EngineeringChangeBaseState):
            raise ValueError("engineering_change_base_state_invalid")

        try:
            validate_engineering_relative_path(self.relative_path)
        except ValueError:
            raise ValueError("engineering_change_path_invalid") from None

        validate_engineering_change_content(self.proposed_content)
        proposed_raw = self.proposed_content.encode("utf-8")
        proposed_sha256 = hashlib.sha256(proposed_raw).hexdigest()

        if self.operation is EngineeringChangeOperation.CREATE_TEXT:
            if self.base_state is not EngineeringChangeBaseState.ABSENT:
                raise ValueError("engineering_change_base_state_invalid")
            if (
                self.base_content is not None
                or self.base_sha256 is not None
                or self.base_size_bytes is not None
            ):
                raise ValueError("engineering_change_base_state_invalid")

        elif self.operation is EngineeringChangeOperation.REPLACE_TEXT:
            if self.base_state is not EngineeringChangeBaseState.PRESENT:
                raise ValueError("engineering_change_base_state_invalid")
            if type(self.base_content) is not str:
                raise ValueError("engineering_change_base_state_invalid")
            try:
                base_raw = self.base_content.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("engineering_change_base_not_text") from None
            if b"\x00" in base_raw:
                raise ValueError("engineering_change_base_not_text")
            if len(base_raw) > ENGINEERING_TEXT_MAX_BYTES:
                raise ValueError("engineering_change_base_too_large")

            _validate_sha256(
                self.base_sha256,
                code="engineering_change_base_digest_invalid",
            )
            if self.base_sha256 != hashlib.sha256(base_raw).hexdigest():
                raise ValueError("engineering_change_base_digest_invalid")
            if (
                type(self.base_size_bytes) is not int
                or self.base_size_bytes != len(base_raw)
            ):
                raise ValueError("engineering_change_base_size_invalid")
            if proposed_raw == base_raw:
                raise ValueError("engineering_change_noop")

        object.__setattr__(self, "proposed_sha256", proposed_sha256)
        object.__setattr__(self, "proposed_size_bytes", len(proposed_raw))

        projection = canonical_engineering_change_projection(
            contract_version=self.contract_version,
            workspace_scope=self.workspace_scope,
            operation=self.operation,
            relative_path=self.relative_path,
            base_state=self.base_state,
            base_content=self.base_content,
            base_sha256=self.base_sha256,
            base_size_bytes=self.base_size_bytes,
            proposed_content=self.proposed_content,
            proposed_sha256=proposed_sha256,
            proposed_size_bytes=len(proposed_raw),
        )
        object.__setattr__(
            self,
            "proposal_digest",
            engineering_change_digest(projection),
        )

    def canonical_projection(self) -> dict[str, Any]:
        return canonical_engineering_change_projection(
            contract_version=self.contract_version,
            workspace_scope=self.workspace_scope,
            operation=self.operation,
            relative_path=self.relative_path,
            base_state=self.base_state,
            base_content=self.base_content,
            base_sha256=self.base_sha256,
            base_size_bytes=self.base_size_bytes,
            proposed_content=self.proposed_content,
            proposed_sha256=self.proposed_sha256,
            proposed_size_bytes=self.proposed_size_bytes,
        )

    def canonical_bytes(self) -> bytes:
        return canonical_engineering_change_bytes(self.canonical_projection())


__all__ = [
    "ENGINEERING_CHANGE_CONTRACT_VERSION",
    "EngineeringChangeBaseState",
    "EngineeringChangeDraft",
    "EngineeringChangeOperation",
    "EngineeringChangeProposal",
    "canonical_engineering_change_bytes",
    "canonical_engineering_change_projection",
    "engineering_change_digest",
    "validate_engineering_change_content",
]
