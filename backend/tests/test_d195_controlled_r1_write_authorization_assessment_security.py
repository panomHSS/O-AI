"""D195 fail-closed, privacy, spoofing, and no-execution security checks."""
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from app.contracts.workspace import WorkspaceId, WorkspaceScope
from app.contracts.controlled_r1_write_authorization_assessment import AUTHORITY_FIELDS
from app.services.controlled_r1_write_authorization_assessment import ControlledR1WriteAuthorizationEvaluator
from tests.test_d195_controlled_r1_write_authorization_assessment import Source, assess, binding


@pytest.mark.parametrize("change", [
    lambda s: replace(s, query=replace(s.query, plan_digest="f"*64)),
    lambda s: replace(s, prior_use=replace(s.prior_use, covered_approval_id="wrong")),
    lambda s: replace(s, capability=replace(s.capability, adapter_id="other")),
    lambda s: replace(s, target=replace(s.target, operation="other")),
    lambda s: replace(s, evaluation_time=datetime(2026, 10, 23)),
    lambda s: replace(s, owner=replace(s.owner, revocation_state="forged")),
    lambda s: replace(s, target=replace(s.target, internal_scope=1)),
    lambda s: replace(s, prior_use=replace(s.prior_use, observation="unknown")),
    lambda s: replace(s, prior_use=replace(s.prior_use, coverage="incomplete")),
    lambda s: replace(s, target=replace(s.target, target_support="unknown")),
    lambda s: replace(s, coherence_state="invalid"),
])
def test_malformed_and_unknown_fail_closed(change):
    out = assess(change)
    assert out.status == "unavailable" and out.assessment_fingerprint is None
    assert all(getattr(out, f) is False for f in AUTHORITY_FIELDS)


def test_source_exception_no_stack_trace():
    class Broken:
        def retrieve(self, query):
            raise RuntimeError("TOP_SECRET_STACK_TRACE")
    b = binding()
    out = ControlledR1WriteAuthorizationEvaluator(workspace_scope=WorkspaceScope(b.workspace_id),
                                                   evidence_source=Broken()).evaluate(binding=b)
    assert out.reason_code == "r1_evidence_unavailable"
    assert "SECRET" not in repr(out)


def test_cross_workspace_binding_no_leak():
    out = ControlledR1WriteAuthorizationEvaluator(workspace_scope=WorkspaceScope(WorkspaceId.COMPANY),
                                                  evidence_source=Source()).evaluate(binding=binding())
    assert out.reason_code == "r1_evidence_invalid"
    assert out.source_intent_digest is None


def test_non_executing_static_boundary():
    service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "controlled_r1_write_authorization_assessment.py"
    contract_path = Path(__file__).resolve().parents[1] / "app" / "contracts" / "controlled_r1_write_authorization_assessment.py"
    source = service_path.read_text(encoding="utf-8") + contract_path.read_text(encoding="utf-8")
    import ast
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(n.startswith(("requests", "subprocess", "socket", "http", "sqlalchemy", "app.api", "app.adapters")) for n in names)
    assert "def execute(" not in source and "def write(" not in source
