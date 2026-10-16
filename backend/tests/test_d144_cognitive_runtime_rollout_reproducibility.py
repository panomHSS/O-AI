from pathlib import Path
from uuid import UUID
import pytest
from app.contracts.cognitive_runtime_rollout import D144_STAGE_BPS
from app.schemas.diagnostics import CognitiveRuntimeRolloutDiagnostics
from app.services.cognitive_runtime_rollout import CognitiveRuntimeRolloutSelector

ROOT=Path(__file__).resolve().parents[2]
V=(("00000000-0000-0000-0000-000000000000",1369),("11111111-1111-1111-1111-111111111111",2241),("22222222-2222-2222-2222-222222222222",7933),("12345678-1234-5678-1234-567812345678",3203),("ffffffff-ffff-ffff-ffff-ffffffffffff",7894),("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",4431),("01234567-89ab-cdef-0123-456789abcdef",986),("deadbeef-dead-beef-dead-beefdeadbeef",164))
STAGES=("control_only","canary_1","canary_5","canary_10","canary_25","canary_50","full")
def t(p): return (ROOT/p).read_text(encoding="utf-8")
def ev(v,s): return CognitiveRuntimeRolloutSelector.evaluate(enabled=True,cognitive_eligible=True,stage=s,conversation_id=UUID(v))

def run_case(c):
    if 1<=c<=8:
        v,e=V[c-1]; assert CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v))==e
    elif 9<=c<=16:
        v,e=V[c-9]; assert CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v))==CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v))==e
    elif 17<=c<=24:
        v,e=V[c-17]; assert [CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v)) for _ in STAGES]==[e]*len(STAGES)
    elif 25<=c<=32:
        v,_=V[c-25]; flags=[ev(v,s).disposition=="cognitive" for s in STAGES]; assert flags==sorted(flags)
    elif 33<=c<=36:
        vals=[x[0] for x in V]; vals=vals if c%2 else list(reversed(vals))
        a={v:CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v)) for v in vals}; b={v:CognitiveRuntimeRolloutSelector.bucket_for_conversation(UUID(v)) for v in reversed(vals)}; assert a==b
    elif 37<=c<=40:
        a=CognitiveRuntimeRolloutSelector(); b=CognitiveRuntimeRolloutSelector(); assert vars(a)==vars(b)=={}
    elif c==41:
        u=UUID(V[-1][0]); assert CognitiveRuntimeRolloutSelector().bucket_for_conversation(u)==CognitiveRuntimeRolloutSelector().bucket_for_conversation(u)
    elif c==42:
        s=t("backend/app/services/cognitive_runtime_rollout.py"); assert "import time" not in s and "datetime" not in s
    elif c==43: assert "random" not in t("backend/app/services/cognitive_runtime_rollout.py")
    elif c==44: assert "hash(" not in t("backend/app/services/cognitive_runtime_rollout.py")
    elif c==45:
        kw=dict(stage="canary_10",rollout_bps=D144_STAGE_BPS["canary_10"],source_promotion_recommendation="eligible_for_promotion",source_promotion_reason_code="readiness_thresholds_satisfied")
        a=CognitiveRuntimeRolloutDiagnostics(**kw); b=CognitiveRuntimeRolloutDiagnostics(**kw); assert a.model_dump()==b.model_dump() and a.model_dump_json()==b.model_dump_json()
    elif c==46: assert t("backend/app/services/runtime_diagnostics.py").count("self._cognitive_runtime_assurance_snapshot()")==1
    elif c==47: assert t("backend/app/services/runtime_diagnostics.py").count("CognitiveRuntimeReadinessEvaluator.evaluate(")==1
    elif c==48:
        s=t("backend/app/services/runtime_diagnostics.py"); assert s.count("CognitiveRuntimePromotionGovernanceEvaluator.evaluate(")==1 and "advisory=promotion_advisory" in s
    else: raise AssertionError(c)

@pytest.mark.parametrize("case",range(1,49),ids=[f"R{i:02d}" for i in range(1,49)])
def test_d144_reproducibility_matrix(case): run_case(case)
