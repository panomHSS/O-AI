from dataclasses import FrozenInstanceError, fields
from uuid import uuid4

import pytest

from app.contracts.engineering_investigation import (
    ENGINEERING_INVESTIGATION_CONTRACT_VERSION,
    ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS,
    ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS,
    ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS,
    EngineeringInvestigationEvidenceItem,
    EngineeringInvestigationEvidencePack,
    EngineeringInvestigationRequest,
)
from app.contracts.workspace import WorkspaceId, WorkspaceScope


PERSONAL = WorkspaceScope(WorkspaceId.PERSONAL)


def test_d113_request_surface_is_provider_neutral_and_non_authoritative() -> None:
    assert tuple(
        item.name for item in fields(EngineeringInvestigationRequest)
    ) == (
        "conversation_id",
        "instruction",
        "focus_paths",
    )

    forbidden = {
        "workspace_scope",
        "workspace_id",
        "repository_root",
        "provider",
        "adapter_id",
        "model",
        "endpoint",
        "api_key",
        "credential",
        "tool",
        "shell",
        "git",
        "proposal",
        "approval",
        "apply",
        "skill_id",
    }
    assert forbidden.isdisjoint(
        {item.name for item in fields(EngineeringInvestigationRequest)}
    )


def test_d113_request_trims_instruction_and_preserves_focus_order() -> None:
    request = EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="  inspect these files safely  ",
        focus_paths=("backend/app.py", "README.md"),
    )
    assert request.instruction == "inspect these files safely"
    assert request.focus_paths == ("backend/app.py", "README.md")


def test_d113_request_rejects_invalid_instruction_paths_and_duplicates() -> None:
    cid = uuid4()

    with pytest.raises(
        ValueError,
        match="engineering_investigation_request_invalid",
    ):
        EngineeringInvestigationRequest(
            conversation_id=cid,
            instruction="x"
            * (ENGINEERING_INVESTIGATION_INSTRUCTION_MAX_CHARS + 1),
        )

    with pytest.raises(
        ValueError,
        match="engineering_investigation_path_invalid",
    ):
        EngineeringInvestigationRequest(
            conversation_id=cid,
            instruction="inspect",
            focus_paths=("../escape.py",),
        )

    with pytest.raises(
        ValueError,
        match="engineering_investigation_path_invalid",
    ):
        EngineeringInvestigationRequest(
            conversation_id=cid,
            instruction="inspect",
            focus_paths=("README.md", "README.md"),
        )

    with pytest.raises(
        ValueError,
        match="engineering_investigation_request_invalid",
    ):
        EngineeringInvestigationRequest(
            conversation_id=cid,
            instruction="inspect",
            focus_paths=tuple(
                f"file-{index}.txt"
                for index in range(
                    ENGINEERING_INVESTIGATION_MAX_FOCUS_PATHS + 1
                )
            ),
        )


def test_d113_evidence_item_requires_text_integrity_metadata() -> None:
    text = EngineeringInvestigationEvidenceItem(
        evidence_id="text:1",
        kind="text",
        relative_path="README.md",
        content="hello\n",
        size_bytes=6,
        content_sha256="a" * 64,
    )
    assert text.kind == "text"

    with pytest.raises(
        ValueError,
        match="engineering_investigation_evidence_invalid",
    ):
        EngineeringInvestigationEvidenceItem(
            evidence_id="text:1",
            kind="text",
            relative_path="README.md",
            content="hello\n",
        )


def test_d113_pack_is_bounded_and_overview_first() -> None:
    cid = uuid4()
    overview = EngineeringInvestigationEvidenceItem(
        evidence_id="overview:0",
        kind="repository_overview",
        relative_path=None,
        content="[]",
    )
    text = EngineeringInvestigationEvidenceItem(
        evidence_id="text:1",
        kind="text",
        relative_path="README.md",
        content="hello",
        size_bytes=5,
        content_sha256="b" * 64,
    )

    pack = EngineeringInvestigationEvidencePack(
        workspace_scope=PERSONAL,
        conversation_id=cid,
        instruction="inspect",
        focus_paths=("README.md",),
        evidence_items=(overview, text),
        omitted_paths=(),
        admitted_text_chars=5,
    )

    assert pack.contract_version == ENGINEERING_INVESTIGATION_CONTRACT_VERSION
    assert pack.contract_version == "d113.v1"

    with pytest.raises(
        ValueError,
        match="engineering_investigation_evidence_invalid",
    ):
        EngineeringInvestigationEvidencePack(
            workspace_scope=PERSONAL,
            conversation_id=cid,
            instruction="inspect",
            focus_paths=("README.md",),
            evidence_items=(text, overview),
            omitted_paths=(),
            admitted_text_chars=5,
        )

    oversized = "x" * (ENGINEERING_INVESTIGATION_MAX_TEXT_CHARS + 1)
    with pytest.raises(
        ValueError,
        match="engineering_investigation_evidence_invalid",
    ):
        EngineeringInvestigationEvidencePack(
            workspace_scope=PERSONAL,
            conversation_id=cid,
            instruction="inspect",
            focus_paths=("README.md",),
            evidence_items=(
                overview,
                EngineeringInvestigationEvidenceItem(
                    evidence_id="text:2",
                    kind="text",
                    relative_path="README.md",
                    content=oversized,
                    size_bytes=len(oversized),
                    content_sha256="c" * 64,
                ),
            ),
            omitted_paths=(),
            admitted_text_chars=len(oversized),
        )


def test_d113_contracts_are_frozen() -> None:
    request = EngineeringInvestigationRequest(
        conversation_id=uuid4(),
        instruction="inspect",
    )
    with pytest.raises(FrozenInstanceError):
        request.instruction = "changed"  # type: ignore[misc]