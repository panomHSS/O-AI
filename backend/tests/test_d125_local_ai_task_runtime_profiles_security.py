from dataclasses import replace
import pytest
from app.contracts.ai import AIRequest
from app.adapters.local_ai import LocalAIAdapter, LocalAIResponseError
from app.contracts.local_ai_runtime import AUTHORIZED_LOCAL_AI_PROFILE_KEY as PROFILE, AUTHORIZED_LOCAL_AI_MODEL_KEY as MODEL
from app.services.ai_runtime import AIExecutionRejectedError
from app.services.execution_guard import execution_plan_digest
from tests.d125_profile_fixtures import profiles
from tests.test_local_ai_adapter import StubRuntimeClient
from tests import test_ai_runtime_e2e as e2e

@pytest.mark.parametrize('metadata', [{}, {PROFILE: 'local_ai.general_chat.v1'}, {MODEL: 'configured-model'}, {PROFILE: 'custom', MODEL: 'configured-model'}, {PROFILE: 'local_ai.general_chat.v1', MODEL: 'other'}])
def test_adapter_requires_exact_binding(metadata):
    runtime = StubRuntimeClient()
    with pytest.raises(LocalAIResponseError):
        LocalAIAdapter(runtime_client=runtime, enabled=True, profiles=profiles()).generate(AIRequest(content='hello', metadata=metadata))
    assert runtime.generate_calls == 0

@pytest.mark.parametrize('key', [PROFILE, MODEL])
def test_caller_reserved_metadata_rejected(key):
    fixture = e2e.UnifiedAIExecutionE2ETests()
    cloud, local, planner, guard, runtime, _ = fixture.build_lane(local_enabled=True)
    command = fixture.command('Use local AI for this command')
    authorization = guard.authorize(command, planner.plan(command))
    with pytest.raises(AIExecutionRejectedError, match='reserved'):
        runtime.bind(command, authorization).generate(AIRequest(content='hello', metadata={key: 'forged'}))
    assert not cloud.requests and (not local.requests)

@pytest.mark.parametrize('changes', [{'model_id': 'other'}, {'local_ai_profile_id': 'custom'}, {'extra': True}, {'local_ai_profile_id': None}])
def test_guard_rejects_tampered_profile_plan_and_digest_binds_parameters(changes):
    fixture = e2e.UnifiedAIExecutionE2ETests()
    _, _, planner, guard, _, _ = fixture.build_lane(local_enabled=True)
    command = fixture.command('Use local AI for this command')
    planning = planner.plan(command)
    plan = planning.plan
    step = replace(plan.steps[0], parameters={**plan.steps[0].parameters, **changes})
    tampered = replace(plan, steps=(step,))
    assert execution_plan_digest(tampered) != execution_plan_digest(plan)
    assert guard.authorize(command, replace(planning, plan=tampered)).status != 'authorized'

@pytest.mark.parametrize('local', [False, True])
def test_guard_requires_exact_parameter_set(local):
    fixture = e2e.UnifiedAIExecutionE2ETests()
    _, _, planner, guard, _, _ = fixture.build_lane(local_enabled=True)
    command = fixture.command('Use local AI for this command' if local else 'hello')
    planning = planner.plan(command)
    parameters = dict(planning.plan.steps[0].parameters)
    if local:
        parameters.pop('local_ai_profile_id')
    else:
        parameters['local_ai_profile_id'] = 'local_ai.general_chat.v1'
    step = replace(planning.plan.steps[0], parameters=parameters)
    assert guard.authorize(command, replace(planning, plan=replace(planning.plan, steps=(step,)))).status == 'rejected'

def test_runtime_rejects_binding_mutation_after_authorization():
    fixture = e2e.UnifiedAIExecutionE2ETests()
    cloud, local, planner, guard, runtime, _ = fixture.build_lane(local_enabled=True)
    command = fixture.command('Use local AI for this command')
    planning = planner.plan(command)
    authorization = guard.authorize(command, planning)
    planning.plan.steps[0].parameters['local_ai_profile_id'] = 'local_ai.software_engineering.v1'
    with pytest.raises(AIExecutionRejectedError):
        runtime.bind(command, authorization).generate(AIRequest(content='hello'))
    assert not local.requests and (not cloud.requests)
