from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from app.api.v1 import engineering
from app.schemas.engineering_owner import (
    EngineeringOwnerDecisionRequest,
    EngineeringOwnerProposalRequest,
    EngineeringOwnerReadRequest,
)


def test_d109_api_routes_are_bounded() -> None:
    routes = {
        (route.path, tuple(sorted(route.methods or ())))
        for route in engineering.router.routes
    }

    assert ("/engineering/read", ("POST",)) in routes
    assert ("/engineering/proposals", ("POST",)) in routes
    assert (
        "/engineering/conversations/{conversation_id}/active",
        ("GET",),
    ) in routes
    assert (
        "/engineering/approvals/{approval_id}/approve",
        ("POST",),
    ) in routes
    assert (
        "/engineering/approvals/{approval_id}/deny",
        ("POST",),
    ) in routes
    assert (
        "/engineering/approvals/{approval_id}/apply",
        ("POST",),
    ) in routes


def test_d109_local_owner_marker_is_required() -> None:
    with pytest.raises(HTTPException) as error:
        engineering.require_local_engineering_owner_request_marker(None)

    assert error.value.status_code == 403
    engineering.require_local_engineering_owner_request_marker("1")


def test_d109_proposal_transport_forbids_authority_injection() -> None:
    with pytest.raises(Exception):
        EngineeringOwnerProposalRequest(
            conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            operation="create_text",
            relative_path="backend/new.py",
            proposed_content="value = 2\n",
            repository_root="D:/evil",
        )

    with pytest.raises(Exception):
        EngineeringOwnerReadRequest(
            conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            operation="read_text",
            relative_path="backend/app.py",
            workspace_id="company",
        )


def test_d109_decision_transport_accepts_no_apply_parameters() -> None:
    with pytest.raises(Exception):
        EngineeringOwnerDecisionRequest(
            conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            proposal_digest="a" * 64,
            path="backend/new.py",
        )

    with pytest.raises(Exception):
        EngineeringOwnerDecisionRequest(
            conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            proposal_digest="a" * 64,
            content="evil",
        )

    with pytest.raises(Exception):
        EngineeringOwnerDecisionRequest(
            conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            proposal_digest="a" * 64,
            repository_root="D:/evil",
        )


def test_d109_api_does_not_import_d48_or_generic_execution() -> None:
    source = inspect.getsource(engineering)
    assert "ToolRuntime" not in source
    assert "FilesystemCreateTextToolAdapter" not in source
    assert "FilesystemReplaceTextToolAdapter" not in source
    assert "ExecutionApprovalService" not in source
    assert "ExecutionPlanner" not in source
    assert "CommandExecutionCoordinator" not in source
