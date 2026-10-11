import pytest
from app.contracts.ai import AIRequest
from app.contracts.task_aware_ai_routing import AITaskKind
from app.contracts.local_ai_runtime import AUTHORIZED_LOCAL_AI_PROFILE_KEY as PROFILE, AUTHORIZED_LOCAL_AI_MODEL_KEY as MODEL
from app.services.ai_runtime import AIExecutionRejectedError
from tests import test_ai_runtime_e2e as e2e
from tests.test_d111_ai_brain_runtime_integration import build_lane
from app.contracts.workspace_ai_policy import WorkspaceAIRouteMode
from dataclasses import replace
from unittest.mock import Mock
from app.adapters.local_ai import LocalAIAdapter, LocalAIUnavailableError
from app.contracts.local_ai_runtime import LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY as OPTIONS
from app.services.adapter_registry import AdapterRegistry
from app.services.ai_provider_routing import AIProviderRoutingPolicy
from app.services.ai_router import AIRouter
from app.services.ai_runtime import AIRuntime
from app.services.command_decision_engine import CommandDecisionEngine
from app.services.execution_guard import ExecutionGuard
from app.services.execution_planner import ExecutionPlanner
from app.services.local_ai_profile import LocalAIProfileAvailability
from app.contracts.workspace import WorkspaceId
from app.contracts.workspace_ai_policy import WorkspaceAIRoutingPolicy
from app.telemetry.system_metrics import SystemMetricsProvider
from tests.d125_profile_fixtures import profiles
from tests.test_local_ai_adapter import StubRuntimeClient
from app.services.engineering_ai_draft import EngineeringAIDraftService, EngineeringAIDraftWorkflowService
from app.services.engineering_repository_reader import EngineeringRepositoryReader
from app.services.engineering_investigation_workflow import EngineeringInvestigationWorkflowService
from app.services.builtin_skills import build_builtin_skill_catalog, ENGINEERING_AI_DRAFT_SKILL_ID
from app.services.skill_invocation_bridge import SkillInvocationBridge
from tests import test_engineering_ai_draft_service as draft_fixture
from tests import test_d113_engineering_investigation_runtime as investigation_fixture

@pytest.mark.parametrize('task,profile', [(AITaskKind.GENERAL_CHAT, 'local_ai.general_chat.v1'), (AITaskKind.SOFTWARE_ENGINEERING, 'local_ai.software_engineering.v1')])
def test_authorized_task_binding_injected_without_mutating_caller(task, profile):
    fixture = e2e.UnifiedAIExecutionE2ETests()
    cloud, local, _, planner, guard, runtime = build_lane(workspace_mode=WorkspaceAIRouteMode.LOCAL_ONLY)
    command = fixture.command('Use local AI for this command')
    planning = planner.plan(command, task_kind=task)
    assert planning.plan.steps[0].parameters == {'capability_id': 'text_generation', 'model_id': 'configured-model', 'local_ai_profile_id': profile}
    proxy = runtime.bind(command, guard.authorize(command, planning))
    request = AIRequest(content='hello', metadata={'context': 'untrusted model override'})
    proxy.generate(request)
    assert request.metadata == {'context': 'untrusted model override'}
    assert local.requests[0].metadata == {'context': 'untrusted model override', PROFILE: profile, MODEL: 'configured-model'}
    with pytest.raises(AIExecutionRejectedError, match='replayed'):
        proxy.generate(request)
    assert len(local.requests) == 1 and (not cloud.requests)

def test_cloud_plan_preserves_two_parameters_and_metadata():
    fixture = e2e.UnifiedAIExecutionE2ETests()
    cloud, local, planner, guard, runtime, _ = fixture.build_lane(local_enabled=True)
    command = fixture.command('hello')
    planning = planner.plan(command)
    assert set(planning.plan.steps[0].parameters) == {'capability_id', 'model_id'}
    request = AIRequest(content='hello')
    runtime.bind(command, guard.authorize(command, planning)).generate(request)
    assert cloud.requests == [request] and (not local.requests)

def real_lane(available=True):
    config = profiles('chat-model', 11, 1024)
    config = replace(config, software_engineering=replace(config.software_engineering, model_id='code-model', timeout_seconds=29, context_length=8192))
    provider = StubRuntimeClient(model_available=available)
    provider.is_model_available = Mock(side_effect=lambda model: available and model in {'chat-model', 'code-model'})
    telemetry = Mock()
    local = LocalAIAdapter(runtime_client=provider, enabled=True, profiles=config, telemetry_provider=telemetry)
    cloud = e2e.RecordingAdapter('chatgpt.default')
    registry = AdapterRegistry((local, cloud))
    router = AIRouter(registry=registry, policy=AIProviderRoutingPolicy(default_adapter_id='chatgpt.default', enabled_adapter_ids=frozenset({'local_ai.default', 'chatgpt.default'})), workspace_policy=WorkspaceAIRoutingPolicy(workspace_id=WorkspaceId.PERSONAL, mode=WorkspaceAIRouteMode.LOCAL_ONLY))
    discovery = Mock()
    discovery.discover.return_value = type('Discovery', (), dict(status='available', capability_ids=('text_generation',), configured_model_id='wrong-discovery-model'))()
    planner = ExecutionPlanner(registry=registry, decision_engine=CommandDecisionEngine(), ai_router=router, ai_discovery=discovery, permission_policy=object(), local_ai_profiles=config, local_ai_availability=LocalAIProfileAvailability(provider, True))
    guard = ExecutionGuard(registry=registry, permission_policy=object(), local_ai_profiles=config)
    return (provider, telemetry, cloud, discovery, planner, guard, AIRuntime(registry=registry))

@pytest.mark.parametrize('task,model,timeout,context,reasoning', [(AITaskKind.GENERAL_CHAT, 'chat-model', 11, 1024, None), (AITaskKind.SOFTWARE_ENGINEERING, 'code-model', 29, 8192, False)])
@pytest.mark.parametrize('structured', [False, True])
def test_actual_adapter_uses_authorized_task_profile(task, model, timeout, context, reasoning, structured):
    provider, telemetry, cloud, discovery, planner, guard, runtime = real_lane()
    command = e2e.UnifiedAIExecutionE2ETests.command('Use local AI for this command')
    plan = planner.plan(command, task_kind=task)
    assert plan.plan.steps[0].parameters['model_id'] == model
    schema = {'type': 'object', 'properties': {'summary': {'type': 'string'}}}
    metadata = {OPTIONS: dict(response_schema=schema, reasoning_enabled=False, temperature=0.0)} if structured else {}
    runtime.bind(command, guard.authorize(command, plan)).generate(AIRequest(content='hello', metadata=metadata))
    assert provider.last_generate_kwargs == dict(model=model, prompt='hello', timeout_seconds=timeout, context_length=context, response_schema=schema if structured else None, reasoning_enabled=False if structured else reasoning, temperature=0.0 if structured else None)
    assert provider.generate_calls == 1 and (not cloud.requests)
    assert provider.is_model_available.call_args_list[0].args == (model,)
    telemetry.start_inference_session.assert_called_once_with(model=model)
    discovery.discover.assert_not_called()

@pytest.mark.parametrize('task', list(AITaskKind))
def test_missing_exact_model_has_no_discovery_or_cloud_fallback(task):
    provider, _, cloud, discovery, planner, _, _ = real_lane(available=False)
    command = e2e.UnifiedAIExecutionE2ETests.command('Use local AI for this command')
    assert planner.plan(command, task_kind=task).status == 'unavailable'
    assert provider.generate_calls == 0 and (not cloud.requests)
    discovery.discover.assert_not_called()

def test_model_disappearing_after_authorization_fails_without_generation():
    provider, _, cloud, _, planner, guard, runtime = real_lane()
    command = e2e.UnifiedAIExecutionE2ETests.command('Use local AI for this command')
    authorization = guard.authorize(command, planner.plan(command))
    provider.is_model_available.side_effect = lambda model: False
    with pytest.raises(LocalAIUnavailableError):
        runtime.bind(command, authorization).generate(AIRequest(content='hello'))
    assert provider.generate_calls == 0 and (not cloud.requests)

def test_telemetry_samples_actual_model_without_changing_configured_default():
    provider = Mock()
    provider.is_runtime_available.return_value = True
    provider.is_model_loaded.side_effect = lambda model: model == 'code-model'
    metrics = SystemMetricsProvider(runtime_client=provider, model='common-model')
    assert metrics._read_runtime_status('code-model') == ('ONLINE', 'LOADED')
    assert metrics._read_runtime_status('chat-model') == ('ONLINE', 'IDLE')
    assert metrics._read_runtime_status() == ('ONLINE', 'IDLE')
    assert [call.args[0] for call in provider.is_model_loaded.call_args_list] == ['code-model', 'chat-model', 'common-model']

@pytest.mark.parametrize('via_skill', [False, True])
def test_d110_and_d121_d123_skill_path_inherit_engineering_policy(tmp_path, via_skill):
    provider, _, cloud, _, planner, guard, runtime = real_lane()
    service = EngineeringAIDraftService(repository_reader=EngineeringRepositoryReader(tmp_path), execution_planner=planner, execution_guard=guard, ai_runtime=runtime)
    request = draft_fixture.req('new.txt')
    if via_skill:
        workflow = EngineeringAIDraftWorkflowService(workspace_scope=draft_fixture.PERSONAL, conversation_repository=Mock(), draft_service=service)
        bridge = SkillInvocationBridge(catalog=build_builtin_skill_catalog(), engineering_ai_draft_workflow=workflow, engineering_investigation_workflow=object.__new__(EngineeringInvestigationWorkflowService))
        result = bridge.invoke(skill_id=ENGINEERING_AI_DRAFT_SKILL_ID, request=request)
    else:
        result = service.draft(workspace_scope=draft_fixture.PERSONAL, request=request)
    assert result.draft_content == 'local reply'
    assert provider.last_generate_kwargs['model'] == 'code-model'
    assert provider.last_generate_kwargs['reasoning_enabled'] is False
    assert provider.generate_calls == 1 and (not cloud.requests)
    assert not (tmp_path / 'new.txt').exists()

def test_d113_service_emits_engineering_binding_and_preserves_options(tmp_path):
    service, local, cloud = investigation_fixture.build_service(tmp_path)
    service.investigate(workspace_scope=investigation_fixture.PERSONAL, request=investigation_fixture.request())
    metadata = local.requests[0].metadata
    assert metadata[PROFILE] == 'local_ai.software_engineering.v1'
    assert metadata[MODEL] == 'configured-model'
    assert metadata[OPTIONS]['reasoning_enabled'] is False
    assert metadata[OPTIONS]['temperature'] == 0.0
    assert metadata[OPTIONS]['response_schema']['additionalProperties'] is False
    assert len(local.requests) == 1 and (not cloud.requests)
