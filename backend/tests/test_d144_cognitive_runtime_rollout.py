from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import get_args
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.command import CommandRequest
from app.contracts.cognitive_runtime_rollout import (
    D144_REFERENCE_BASELINE, D144_ROLLOUT_BUCKET_COUNT,
    D144_SELECTION_SCOPE, D144_SELECTION_STRATEGY,
    D144_STAGE_BPS, CognitiveRuntimeRolloutStage,
)
from app.core.cognitive_runtime_rollout_config import CognitiveRuntimeRolloutSettings
from app.schemas.chat import ChatRequest
from app.services.cognitive_runtime_rollout import CognitiveRuntimeRolloutSelector
from app.services.command_orchestrator import CommandOrchestrator
from app.services.conversations import ConversationService

ROOT = Path(__file__).resolve().parents[2]
FIXED = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")
PROJECT = UUID("33333333-3333-3333-3333-333333333333")
STAGES = ("control_only","canary_1","canary_5","canary_10","canary_25","canary_50","full")
BPS = (0,100,500,1000,2500,5000,10000)
VECTORS = (
("00000000-0000-0000-0000-000000000000",1369),
("11111111-1111-1111-1111-111111111111",2241),
("22222222-2222-2222-2222-222222222222",7933),
("12345678-1234-5678-1234-567812345678",3203),
("ffffffff-ffff-ffff-ffff-ffffffffffff",7894),
("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",4431),
("01234567-89ab-cdef-0123-456789abcdef",986),
("deadbeef-dead-beef-dead-beefdeadbeef",164),
)

def _text(path): return (ROOT/path).read_text(encoding="utf-8")

class _Repo:
    workspace_id="personal"
    def __init__(self, existing=None): self.current=existing; self.creates=0; self.rollbacks=0
    def create(self,title,project_id=None):
        self.creates += 1
        self.current=SimpleNamespace(id=str(FIXED),project_id=project_id,workspace_id="personal")
        return self.current
    def get(self,cid): return self.current if self.current is not None and self.current.id==cid else None
    def project_exists(self,pid): return True
    def rollback(self): self.rollbacks += 1

def _conversation(repo=None):
    repository=repo or _Repo()
    return ConversationService(repository=repository,chat_service=object(),context_message_limit=20), repository

def _decision(enabled=True,eligible=True,stage="full",conversation_id=FIXED):
    return CognitiveRuntimeRolloutSelector.evaluate(
        enabled=enabled,cognitive_eligible=eligible,stage=stage,conversation_id=conversation_id
    )

def run_case(case):
    if 1 <= case <= 7:
        assert D144_STAGE_BPS[STAGES[case-1]] == BPS[case-1]
    elif case == 8:
        assert CognitiveRuntimeRolloutSettings.model_fields["oai_cognitive_runtime_rollout_stage"].default=="full"
    elif case == 9:
        assert set(get_args(CognitiveRuntimeRolloutStage)) == set(STAGES)
    elif case == 10:
        with pytest.raises(ValidationError):
            CognitiveRuntimeRolloutSettings(oai_cognitive_runtime_rollout_stage="invalid")
    elif case == 11:
        r=_decision(enabled=False); assert (r.disposition,r.reason_code)==("not_applicable","cognitive_runtime_disabled")
    elif case == 12:
        r=_decision(eligible=False); assert (r.disposition,r.reason_code)==("not_applicable","not_cognitive_eligible")
    elif case == 13:
        r=_decision(stage="canary_10",conversation_id=None); assert (r.disposition,r.reason_code)==("control","missing_conversation_identity")
    elif case == 14:
        r=_decision(stage="control_only"); assert (r.disposition,r.reason_code)==("control","rollout_control_only")
    elif case == 15:
        r=_decision(stage="full"); assert (r.disposition,r.reason_code)==("cognitive","rollout_full")
    elif 16 <= case <= 25:
        stage=STAGES[1+((case-16)//2)]; threshold=D144_STAGE_BPS[stage]
        bucket=threshold-1 if case%2==0 else threshold
        with patch.object(CognitiveRuntimeRolloutSelector,"bucket_for_conversation",return_value=bucket):
            r=_decision(stage=stage)
        assert r.disposition==("cognitive" if bucket<threshold else "control")
    elif 26 <= case <= 31:
        rs=(_decision(enabled=False),_decision(eligible=False),_decision(stage="invalid"),
            _decision(stage="canary_10",conversation_id=None),_decision(stage="control_only"),_decision(stage="full"))
        exp=("cognitive_runtime_disabled","not_cognitive_eligible","invalid_rollout_stage",
             "missing_conversation_identity","rollout_control_only","rollout_full")[case-26]
        assert rs[case-26].reason_code==exp
    elif 32 <= case <= 33:
        bucket=999 if case==32 else 1000
        with patch.object(CognitiveRuntimeRolloutSelector,"bucket_for_conversation",return_value=bucket):
            r=_decision(stage="canary_10")
        assert r.reason_code==("rollout_bucket_cognitive" if case==32 else "rollout_bucket_control")
    elif 34 <= case <= 41:
        value,expected=VECTORS[case-34]
        assert CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(value))==expected
    elif case == 42:
        s,_=_conversation(); assert s.reserve_cognitive_turn("hello",None,None,turn_id="turn-1").conversation_id==FIXED
    elif case == 43:
        s,r=_conversation(); a=s.reserve_cognitive_turn("hello",None,None,turn_id="turn-1"); b=s.reserve_cognitive_turn("hello",a.conversation_id,None,turn_id="turn-1"); assert b.conversation_id==a.conversation_id and r.creates==1
    elif case == 44:
        s,_=_conversation(); a=s.reserve_cognitive_turn("hello",None,PROJECT,turn_id="turn-1"); b=s.reserve_cognitive_turn("hello",a.conversation_id,None,turn_id="turn-1"); assert a.project_id==PROJECT and b.project_id==PROJECT
    elif 45 <= case <= 49:
        original=CommandRequest(request_id="turn-1",command="chat.message",arguments={"message":"hello","conversation_id":OTHER,"project_id":PROJECT})
        before=dict(original.arguments); binding=SimpleNamespace(conversation_id=FIXED,project_id=PROJECT)
        normalized=CommandOrchestrator._d144_server_bound_cognitive_command(command=original,message="hello",binding=binding)
        checks=(normalized.request_id==original.request_id,normalized.command==original.command,normalized.arguments["message"]=="hello",normalized.arguments["conversation_id"]==FIXED,normalized.arguments["project_id"] is None and dict(original.arguments)==before)
        assert checks[case-45]
    elif case == 50:
        s,_=_conversation(); assert type(s.reserve_cognitive_turn("hello",None,None,turn_id="turn-1").conversation_id) is UUID
    elif case == 51:
        existing=SimpleNamespace(id=str(OTHER),project_id=None,workspace_id="personal")
        s,r=_conversation(_Repo(existing)); b=s.reserve_cognitive_turn("hello",OTHER,None,turn_id="turn-1")
        assert b.conversation_id==OTHER and r.creates==0
    elif case == 52:
        s,_=_conversation(); assert s.reserve_cognitive_turn("hello",None,PROJECT,turn_id="turn-1").project_id==PROJECT
    elif case == 53:
        src=_text("backend/app/services/command_orchestrator.py"); assert src.index("reserve_cognitive_turn(")<src.index("CognitiveRuntimeRolloutSelector.evaluate(")
    elif case == 54:
        assert "self._cognitive_executive.process_chat(\n                        cognitive_command," in _text("backend/app/services/command_orchestrator.py")
    elif case == 55:
        src=_text("backend/app/services/cognitive_executive.py"); assert "reserve_cognitive_turn(" in src and "prebound_binding" not in src
    elif case == 56:
        src=_text("backend/app/services/command_orchestrator.py"); assert "binding.conversation_id" in src and "project_id=None" in src
    elif case == 57:
        src=_text("backend/app/services/command_orchestrator.py"); block=src[src.index("def _d144_control_turn"):src.index("def _observe_selection")]; assert "_cognitive_executive.process_chat" not in block
    elif case == 58:
        assert CognitiveRuntimeRolloutSettings.model_fields["oai_cognitive_runtime_rollout_stage"].default=="full"
    elif case == 59:
        s,r=_conversation(); a=s.reserve_cognitive_turn("hello",None,None,turn_id="turn-1"); s.reserve_cognitive_turn("hello",a.conversation_id,None,turn_id="turn-1"); assert r.creates==1
    elif 60 <= case <= 63:
        src=_text("backend/app/services/command_orchestrator.py")
        assert ("conversation_service.abort_cognitive_turn()","normalize_execution_authorization","self._ai_runtime.bind(","send_context_message(")[case-60] in src
    elif case == 64:
        src=_text("backend/app/services/command_orchestrator.py"); c=src.index("if self._cognitive_executive is not None:"); l=src.index('selected_lane="legacy"',c); assert "self._planner.plan(" not in src[c:l]
    elif case == 65:
        assert "except CognitiveExecutiveFailure as error:" in _text("backend/app/services/command_orchestrator.py")
    elif case == 66:
        src=_text("backend/app/services/command_orchestrator.py"); assert "for attempt" not in src and "while " not in src
    elif case == 67:
        assert _text("backend/app/services/command_orchestrator.py").count('selected_lane="legacy"')>=2
    elif case == 68:
        assert 'selected_lane="cognitive"' in _text("backend/app/services/command_orchestrator.py")
    elif case == 69:
        src=_text("backend/app/services/command_orchestrator.py"); block=src[src.index("def _d144_control_turn"):src.index("def _observe_selection")]; assert "_observe_cognitive_outcome" not in block
    elif case == 70:
        assert "_observe_cognitive_outcome(" in _text("backend/app/services/command_orchestrator.py")
    elif case == 71:
        assert "try_record_selection" in _text("backend/app/services/cognitive_runtime_observability.py")
    elif case == 72:
        assert "d144" not in _text("backend/app/contracts/cognitive_runtime_assurance.py").lower()
    elif case == 73:
        assert "cognitive_runtime_rollout" in _text("backend/app/schemas/diagnostics.py")
    elif case == 74:
        assert "rollout_bps=rollout_bps" in _text("backend/app/services/runtime_diagnostics.py")
    elif case == 75:
        r=_decision()
        for n in ("promotion_authority","rollback_authority","execution_authority","routing_authority","configuration_authority","automatic_stage_increase","automatic_stage_decrease"):
            assert getattr(r,n) is False
    elif case == 76:
        src=_text("backend/app/services/runtime_diagnostics.py"); assert "source_promotion_recommendation=advisory.recommendation" in src and "source_promotion_reason_code=advisory.reason_code" in src
    elif case == 77:
        src=_text("backend/app/services/runtime_diagnostics.py"); assert src.count("CognitiveRuntimePromotionGovernanceEvaluator.evaluate(")==1 and "advisory=promotion_advisory" in src
    elif case == 78:
        assert 'contract_version: Literal["1"] = "1"' in _text("backend/app/schemas/diagnostics.py")
    elif case == 79:
        assert set(ChatRequest.model_fields)=={"message","conversation_id","project_id","ai_mode"}
    elif case == 80:
        assert D144_REFERENCE_BASELINE=="9f6fa3557e3c9b91a3549c1175b8273c24fad20c"
        assert D144_ROLLOUT_BUCKET_COUNT==10000 and D144_SELECTION_SCOPE=="d140_cognitive_eligible_turns" and D144_SELECTION_STRATEGY=="sha256_server_bound_conversation_uuid_v1"
    else: raise AssertionError(case)

@pytest.mark.parametrize("case",range(1,81),ids=[f"F{i:02d}" for i in range(1,81)])
def test_d144_functional_matrix(case): run_case(case)
