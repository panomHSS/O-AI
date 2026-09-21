from dataclasses import fields
from uuid import uuid4

import pytest

from app.contracts.engineering_ai_draft import (
    ENGINEERING_AI_DRAFT_CONTRACT_VERSION,
    ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS,
    EngineeringAIDraftRequest,
    EngineeringAIDraftResult,
)
from app.contracts.engineering_read import ENGINEERING_TEXT_MAX_BYTES


def test_d110_request_surface_is_exact_and_non_authoritative() -> None:
    assert tuple(item.name for item in fields(EngineeringAIDraftRequest)) == (
        "conversation_id",
        "relative_path",
        "instruction",
    )
    forbidden = {
        "workspace_scope",
        "workspace_id",
        "repository_root",
        "operation",
        "provider",
        "model",
        "approval_id",
        "proposal_digest",
        "apply",
        "tool",
        "shell",
    }
    assert forbidden.isdisjoint(
        {item.name for item in fields(EngineeringAIDraftRequest)}
    )


def test_d110_request_validates_path_and_instruction() -> None:
    cid = uuid4()
    value = EngineeringAIDraftRequest(
        conversation_id=cid,
        relative_path="backend/app.py",
        instruction="  add a safe test  ",
    )
    assert value.instruction == "add a safe test"

    with pytest.raises(ValueError, match="engineering_ai_draft_request_invalid"):
        EngineeringAIDraftRequest(
            conversation_id=cid,
            relative_path="backend/app.py",
            instruction="x" * (ENGINEERING_AI_DRAFT_INSTRUCTION_MAX_CHARS + 1),
        )

    with pytest.raises(ValueError, match="engineering_ai_draft_path_invalid"):
        EngineeringAIDraftRequest(
            conversation_id=cid,
            relative_path="../escape.py",
            instruction="safe",
        )


def test_d110_result_contract_is_frozen() -> None:
    assert tuple(item.name for item in fields(EngineeringAIDraftResult)) == (
        "contract_version",
        "conversation_id",
        "relative_path",
        "draft_operation",
        "source_state",
        "source_sha256",
        "source_size_bytes",
        "draft_content",
        "ai_adapter_id",
    )
    result = EngineeringAIDraftResult(
        conversation_id=uuid4(),
        relative_path="new.txt",
        draft_operation="create_text",
        source_state="absent",
        source_sha256=None,
        source_size_bytes=None,
        draft_content="candidate\n",
        ai_adapter_id="local_ai.default",
    )
    assert result.contract_version == ENGINEERING_AI_DRAFT_CONTRACT_VERSION
    assert result.contract_version == "d110.v1"


def test_d110_present_source_requires_replace_shape() -> None:
    EngineeringAIDraftResult(
        conversation_id=uuid4(),
        relative_path="existing.txt",
        draft_operation="replace_text",
        source_state="present",
        source_sha256="a" * 64,
        source_size_bytes=4,
        draft_content="next",
        ai_adapter_id="local_ai.default",
    )
    with pytest.raises(ValueError, match="engineering_ai_draft_output_invalid"):
        EngineeringAIDraftResult(
            conversation_id=uuid4(),
            relative_path="existing.txt",
            draft_operation="create_text",
            source_state="present",
            source_sha256="a" * 64,
            source_size_bytes=4,
            draft_content="next",
            ai_adapter_id="local_ai.default",
        )


def test_d110_output_reuses_d107_effective_limit() -> None:
    with pytest.raises(ValueError, match="engineering_ai_draft_too_large"):
        EngineeringAIDraftResult(
            conversation_id=uuid4(),
            relative_path="new.txt",
            draft_operation="create_text",
            source_state="absent",
            source_sha256=None,
            source_size_bytes=None,
            draft_content="x" * (ENGINEERING_TEXT_MAX_BYTES + 1),
            ai_adapter_id="local_ai.default",
        )
