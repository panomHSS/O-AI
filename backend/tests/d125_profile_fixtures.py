"""Explicit server-owned D125 configuration for migrated test lanes."""
from app.contracts.ai import AIRequest
from app.contracts.local_ai_profile import LocalAIProfile, GENERAL_CHAT_PROFILE_ID, SOFTWARE_ENGINEERING_PROFILE_ID
from app.contracts.local_ai_runtime import AUTHORIZED_LOCAL_AI_PROFILE_KEY, AUTHORIZED_LOCAL_AI_MODEL_KEY
from app.contracts.task_aware_ai_routing import AITaskKind
from app.services.local_ai_profile import LocalAIProfileResolver, LocalAIProfileAvailability

def profiles(model='configured-model', timeout=12.5, context=4096):
    return LocalAIProfileResolver(LocalAIProfile(GENERAL_CHAT_PROFILE_ID, AITaskKind.GENERAL_CHAT, model, timeout, context, None), LocalAIProfile(SOFTWARE_ENGINEERING_PROFILE_ID, AITaskKind.SOFTWARE_ENGINEERING, model, timeout, context, False))

class AvailableProfileRuntime:

    def is_runtime_available(self):
        return True

    def is_model_available(self, model):
        return model == 'configured-model'

def availability():
    return LocalAIProfileAvailability(AvailableProfileRuntime(), True)

def bound_request(content, metadata=None, model='configured-model'):
    return AIRequest(content=content, metadata={**(metadata or {}), AUTHORIZED_LOCAL_AI_PROFILE_KEY: GENERAL_CHAT_PROFILE_ID, AUTHORIZED_LOCAL_AI_MODEL_KEY: model})
