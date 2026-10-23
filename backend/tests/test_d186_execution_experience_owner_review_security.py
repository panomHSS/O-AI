from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from app.contracts.governed_execution_experience_owner_review import (
    GovernedExecutionExperienceOwnerReviewProposal,
)


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (backend_root() / path).read_text(encoding="utf-8")


def test_d186_has_no_raw_sensitive_contract_fields_or_owner_free_text():
    names = {item.name for item in fields(GovernedExecutionExperienceOwnerReviewProposal)}
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
        }
    )
    assert "decision_comment" not in read("app/schemas/execution_experience_reviews.py")
    assert "decision_comment" not in read("app/models/execution_experience_review.py")


def test_d186_does_not_depend_on_d147_memory_ai_or_execution_authority():
    combined = "\n".join(
        read(path)
        for path in (
            "app/contracts/governed_execution_experience_owner_review.py",
            "app/models/execution_experience_review.py",
            "app/repositories/execution_experience_reviews.py",
            "app/schemas/execution_experience_reviews.py",
            "app/services/execution_experience_review_lifecycle.py",
            "app/api/v1/execution_experience_reviews.py",
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


def test_d186_never_models_review_acceptance_as_trust():
    contract = read("app/contracts/governed_execution_experience_owner_review.py")
    model = read("app/models/execution_experience_review.py")
    migration = read("alembic/versions/0017_execution_experience_review_lifecycle.py")
    for text in (contract, model, migration):
        assert "REVIEW_ACCEPTED" in text
        assert "'TRUSTED'" not in text
        assert '"TRUSTED"' not in text
