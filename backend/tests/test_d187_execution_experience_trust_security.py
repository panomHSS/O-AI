from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from app.contracts.governed_execution_experience_trust import (
    GovernedExecutionExperienceTrustPromotionProposal,
)


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (backend_root() / path).read_text(encoding="utf-8")


def test_d187_contract_has_no_raw_sensitive_or_owner_free_text_fields():
    names = {
        item.name
        for item in fields(GovernedExecutionExperienceTrustPromotionProposal)
    }
    assert names.isdisjoint(
        {
            "output",
            "error",
            "parameters",
            "payload",
            "prompt",
            "response",
            "credentials",
            "token",
            "secret",
            "decision_comment",
            "user_text",
            "assistant_text",
        }
    )
    combined = "\n".join(
        read(path)
        for path in (
            "app/contracts/governed_execution_experience_trust.py",
            "app/models/trusted_execution_experience.py",
            "app/schemas/trusted_execution_experiences.py",
        )
    )
    assert "decision_comment" not in combined


def test_d187_does_not_depend_on_d147_memory_ai_or_execution_authority():
    combined = "\n".join(
        read(path)
        for path in (
            "app/contracts/governed_execution_experience_trust.py",
            "app/models/trusted_execution_experience.py",
            "app/repositories/trusted_execution_experiences.py",
            "app/schemas/trusted_execution_experiences.py",
            "app/services/execution_experience_trust_lifecycle.py",
            "app/api/v1/trusted_execution_experiences.py",
        )
    )
    for forbidden in (
        "TrustedExperienceLifecycleService",
        "TrustedExperienceRepository",
        "TrustedExperienceRecord",
        "TrustedExperienceEventRecord",
        "CognitiveTrustedExperienceProposal",
        "TrustedExperienceRetrievalService",
        "MemoryService",
        "MemoryRepository",
        "CognitiveExecutive",
        "CognitiveInvocationCoordinator",
        "AIRuntime",
        "ExecutionApprovalService",
        "ExecutionPlanner",
        "ExecutionGuard",
        "CommandExecutionCoordinator",
        "ToolRuntime",
        "ModuleRuntime",
    ):
        assert forbidden not in combined


def test_d187_trusted_state_never_encodes_execution_or_learning_authority():
    contract = read("app/contracts/governed_execution_experience_trust.py")
    model = read("app/models/trusted_execution_experience.py")
    migration = read(
        "alembic/versions/0018_trusted_execution_experience_lifecycle.py"
    )
    assert '"TRUSTED"' in contract
    assert "state IN ('TRUSTED','REVOKED')" in model
    assert "state IN ('TRUSTED','REVOKED')" in migration
    assert "execution_authority: Literal[False] = False" in contract
    assert "learning_authority: Literal[False] = False" in contract
