import ast
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
import pytest
from app.contracts.command import CommandRequest
from app.contracts.cognitive_runtime_rollout import CognitiveRuntimeRolloutDecision
from app.schemas.chat import ChatRequest
from app.services.cognitive_runtime_rollout import CognitiveRuntimeRolloutSelector
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ConversationService

ROOT=Path(__file__).resolve().parents[2]
FIXED=UUID("11111111-1111-1111-1111-111111111111"); OTHER=UUID("22222222-2222-2222-2222-222222222222"); PROJECT=UUID("33333333-3333-3333-3333-333333333333")
def t(p): return (ROOT/p).read_text(encoding="utf-8")
def imports(p):
    tree=ast.parse(t(p)); r=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): r.update(a.name for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: r.add(n.module)
    return r
class R:
    workspace_id="personal"
    def __init__(self): self.current=None
    def create(self,title,project_id=None): self.current=SimpleNamespace(id=str(FIXED),project_id=project_id,workspace_id="personal"); return self.current
    def get(self,cid): return self.current if self.current is not None and self.current.id==cid else None
    def project_exists(self,p): return True
    def rollback(self): pass
def service(): return ConversationService(repository=R(),chat_service=object(),context_message_limit=20)
def dec(**kw):
    a=dict(enabled=True,cognitive_eligible=True,stage="full",conversation_id=FIXED); a.update(kw); return CognitiveRuntimeRolloutSelector.evaluate(**a)

def run_case(c):
    if 1<=c<=8:
        f=("rollout_stage","rollout_bps","rollout_bucket","rollout_hash","cognitive_candidate","rollout_control","automatic_promotion","rollout_authority")[c-1]; assert f not in ChatRequest.model_fields
    elif 9<=c<=16:
        names={x.name for x in fields(CognitiveRuntimeRolloutDecision)}; f=("message","prompt","response","context","memory","knowledge","secret","conversation_id")[c-9]; assert f not in names
    elif 17<=c<=24:
        im=imports("backend/app/services/cognitive_runtime_rollout.py"); f=("random","time","requests","httpx","sqlalchemy","subprocess","app.services.cognitive_runtime_assurance","app.services.cognitive_runtime_promotion_advisory")[c-17]; assert not any(m==f or m.startswith(f+".") for m in im)
    elif 25<=c<=31:
        r=dec(); n=("promotion_authority","rollback_authority","execution_authority","routing_authority","configuration_authority","automatic_stage_increase","automatic_stage_decrease")[c-25]; assert getattr(r,n) is False
    elif 32<=c<=39:
        v=({"enabled":"true"},{"cognitive_eligible":1},{"stage":None},{"stage":object()},{"stage":"ready"},{"conversation_id":"bad","stage":"canary_10"},{"conversation_id":1,"stage":"canary_10"},{"conversation_id":object(),"stage":"canary_10"})[c-32]; assert dec(**v).disposition!="cognitive"
    elif 40<=c<=45:
        original=CommandRequest(request_id="turn-1",command="chat.message",arguments={"message":"hello","conversation_id":OTHER,"project_id":PROJECT})
        before=dict(original.arguments); binding=SimpleNamespace(conversation_id=FIXED,project_id=PROJECT)
        normalized=CommandOrchestrator._d144_server_bound_cognitive_command(command=original,message="hello",binding=binding)
        checks=(normalized.arguments["conversation_id"]==FIXED,normalized.arguments["conversation_id"]!=OTHER,normalized.arguments["project_id"] is None,normalized.request_id==original.request_id,normalized.arguments["message"]==original.arguments["message"],dict(original.arguments)==before)
        assert checks[c-40]
    elif c==46:
        s=t("backend/app/services/command_orchestrator.py")
        process=s[s.index("    def process_chat("):s.index("    def execute_tool(")]
        assert process.index("rollout = self._d144_rollout_binding(")<process.index("cognitive_command = self._d144_server_bound_cognitive_command(")
        helper=s[s.index("    def _d144_rollout_binding("):s.index("    @staticmethod\n    def _d144_server_bound_cognitive_command(")]
        assert "reserve_cognitive_turn(" in helper
    elif c==47:
        assert "self._cognitive_executive.process_chat(\n                        cognitive_command," in t("backend/app/services/command_orchestrator.py")
    elif c==48:
        s=t("backend/app/services/command_orchestrator.py"); a=s.index("if self._cognitive_executive is not None:"); b=s.index('selected_lane="legacy"',a); assert "self._planner.plan(" not in s[a:b]
    elif c==49:
        s=t("backend/app/services/command_orchestrator.py"); assert "for attempt" not in s and "while " not in s
    elif c==50:
        s=t("backend/app/services/command_orchestrator.py"); a=s.index("if self._cognitive_executive is not None:"); b=s.index('selected_lane="legacy"',a); assert "self._ai_runtime.bind(" not in s[a:b]
    elif c==51: assert t("backend/app/services/command_orchestrator.py").count("CognitiveRuntimeRolloutSelector.evaluate(")==1
    elif c==52:
        s=t("backend/app/services/command_orchestrator.py"); assert "type(self._conversation_service) is not ConversationService" in s and s.index("reserve_cognitive_turn(")<s.index("CognitiveRuntimeRolloutSelector.evaluate(")
    elif c==53:
        s=t("backend/app/services/cognitive_runtime_rollout.py").lower()
        for f in ("workspace","project","message","prompt"): assert f not in s
    elif c==54: assert "D142_" not in t("backend/app/services/cognitive_runtime_rollout.py")
    elif c==55: assert not any("promotion_advisory" in m for m in imports("backend/app/services/cognitive_runtime_rollout.py"))
    elif c==56: assert not any("assurance" in m for m in imports("backend/app/services/cognitive_runtime_rollout.py"))
    elif c==57: assert "cognitive_runtime_rollout" not in t("backend/app/services/cognitive_runtime_promotion_advisory.py")
    elif c==58:
        s=t("backend/app/services/cognitive_runtime_rollout.py"); assert "setattr(" not in s and "os.environ" not in s
    elif c==59:
        s=t("backend/app/services/cognitive_runtime_rollout.py").lower()
        for f in ("model_id","provider","profile_id"): assert f not in s
    elif c==60: assert "rollout" not in t("backend/app/api/v1/chat.py").lower() and "rollout" not in t("backend/app/api/v1/diagnostics.py").lower()
    elif c==61:
        s=t("backend/app/contracts/cognitive_runtime_rollout.py")+t("backend/app/services/cognitive_runtime_rollout.py"); assert "sqlalchemy" not in s and "alembic" not in s
    elif c==62:
        s=t("backend/app/services/cognitive_runtime_rollout.py").lower(); assert "thread" not in s and "scheduler" not in s and "background" not in s
    elif c==63: assert set(ChatRequest.model_fields)=={"message","conversation_id","project_id","ai_mode"}
    elif c==64:
        s=(t("backend/app/contracts/cognitive_runtime_rollout.py")+t("backend/app/services/cognitive_runtime_rollout.py")+t("backend/app/core/cognitive_runtime_rollout_config.py")).lower()
        for f in ("d138","subprocess","git "): assert f not in s
    else: raise AssertionError(c)

@pytest.mark.parametrize("case",range(1,65),ids=[f"S{i:02d}" for i in range(1,65)])
def test_d144_security_matrix(case): run_case(case)
