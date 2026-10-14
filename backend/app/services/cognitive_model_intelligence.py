"""D135 deterministic Model Intelligence capability-knowledge projection."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Sequence

from app.contracts.ai_discovery import (
    AI_CAPABILITY_TEXT_GENERATION,
    AIAdapterDiscovery,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.cognitive_input_semantics import CognitiveTaskDescription
from app.contracts.cognitive_model_intelligence import (
    D135_DISCOVERY_CAPABILITY_MAX_COUNT,
    D135_DISCOVERY_INPUT_DIGEST_VERSION,
    D135_DISCOVERY_MODEL_MAX_COUNT,
    D135_EVALUATION_EVIDENCE_MAX_COUNT,
    D135_MODEL_CAPABILITY_ARTIFACT_TYPE,
    D135_MODEL_CAPABILITY_CONTRACT_VERSION,
    D135_PROFILE_INPUT_DIGEST_VERSION,
    CognitiveModelCapabilityKnowledgeArtifact,
    ModelCapabilityEvaluationEvidence,
    ModelCapabilitySupport,
    _derive_conflict_codes,
    _derive_limitation_codes,
    _evaluation_source_digests,
    _knowledge_fingerprint,
)
from app.contracts.local_ai_profile import LocalAIProfile, valid_model_id


_CONTRACT_VIOLATION = "cognitive_model_intelligence_contract_violation"


def _reject() -> None:
    raise ValueError(_CONTRACT_VIOLATION)


def _safe_identifier(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        _reject()
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        _reject()
    if len(encoded) > COGNITIVE_ID_MAX_BYTES or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        _reject()
    return value


def _canonical_json_sha256(payload: object) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _discovery_input_digest(discovery: AIAdapterDiscovery) -> str:
    return _canonical_json_sha256(
        {
            "digest_version": D135_DISCOVERY_INPUT_DIGEST_VERSION,
            "adapter_id": discovery.adapter_id,
            "status": discovery.status,
            "configured_model_id": discovery.configured_model_id,
            "capability_ids": list(discovery.capability_ids),
            "models": [
                {
                    "model_id": model.model_id,
                    "capability_ids": list(model.capability_ids),
                }
                for model in discovery.models
            ],
            "reason_code": discovery.reason_code,
        }
    )


def _profile_input_digest(profile: LocalAIProfile) -> str:
    return _canonical_json_sha256(
        {
            "digest_version": D135_PROFILE_INPUT_DIGEST_VERSION,
            "profile_id": profile.profile_id,
            "task_kind": profile.task_kind.value,
            "model_id": profile.model_id,
            "context_length": profile.context_length,
            "reasoning_enabled": profile.reasoning_enabled,
        }
    )


def _aggregate_support(
    evidence: tuple[ModelCapabilityEvaluationEvidence, ...],
    attribute: str,
) -> ModelCapabilitySupport:
    values = {
        value
        for item in evidence
        if (value := getattr(item, attribute)) is not None
    }
    if not values:
        return "unknown"
    if len(values) == 1:
        return next(iter(values))  # type: ignore[return-value]
    return "conflicted"


def _validate_envelope(
    envelope: object,
    task: CognitiveTaskDescription,
) -> CognitiveArtifactEnvelope:
    if not isinstance(envelope, CognitiveArtifactEnvelope):
        _reject()
    if (
        envelope.producer_organ is not CognitiveOrgan.MODEL_INTELLIGENCE
        or envelope.artifact_type != D135_MODEL_CAPABILITY_ARTIFACT_TYPE
        or envelope.contract_version != D135_MODEL_CAPABILITY_CONTRACT_VERSION
        or envelope.status is not CognitiveOrganStatus.READY
        or envelope.model_binding_reference is not None
        or envelope.turn_id != task.envelope.turn_id
        or envelope.workspace_id is not task.envelope.workspace_id
        or envelope.context_snapshot_digest != task.envelope.context_snapshot_digest
    ):
        _reject()
    return envelope


def _validate_discovery(discovery: object) -> AIAdapterDiscovery:
    if not isinstance(discovery, AIAdapterDiscovery):
        _reject()

    _safe_identifier(discovery.adapter_id)
    _safe_identifier(discovery.reason_code)
    if discovery.configured_model_id is not None:
        _safe_identifier(discovery.configured_model_id)

    if len(discovery.models) > D135_DISCOVERY_MODEL_MAX_COUNT:
        _reject()
    if len(discovery.capability_ids) > D135_DISCOVERY_CAPABILITY_MAX_COUNT:
        _reject()

    adapter_capabilities = set(discovery.capability_ids)
    for capability_id in discovery.capability_ids:
        _safe_identifier(capability_id)

    for model in discovery.models:
        _safe_identifier(model.model_id)
        if len(model.capability_ids) > D135_DISCOVERY_CAPABILITY_MAX_COUNT:
            _reject()
        for capability_id in model.capability_ids:
            _safe_identifier(capability_id)
        if not set(model.capability_ids).issubset(adapter_capabilities):
            _reject()

    return discovery


def _canonical_evidence(
    value: object,
    *,
    adapter_id: str,
    model_id: str,
    task_kind: object,
) -> tuple[ModelCapabilityEvaluationEvidence, ...]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) > D135_EVALUATION_EVIDENCE_MAX_COUNT
    ):
        _reject()

    evidence = tuple(value)
    if not all(isinstance(item, ModelCapabilityEvaluationEvidence) for item in evidence):
        _reject()

    evidence_ids = tuple(item.evidence_id for item in evidence)
    if len(set(evidence_ids)) != len(evidence_ids):
        _reject()

    for item in evidence:
        if (
            item.adapter_id != adapter_id
            or item.model_id != model_id
            or item.task_kind is not task_kind
        ):
            _reject()

    return tuple(sorted(evidence, key=lambda item: item.evidence_id))


class CognitiveModelIntelligenceCoordinator:
    """Form one bounded read-only D135 capability-knowledge artifact."""

    def form_knowledge(
        self,
        envelope: CognitiveArtifactEnvelope,
        task: CognitiveTaskDescription,
        discovery: AIAdapterDiscovery,
        *,
        target_model_id: str,
        local_profile: LocalAIProfile | None = None,
        evaluation_evidence: Sequence[ModelCapabilityEvaluationEvidence] = (),
    ) -> CognitiveModelCapabilityKnowledgeArtifact:
        try:
            if not isinstance(task, CognitiveTaskDescription):
                _reject()
            envelope = _validate_envelope(envelope, task)
            discovery = _validate_discovery(discovery)
            target_model_id = _safe_identifier(target_model_id)

            if local_profile is not None:
                if not isinstance(local_profile, LocalAIProfile):
                    _reject()
                if (
                    discovery.adapter_id != LOCAL_AI_ADAPTER_ID
                    or local_profile.task_kind is not task.authoritative_ai_task_kind
                    or local_profile.model_id != target_model_id
                    or not valid_model_id(local_profile.model_id)
                ):
                    _reject()
                _safe_identifier(local_profile.profile_id)
            elif discovery.adapter_id != LOCAL_AI_ADAPTER_ID:
                local_profile = None

            evidence = _canonical_evidence(
                evaluation_evidence,
                adapter_id=discovery.adapter_id,
                model_id=target_model_id,
                task_kind=task.authoritative_ai_task_kind,
            )

            target_descriptor = next(
                (
                    model
                    for model in discovery.models
                    if model.model_id == target_model_id
                ),
                None,
            )
            model_discovered = target_descriptor is not None
            if target_descriptor is None:
                text_generation_support: ModelCapabilitySupport = "unknown"
            elif AI_CAPABILITY_TEXT_GENERATION in target_descriptor.capability_ids:
                text_generation_support = "supported"
            else:
                text_generation_support = "unsupported"

            if discovery.adapter_id == LOCAL_AI_ADAPTER_ID:
                locality = "local"
            elif discovery.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID:
                locality = "cloud"
            else:
                locality = "unknown"

            if local_profile is None:
                profile_id = None
                configured_context_length = None
                configured_reasoning_policy = None
                profile_digest = None
            else:
                profile_id = local_profile.profile_id
                configured_context_length = local_profile.context_length
                configured_reasoning_policy = local_profile.reasoning_enabled
                profile_digest = _profile_input_digest(local_profile)

            task_fit = _aggregate_support(evidence, "task_fit")
            reasoning_support = _aggregate_support(evidence, "reasoning_support")
            structured_output_support = _aggregate_support(
                evidence,
                "structured_output_support",
            )

            context_values = tuple(
                item.verified_context_tokens
                for item in evidence
                if item.verified_context_tokens is not None
            )
            max_verified_context_tokens = (
                max(context_values) if context_values else None
            )
            latency_observations_ms = tuple(
                item.observed_latency_ms
                for item in evidence
                if item.observed_latency_ms is not None
            )

            limitation_codes = _derive_limitation_codes(
                task_fit=task_fit,
                reasoning_support=reasoning_support,
                structured_output_support=structured_output_support,
            )
            conflict_codes = _derive_conflict_codes(
                task_fit=task_fit,
                reasoning_support=reasoning_support,
                structured_output_support=structured_output_support,
            )

            discovery_digest = _discovery_input_digest(discovery)
            evaluation_digests = _evaluation_source_digests(evidence)
            expected_refs = (
                discovery_digest,
                *((profile_digest,) if profile_digest is not None else ()),
                *evaluation_digests,
            )
            if envelope.input_reference_digests != expected_refs:
                _reject()

            fingerprint = _knowledge_fingerprint(
                task_kind=task.authoritative_ai_task_kind,
                adapter_id=discovery.adapter_id,
                model_id=target_model_id,
                profile_id=profile_id,
                adapter_discovery_status=discovery.status,
                discovery_reason_code=discovery.reason_code,
                model_discovered=model_discovered,
                text_generation_support=text_generation_support,
                locality=locality,
                configured_context_length=configured_context_length,
                configured_reasoning_policy=configured_reasoning_policy,
                task_fit=task_fit,
                reasoning_support=reasoning_support,
                structured_output_support=structured_output_support,
                max_verified_context_tokens=max_verified_context_tokens,
                latency_observations_ms=latency_observations_ms,
                limitation_codes=limitation_codes,
                evidence_conflict_codes=conflict_codes,
                evaluation_evidence=evidence,
                discovery_input_digest=discovery_digest,
                profile_input_digest=profile_digest,
                evaluation_source_digests=evaluation_digests,
            )

            return CognitiveModelCapabilityKnowledgeArtifact(
                envelope=envelope,
                task_kind=task.authoritative_ai_task_kind,
                adapter_id=discovery.adapter_id,
                model_id=target_model_id,
                profile_id=profile_id,
                adapter_discovery_status=discovery.status,
                discovery_reason_code=discovery.reason_code,
                model_discovered=model_discovered,
                text_generation_support=text_generation_support,
                locality=locality,
                configured_context_length=configured_context_length,
                configured_reasoning_policy=configured_reasoning_policy,
                task_fit=task_fit,
                reasoning_support=reasoning_support,
                structured_output_support=structured_output_support,
                max_verified_context_tokens=max_verified_context_tokens,
                latency_observations_ms=latency_observations_ms,
                limitation_codes=limitation_codes,
                evidence_conflict_codes=conflict_codes,
                evaluation_evidence=evidence,
                knowledge_fingerprint=fingerprint,
            )
        except ValueError as error:
            if str(error) == _CONTRACT_VIOLATION:
                raise
            raise ValueError(_CONTRACT_VIOLATION) from None
        except (TypeError, UnicodeError):
            raise ValueError(_CONTRACT_VIOLATION) from None


__all__ = ["CognitiveModelIntelligenceCoordinator"]
