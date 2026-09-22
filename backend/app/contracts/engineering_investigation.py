"""D113 provider-neutral Engineering Investigation contracts.

D113 investigation data is read-only and non-authoritative. These contracts
grant no repository mutation, D107 proposal, D108 apply, owner approval,
provider/model/credential, Tool/Module, connector, shell/process, Git, network,
or Skill execution authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, TypeAlias
from uuid import UUID

from app.contracts.engineering_read import validate_engineering_relative_path
from app.contracts.workspace import WorkspaceScope


ENGINEERING_INVESTIGATION_CONTRACT_VERSION = "d113.v1"
ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS = 8_000
ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS = 8
ENGINEERING_INVESTIGATION_MAX_TEXT_ITEMS = 8
ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS = 96_000

ENGINEERING_INVESTIGATION_MAX_EVIDENCE_ITEMS = (
    1 + (ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS * 2)
)
ENGINEERING_INVESTIGATION_EVIDENCE_ID_MAX_CHARS = 64

EngineeringInvestigationEvidenceKind: TypeAlias = Literal[
    "repository_overview",
    "path_stat",
    "directory_listing",
    "text",
]

_EVIDENCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._-]{0,63}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _validated_instruction(value: object) -> str:
    if type(value) is not str:
        raise ValueError("engineering_investigation_request_invalid")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("engineering_investigation_request_invalid") from None

    normalized = value.strip()
    if (
        not normalized
        or "\x00" in normalized
        or len(normalized)
        > ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS
    ):
        raise ValueError("engineering_investigation_request_invalid")
    return normalized


def _validated_focus_paths(value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError("engineering_investigation_request_invalid")
    if len(value) > ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS:
        raise ValueError("engineering_investigation_request_invalid")

    validated: list[str] = []
    for path in value:
        try:
            item = validate_engineering_relative_path(path)
        except ValueError:
            raise ValueError("engineering_investigation_path_invalid") from None
        if item in validated:
            raise ValueError("engineering_investigation_path_invalid")
        validated.append(item)

    return tuple(validated)


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationRequest:
    """Exact owner input for one read-only D113 investigation."""

    conversation_id: UUID
    instruction: str
    focus_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_investigation_request_invalid")

        object.__setattr__(
            self,
            "instruction",
            _validated_instruction(self.instruction),
        )
        object.__setattr__(
            self,
            "focus_paths",
            _validated_focus_paths(self.focus_paths),
        )


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationEvidenceItem:
    """One bounded server-built repository observation for later AI reasoning."""

    evidence_id: str
    kind: EngineeringInvestigationEvidenceKind
    relative_path: str | None
    content: str
    size_bytes: int | None = None
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.evidence_id) is not str
            or len(self.evidence_id)
            > ENGINEERING_INVESTIGATION_EVIDENCE_ID_MAX_CHARS
            or _EVIDENCE_ID_RE.fullmatch(self.evidence_id) is None
        ):
            raise ValueError("engineering_investigation_evidence_invalid")

        if self.kind not in {
            "repository_overview",
            "path_stat",
            "directory_listing",
            "text",
        }:
            raise ValueError("engineering_investigation_evidence_invalid")

        if self.kind == "repository_overview":
            if self.relative_path is not None:
                raise ValueError("engineering_investigation_evidence_invalid")
        else:
            try:
                validate_engineering_relative_path(self.relative_path)
            except ValueError:
                raise ValueError(
                    "engineering_investigation_evidence_invalid"
                ) from None

        if type(self.content) is not str or "\x00" in self.content:
            raise ValueError("engineering_investigation_evidence_invalid")
        try:
            self.content.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError(
                "engineering_investigation_evidence_invalid"
            ) from None

        if self.kind == "text":
            if (
                type(self.size_bytes) is not int
                or self.size_bytes < 0
                or type(self.content_sha256) is not str
                or _SHA256_RE.fullmatch(self.content_sha256) is None
            ):
                raise ValueError("engineering_investigation_evidence_invalid")
        elif self.content_sha256 is not None:
            raise ValueError("engineering_investigation_evidence_invalid")
        elif self.size_bytes is not None and (
            type(self.size_bytes) is not int or self.size_bytes < 0
        ):
            raise ValueError("engineering_investigation_evidence_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationEvidencePack:
    """One deterministic D113 evidence pack; data only, never authority."""

    contract_version: str = field(
        default=ENGINEERING_INVESTIGATION_CONTRACT_VERSION,
        init=False,
    )
    workspace_scope: WorkspaceScope
    conversation_id: UUID
    instruction: str
    focus_paths: tuple[str, ...]
    evidence_items: tuple[EngineeringInvestigationEvidenceItem, ...]
    omitted_paths: tuple[str, ...]
    admitted_text_chars: int

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_scope, WorkspaceScope):
            raise ValueError("engineering_investigation_evidence_invalid")
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_investigation_evidence_invalid")

        object.__setattr__(
            self,
            "instruction",
            _validated_instruction(self.instruction),
        )
        object.__setattr__(
            self,
            "focus_paths",
            _validated_focus_paths(self.focus_paths),
        )

        if type(self.evidence_items) is not tuple:
            raise ValueError("engineering_investigation_evidence_invalid")
        if (
            not self.evidence_items
            or len(self.evidence_items)
            > ENGINEERING_INVESTIGATION_MAX_EVIDENCE_ITEMS
            or any(
                not isinstance(item, EngineeringInvestigationEvidenceItem)
                for item in self.evidence_items
            )
        ):
            raise ValueError("engineering_investigation_evidence_invalid")

        if self.evidence_items[0].kind != "repository_overview":
            raise ValueError("engineering_investigation_evidence_invalid")
        if sum(
            item.kind == "repository_overview"
            for item in self.evidence_items
        ) != 1:
            raise ValueError("engineering_investigation_evidence_invalid")

        evidence_ids = tuple(item.evidence_id for item in self.evidence_items)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("engineering_investigation_evidence_invalid")

        if type(self.omitted_paths) is not tuple:
            raise ValueError("engineering_investigation_evidence_invalid")
        if len(set(self.omitted_paths)) != len(self.omitted_paths):
            raise ValueError("engineering_investigation_evidence_invalid")
        for path in self.omitted_paths:
            try:
                validate_engineering_relative_path(path)
            except ValueError:
                raise ValueError(
                    "engineering_investigation_evidence_invalid"
                ) from None
            if path not in self.focus_paths:
                raise ValueError("engineering_investigation_evidence_invalid")

        text_items = tuple(
            item for item in self.evidence_items if item.kind == "text"
        )
        if len(text_items) > ENGINEERING_INVESTIGATION_MAX_TEXT_ITEMS:
            raise ValueError("engineering_investigation_evidence_invalid")

        expected_chars = sum(len(item.content) for item in text_items)
        if (
            type(self.admitted_text_chars) is not int
            or self.admitted_text_chars != expected_chars
            or self.admitted_text_chars < 0
            or self.admitted_text_chars
            > ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS
        ):
            raise ValueError("engineering_investigation_evidence_invalid")


ENGINEERING_INVESTIGATION_SUMMARY_MAX_CHARS = 4_000
ENGINEERING_INVESTIGATION_MAX_FINDINGS = 12
ENGINEERING_INVESTIGATION_FINDING_TITLE_MAX_CHARS = 200
ENGINEERING_INVESTIGATION_FINDING_DETAIL_MAX_CHARS = 2_000
ENGINEERING_INVESTIGATION_MAX_CHANGE_PLAN_ITEMS = 12
ENGINEERING_INVESTIGATION_PLAN_TITLE_MAX_CHARS = 200
ENGINEERING_INVESTIGATION_PLAN_RATIONALE_MAX_CHARS = 2_000
ENGINEERING_INVESTIGATION_MAX_RESULT_EVIDENCE_REFS = 8

EngineeringInvestigationConfidence: TypeAlias = Literal[
    "low",
    "medium",
    "high",
]
EngineeringInvestigationChangeKind: TypeAlias = Literal[
    "inspect",
    "create_text",
    "replace_text",
    "test",
    "documentation",
    "configuration",
    "other",
]

_FINDING_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _validated_result_text(
    value: object,
    *,
    max_chars: int,
    code: str = "engineering_investigation_result_invalid",
) -> str:
    if type(value) is not str:
        raise ValueError(code)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    normalized = value.strip()
    if not normalized or "\x00" in normalized or len(normalized) > max_chars:
        raise ValueError(code)
    return normalized


def _validated_result_evidence_refs(value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError("engineering_investigation_result_invalid")
    if len(value) > ENGINEERING_INVESTIGATION_MAX_RESULT_EVIDENCE_REFS:
        raise ValueError("engineering_investigation_result_invalid")
    if len(set(value)) != len(value):
        raise ValueError("engineering_investigation_result_invalid")
    for evidence_id in value:
        if (
            type(evidence_id) is not str
            or len(evidence_id)
            > ENGINEERING_INVESTIGATION_EVIDENCE_ID_MAX_CHARS
            or _EVIDENCE_ID_RE.fullmatch(evidence_id) is None
        ):
            raise ValueError("engineering_investigation_result_invalid")
    return value


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationFinding:
    """One bounded AI finding; descriptive only, never authority."""

    finding_id: str
    title: str
    detail: str
    evidence_refs: tuple[str, ...]
    confidence: EngineeringInvestigationConfidence

    def __post_init__(self) -> None:
        if (
            type(self.finding_id) is not str
            or _FINDING_ID_RE.fullmatch(self.finding_id) is None
        ):
            raise ValueError("engineering_investigation_result_invalid")
        object.__setattr__(
            self,
            "title",
            _validated_result_text(
                self.title,
                max_chars=ENGINEERING_INVESTIGATION_FINDING_TITLE_MAX_CHARS,
            ),
        )
        object.__setattr__(
            self,
            "detail",
            _validated_result_text(
                self.detail,
                max_chars=ENGINEERING_INVESTIGATION_FINDING_DETAIL_MAX_CHARS,
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_result_evidence_refs(self.evidence_refs),
        )
        if self.confidence not in {"low", "medium", "high"}:
            raise ValueError("engineering_investigation_result_invalid")


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationChangePlanItem:
    """One non-authoritative suggested change-plan item."""

    sequence: int
    title: str
    rationale: str
    candidate_relative_path: str | None
    candidate_change_kind: EngineeringInvestigationChangeKind
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int
            or self.sequence < 1
            or self.sequence > ENGINEERING_INVESTIGATION_MAX_CHANGE_PLAN_ITEMS
        ):
            raise ValueError("engineering_investigation_result_invalid")
        object.__setattr__(
            self,
            "title",
            _validated_result_text(
                self.title,
                max_chars=ENGINEERING_INVESTIGATION_PLAN_TITLE_MAX_CHARS,
            ),
        )
        object.__setattr__(
            self,
            "rationale",
            _validated_result_text(
                self.rationale,
                max_chars=ENGINEERING_INVESTIGATION_PLAN_RATIONALE_MAX_CHARS,
            ),
        )
        if self.candidate_relative_path is not None:
            try:
                validate_engineering_relative_path(
                    self.candidate_relative_path
                )
            except ValueError:
                raise ValueError(
                    "engineering_investigation_result_invalid"
                ) from None
        if self.candidate_change_kind not in {
            "inspect",
            "create_text",
            "replace_text",
            "test",
            "documentation",
            "configuration",
            "other",
        }:
            raise ValueError("engineering_investigation_result_invalid")
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_result_evidence_refs(self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class EngineeringInvestigationResult:
    """One structured non-authoritative D113 investigation result."""

    contract_version: str = field(
        default=ENGINEERING_INVESTIGATION_CONTRACT_VERSION,
        init=False,
    )
    conversation_id: UUID
    summary: str
    findings: tuple[EngineeringInvestigationFinding, ...]
    change_plan: tuple[EngineeringInvestigationChangePlanItem, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conversation_id, UUID):
            raise ValueError("engineering_investigation_result_invalid")
        object.__setattr__(
            self,
            "summary",
            _validated_result_text(
                self.summary,
                max_chars=ENGINEERING_INVESTIGATION_SUMMARY_MAX_CHARS,
            ),
        )
        if (
            type(self.findings) is not tuple
            or len(self.findings) > ENGINEERING_INVESTIGATION_MAX_FINDINGS
            or any(
                not isinstance(item, EngineeringInvestigationFinding)
                for item in self.findings
            )
        ):
            raise ValueError("engineering_investigation_result_invalid")
        finding_ids = tuple(item.finding_id for item in self.findings)
        if len(set(finding_ids)) != len(finding_ids):
            raise ValueError("engineering_investigation_result_invalid")

        if (
            type(self.change_plan) is not tuple
            or len(self.change_plan)
            > ENGINEERING_INVESTIGATION_MAX_CHANGE_PLAN_ITEMS
            or any(
                not isinstance(
                    item,
                    EngineeringInvestigationChangePlanItem,
                )
                for item in self.change_plan
            )
        ):
            raise ValueError("engineering_investigation_result_invalid")
        if tuple(item.sequence for item in self.change_plan) != tuple(
            range(1, len(self.change_plan) + 1)
        ):
            raise ValueError("engineering_investigation_result_invalid")

        object.__setattr__(
            self,
            "evidence_refs",
            _validated_result_evidence_refs(self.evidence_refs),
        )

__all__ = [
    "ENGINEERING_INVESTIGATION_CONTRACT_VERSION",
    "ENGINEERING_INVESTIGATION_EVIDENCE_ID_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_MAX_EVIDENCE_ITEMS",
    "ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS",
    "ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS",
    "ENGINEERING_INVESTIGATION_MAX_TEXT_ITEMS",
    "ENGINEERING_INVESTIGATION_FINDING_DETAIL_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_FINDING_TITLE_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_MAX_CHANGE_PLAN_ITEMS",
    "ENGINEERING_INVESTIGATION_MAX_FINDINGS",
    "ENGINEERING_INVESTIGATION_MAX_RESULT_EVIDENCE_REFS",
    "ENGINEERING_INVESTIGATION_PLAN_RATIONALE_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_PLAN_TITLE_MAX_CHARS",
    "ENGINEERING_INVESTIGATION_SUMMARY_MAX_CHARS",
    "EngineeringInvestigationChangeKind",
    "EngineeringInvestigationChangePlanItem",
    "EngineeringInvestigationConfidence",
    "EngineeringInvestigationEvidenceItem",
    "EngineeringInvestigationEvidenceKind",
    "EngineeringInvestigationEvidencePack",
    "EngineeringInvestigationFinding",
    "EngineeringInvestigationRequest",
    "EngineeringInvestigationResult",
]