from dataclasses import FrozenInstanceError, replace
import pytest
from app.core.config import Settings
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.local_ai_profile import LocalAIProfileResolver
from app.adapters.local_ai import LocalAIAdapter, LocalAIResponseError
from app.contracts.local_ai_runtime import LOCAL_AI_GENERATION_OPTIONS_METADATA_KEY as OPTIONS
from tests.d125_profile_fixtures import profiles, bound_request
from tests.test_local_ai_adapter import StubRuntimeClient

def test_defaults_and_common_configuration_fallback():
    config = Settings(_env_file=None, oai_local_ai_model='common', oai_local_ai_timeout_seconds=22, oai_local_ai_context_length=1024)
    registry = LocalAIProfileResolver.from_settings(config)
    assert registry.general_chat.model_id == registry.software_engineering.model_id == 'common'
    assert registry.general_chat.timeout_seconds == registry.software_engineering.timeout_seconds == 22
    assert registry.general_chat.context_length == registry.software_engineering.context_length == 1024
    assert registry.general_chat.reasoning_enabled is None
    assert registry.software_engineering.reasoning_enabled is False
    with pytest.raises(FrozenInstanceError):
        registry.general_chat.model_id = 'other'

def test_task_overrides_are_independent():
    registry = LocalAIProfileResolver.from_settings(Settings(_env_file=None, oai_local_ai_general_chat_model='chat', oai_local_ai_general_chat_timeout_seconds=11, oai_local_ai_general_chat_context_length=512, oai_local_ai_general_chat_reasoning_enabled=True, oai_local_ai_software_engineering_model='code', oai_local_ai_software_engineering_timeout_seconds=33, oai_local_ai_software_engineering_context_length=8192))
    assert registry.resolve(AITaskKind.GENERAL_CHAT) == registry.general_chat
    assert registry.resolve(AITaskKind.SOFTWARE_ENGINEERING) == registry.software_engineering
    assert (registry.general_chat.model_id, registry.general_chat.timeout_seconds, registry.general_chat.context_length, registry.general_chat.reasoning_enabled) == ('chat', 11, 512, True)
    assert (registry.software_engineering.model_id, registry.software_engineering.timeout_seconds, registry.software_engineering.context_length, registry.software_engineering.reasoning_enabled) == ('code', 33, 8192, False)
    with pytest.raises(ValueError):
        registry.resolve('general_chat')

@pytest.mark.parametrize('field,value', [('model_id', ''), ('model_id', 'bad model'), ('timeout_seconds', 0), ('timeout_seconds', float('nan')), ('timeout_seconds', 601), ('context_length', 255), ('context_length', 32769), ('reasoning_enabled', 1), ('profile_id', 'custom')])
def test_profile_bounds(field, value):
    with pytest.raises(ValueError):
        replace(profiles().general_chat, **{field: value})

@pytest.mark.parametrize('field,value', [('model', ''), ('timeout_seconds', 0), ('timeout_seconds', True), ('context_length', 1), ('reasoning_enabled', 'yes'), ('reasoning_enabled', 1)])
def test_settings_reject_invalid_overrides(field, value):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **{'oai_local_ai_general_chat_' + field: value})

@pytest.mark.parametrize('policy', [None, False, True])
@pytest.mark.parametrize('requested', [None, False, True])
def test_reasoning_matrix_and_exact_runtime_configuration(policy, requested):
    registry = profiles('exact-model', 17, 2048)
    registry = replace(registry, general_chat=replace(registry.general_chat, reasoning_enabled=policy))
    runtime = StubRuntimeClient()
    adapter = LocalAIAdapter(runtime_client=runtime, enabled=True, profiles=registry)
    metadata = {} if requested is None else {OPTIONS: {'reasoning_enabled': requested}}
    request = bound_request('hello', metadata, model='exact-model')
    if policy is not None and requested is not None and (requested != policy):
        with pytest.raises(LocalAIResponseError):
            adapter.generate(request)
        assert runtime.generate_calls == 0
    else:
        adapter.generate(request)
        assert runtime.generate_calls == 1
        assert runtime.last_generate_kwargs == dict(model='exact-model', prompt='hello', timeout_seconds=17, context_length=2048, response_schema=None, reasoning_enabled=policy if policy is not None else requested, temperature=None)
