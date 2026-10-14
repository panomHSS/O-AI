"""D135 immutable Model Intelligence capability-knowledge contracts.

These contracts describe bounded, read-only capability/evaluation knowledge.
They grant no routing, model/profile selection, authorization, persistence, or
execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.contracts.ai_discovery import (
    AI_DISCOVERY_STATUSES,
    AIDiscoveryStatus,
)
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.cognitive_brain import (
    COGNITIVE_ID_MAX_BYTES,
    CognitiveArtifactEnvelope,
    CognitiveOrgan,
    CognitiveOrganStatus,
)
from app.contracts.local_ai_profile import (
    GENERAL_CHAT_PROFILE_ID,
    SOFTWARE_ENGINEERING_PROFILE_ID,
    valid_model_id,
)
from app.contracts.task_aware_ai_routing import AITaskKind


D135_MODEL_CAPABILITY_ARTIFACT_TYPE = "cognitive.model_capability_knowledge"
D135_MODEL_CAPABILITY_CONTRACT_VERSION = "o-ai.cognitive-model-capability-knowledge.v1"
D135_MODEL_CAPABILITY_FINGERPRINT_VERSION = "o-ai.cognitive-model-capability-fingerprint.v1"

D135_DISCOVERY_INPUT_DIGEST_VERSION = "o-ai.d135.discovery-input.v1"
D135_PROFILE_INPUT_DIGEST_VERSION = "o-ai.d135.profile-input.v1"

D135_EVALUATION_SOURCE_KIND = "server_evaluation"

D135_EVALUATION_EVIDENCE_MAX_COUNT = 32
D135_DISCOVERY_MODEL_MAX_COUNT = 256
D135_DISCOVERY_CAPABILITY_MAX_COUNT = 32

D135_VERIFIED_CONTEXT_TOKENS_MAX = 10_000_000
D135_OBSERVED_LATENCY_MS_MAX = 3_600_000


ModelCapabilitySupport: TypeAlias = Literal[
    "supported",
    "limited",
    "unsupported",
    "unknown",
    "conflicted",
]

ModelCapabilityEvaluationSupport: TypeAlias = Literal[
    "supported",
    "limited",
    "unsupported",
]

ModelLocality: TypeAlias = Literal[
    "local",
    "cloud",
    "unknown",
]

ModelCapabilityLimitationCode: TypeAlias = Literal[
    "task_fit_limited",
    "task_fit_unsupported",
    "reasoning_limited",
    "reasoning_unsupported",
    "structured_output_limited",
    "structured_output_unsupported",
]

ModelCapabilityConflictCode: TypeAlias = Literal[
    "task_fit_conflict",
    "reasoning_support_conflict",
    "structured_output_support_conflict",
]


_MODEL_CAPABILITY_SUPPORTS = frozenset(
    {"supported", "limited", "unsupported", "unknown", "conflicted"}
)
_MODEL_CAPABILITY_EVALUATION_SUPPORTS = frozenset(
    {"supported", "limited", "unsupported"}
)
_MODEL_LOCALITIES = frozenset({"local", "cloud", "unknown"})
_LIMITATION_CODES = (
    "task_fit_limited",
    "task_fit_unsupported",
    "reasoning_limited",
    "reasoning_unsupported",
    "structured_output_limited",
    "structured_output_unsupported",
)
_CONFLICT_CODES = (
    "task_fit_conflict",
    "reasoning_support_conflict",
    "structured_output_support_conflict",
)
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _validate_identifier(value: object, *, code: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(code) from None
    if len(encoded) > COGNITIVE_ID_MAX_BYTES or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(code)
    return value


def _validate_optional_identifier(value: object, *, code: str) -> str | None:
    if value is None:
        return None
    return _validate_identifier(value, code=code)


def _validate_digest(value: object, *, code: str) -> str:
    if type(value) is not str or _SHA256_HEX.fullmatch(value) is None:
        raise ValueError(code)
    return value


def _validate_support(value: object, *, code: str) -> ModelCapabilitySupport:
    if type(value) is not str or value not in _MODEL_CAPABILITY_SUPPORTS:
        raise ValueError(code)
    return value  # type: ignore[return-value]


def _validate_evaluation_support(
    value: object,
    *,
    code: str,
) -> ModelCapabilityEvaluationSupport | None:
    if value is None:
        return None
    if type(value) is not str or value not in _MODEL_CAPABILITY_EVALUATION_SUPPORTS:
        raise ValueError(code)
    return value  # type: ignore[return-value]


def _validate_positive_int(
    value: object,
    *,
    maximum: int,
    code: str,
) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(code)
    return value


def _canonical_json_sha256(payload: object) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _evaluation_payload(
    evidence: "ModelCapabilityEvaluationEvidence",
) -> dict[str, object]:
    return {
        "evidence_id": evidence.evidence_id,
        "source_kind": evidence.source_kind,
        "source_digest": evidence.source_digest,
        "adapter_id": evidence.adapter_id,
        "model_id": evidence.model_id,
        "task_kind": evidence.task_kind.value,
        "task_fit": evidence.task_fit,
        "reasoning_support": evidence.reasoning_support,
        "structured_output_support": evidence.structured_output_support,
        "verified_context_tokens": evidence.verified_context_tokens,
        "observed_latency_ms": evidence.observed_latency_ms,
    }


def _aggregate_support(
    evidence: tuple["ModelCapabilityEvaluationEvidence", ...],
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


def _derive_limitation_codes(
    *,
    task_fit: ModelCapabilitySupport,
    reasoning_support: ModelCapabilitySupport,
    structured_output_support: ModelCapabilitySupport,
) -> tuple[ModelCapabilityLimitationCode, ...]:
    result: list[ModelCapabilityLimitationCode] = []
    mappings = (
        ("task_fit", task_fit, "task_fit_limited", "task_fit_unsupported"),
        (
            "reasoning_support",
            reasoning_support,
            "reasoning_limited",
            "reasoning_unsupported",
        ),
        (
            "structured_output_support",
            structured_output_support,
            "structured_output_limited",
            "structured_output_unsupported",
        ),
    )
    for _, value, limited_code, unsupported_code in mappings:
        if value == "limited":
            result.append(limited_code)  # type: ignore[arg-type]
        elif value == "unsupported":
            result.append(unsupported_code)  # type: ignore[arg-type]
    return tuple(result)


def _derive_conflict_codes(
    *,
    task_fit: ModelCapabilitySupport,
    reasoning_support: ModelCapabilitySupport,
    structured_output_support: ModelCapabilitySupport,
) -> tuple[ModelCapabilityConflictCode, ...]:
    result: list[ModelCapabilityConflictCode] = []
    if task_fit == "conflicted":
        result.append("task_fit_conflict")
    if reasoning_support == "conflicted":
        result.append("reasoning_support_conflict")
    if structured_output_support == "conflicted":
        result.append("structured_output_support_conflict")
    return tuple(result)


def _evaluation_source_digests(
    evidence: tuple["ModelCapabilityEvaluationEvidence", ...],
) -> tuple[str, ...]:
    return tuple(sorted({item.source_digest for item in evidence}))


def _profile_input_digest_from_artifact(
    *,
    profile_id: str,
    task_kind: AITaskKind,
    model_id: str,
    configured_context_length: int,
    configured_reasoning_policy: bool | None,
) -> str:
    return _canonical_json_sha256(
        {
            "digest_version": D135_PROFILE_INPUT_DIGEST_VERSION,
            "profile_id": profile_id,
            "task_kind": task_kind.value,
            "model_id": model_id,
            "context_length": configured_context_length,
            "reasoning_enabled": configured_reasoning_policy,
        }
    )


def _knowledge_fingerprint(
    *,
    task_kind: AITaskKind,
    adapter_id: str,
    model_id: str,
    profile_id: str | None,
    adapter_discovery_status: AIDiscoveryStatus,
    discovery_reason_code: str,
    model_discovered: bool,
    text_generation_support: ModelCapabilitySupport,
    locality: ModelLocality,
    configured_context_length: int | None,
    configured_reasoning_policy: bool | None,
    task_fit: ModelCapabilitySupport,
    reasoning_support: ModelCapabilitySupport,
    structured_output_support: ModelCapabilitySupport,
    max_verified_context_tokens: int | None,
    latency_observations_ms: tuple[int, ...],
    limitation_codes: tuple[ModelCapabilityLimitationCode, ...],
    evidence_conflict_codes: tuple[ModelCapabilityConflictCode, ...],
    evaluation_evidence: tuple["ModelCapabilityEvaluationEvidence", ...],
    discovery_input_digest: str,
    profile_input_digest: str | None,
    evaluation_source_digests: tuple[str, ...],
) -> str:
    return _canonical_json_sha256(
        {
            "fingerprint_version": D135_MODEL_CAPABILITY_FINGERPRINT_VERSION,
            "task_kind": task_kind.value,
            "adapter_id": adapter_id,
            "model_id": model_id,
            "profile_id": profile_id,
            "adapter_discovery_status": adapter_discovery_status,
            "discovery_reason_code": discovery_reason_code,
            "model_discovered": model_discovered,
            "text_generation_support": text_generation_support,
            "locality": locality,
            "configured_context_length": configured_context_length,
            "configured_reasoning_policy": configured_reasoning_policy,
            "task_fit": task_fit,
            "reasoning_support": reasoning_support,
            "structured_output_support": structured_output_support,
            "max_verified_context_tokens": max_verified_context_tokens,
            "latency_observations_ms": list(latency_observations_ms),
            "limitation_codes": list(limitation_codes),
            "evidence_conflict_codes": list(evidence_conflict_codes),
            "evaluation_evidence": [
                _evaluation_payload(item) for item in evaluation_evidence
            ],
            "discovery_input_digest": discovery_input_digest,
            "profile_input_digest": profile_input_digest,
            "evaluation_source_digests": list(evaluation_source_digests),
        }
    )


@dataclass(frozen=True, slots=True)
class ModelCapabilityEvaluationEvidence:
    evidence_id: str
    source_kind: Literal["server_evaluation"]
    source_digest: str
    adapter_id: str
    model_id: str
    task_kind: AITaskKind
    task_fit: ModelCapabilityEvaluationSupport | None = None
    reasoning_support: ModelCapabilityEvaluationSupport | None = None
    structured_output_support: ModelCapabilityEvaluationSupport | None = None
    verified_context_tokens: int | None = None
    observed_latency_ms: int | None = None

    def __post_init__(self) -> None:
        _validate_identifier(
            self.evidence_id,
            code="cognitive_model_capability_evidence_id_invalid",
        )
        if self.source_kind != D135_EVALUATION_SOURCE_KIND:
            raise ValueError("cognitive_model_capability_evidence_source_kind_invalid")
        _validate_digest(
            self.source_digest,
            code="cognitive_model_capability_evidence_source_digest_invalid",
        )
        _validate_identifier(
            self.adapter_id,
            code="cognitive_model_capability_evidence_adapter_invalid",
        )
        _validate_identifier(
            self.model_id,
            code="cognitive_model_capability_evidence_model_invalid",
        )
        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("cognitive_model_capability_evidence_task_kind_invalid")

        _validate_evaluation_support(
            self.task_fit,
            code="cognitive_model_capability_evidence_task_fit_invalid",
        )
        _validate_evaluation_support(
            self.reasoning_support,
            code="cognitive_model_capability_evidence_reasoning_invalid",
        )
        _validate_evaluation_support(
            self.structured_output_support,
            code="cognitive_model_capability_evidence_structured_output_invalid",
        )
        _validate_positive_int(
            self.verified_context_tokens,
            maximum=D135_VERIFIED_CONTEXT_TOKENS_MAX,
            code="cognitive_model_capability_evidence_context_invalid",
        )
        _validate_positive_int(
            self.observed_latency_ms,
            maximum=D135_OBSERVED_LATENCY_MS_MAX,
            code="cognitive_model_capability_evidence_latency_invalid",
        )

        if all(
            value is None
            for value in (
                self.task_fit,
                self.reasoning_support,
                self.structured_output_support,
                self.verified_context_tokens,
                self.observed_latency_ms,
            )
        ):
            raise ValueError("cognitive_model_capability_evidence_empty")


@dataclass(frozen=True, slots=True)
class CognitiveModelCapabilityKnowledgeArtifact:
    envelope: CognitiveArtifactEnvelope
    task_kind: AITaskKind
    adapter_id: str
    model_id: str
    profile_id: str | None
    adapter_discovery_status: AIDiscoveryStatus
    discovery_reason_code: str
    model_discovered: bool
    text_generation_support: ModelCapabilitySupport
    locality: ModelLocality
    configured_context_length: int | None
    configured_reasoning_policy: bool | None
    task_fit: ModelCapabilitySupport
    reasoning_support: ModelCapabilitySupport
    structured_output_support: ModelCapabilitySupport
    max_verified_context_tokens: int | None
    latency_observations_ms: tuple[int, ...]
    limitation_codes: tuple[ModelCapabilityLimitationCode, ...]
    evidence_conflict_codes: tuple[ModelCapabilityConflictCode, ...]
    evaluation_evidence: tuple[ModelCapabilityEvaluationEvidence, ...]
    knowledge_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, CognitiveArtifactEnvelope):
            raise ValueError("cognitive_model_capability_envelope_invalid")
        if (
            self.envelope.producer_organ is not CognitiveOrgan.MODEL_INTELLIGENCE
            or self.envelope.artifact_type != D135_MODEL_CAPABILITY_ARTIFACT_TYPE
            or self.envelope.contract_version
            != D135_MODEL_CAPABILITY_CONTRACT_VERSION
            or self.envelope.status is not CognitiveOrganStatus.READY
            or self.envelope.model_binding_reference is not None
        ):
            raise ValueError("cognitive_model_capability_envelope_invalid")

        if not isinstance(self.task_kind, AITaskKind):
            raise ValueError("cognitive_model_capability_task_kind_invalid")

        _validate_identifier(
            self.adapter_id,
            code="cognitive_model_capability_adapter_invalid",
        )
        _validate_identifier(
            self.model_id,
            code="cognitive_model_capability_model_invalid",
        )
        _validate_optional_identifier(
            self.profile_id,
            code="cognitive_model_capability_profile_invalid",
        )
        if self.adapter_discovery_status not in AI_DISCOVERY_STATUSES:
            raise ValueError("cognitive_model_capability_discovery_status_invalid")
        _validate_identifier(
            self.discovery_reason_code,
            code="cognitive_model_capability_discovery_reason_invalid",
        )
        if type(self.model_discovered) is not bool:
            raise ValueError("cognitive_model_capability_model_discovered_invalid")

        text_generation_support = _validate_support(
            self.text_generation_support,
            code="cognitive_model_capability_text_generation_invalid",
        )
        if self.model_discovered:
            if text_generation_support not in {"supported", "unsupported"}:
                raise ValueError(
                    "cognitive_model_capability_text_generation_projection_invalid"
                )
        elif text_generation_support != "unknown":
            raise ValueError(
                "cognitive_model_capability_text_generation_projection_invalid"
            )

        expected_locality: ModelLocality
        if self.adapter_id == LOCAL_AI_ADAPTER_ID:
            expected_locality = "local"
        elif self.adapter_id == CHATGPT_DEFAULT_ADAPTER_ID:
            expected_locality = "cloud"
        else:
            expected_locality = "unknown"
        if self.locality != expected_locality or self.locality not in _MODEL_LOCALITIES:
            raise ValueError("cognitive_model_capability_locality_invalid")

        if self.profile_id is None:
            if (
                self.configured_context_length is not None
                or self.configured_reasoning_policy is not None
            ):
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
        else:
            if self.adapter_id != LOCAL_AI_ADAPTER_ID:
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
            if not valid_model_id(self.model_id):
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
            expected_profile = {
                AITaskKind.GENERAL_CHAT: GENERAL_CHAT_PROFILE_ID,
                AITaskKind.SOFTWARE_ENGINEERING: SOFTWARE_ENGINEERING_PROFILE_ID,
            }[self.task_kind]
            if self.profile_id != expected_profile:
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
            if (
                type(self.configured_context_length) is not int
                or not 256 <= self.configured_context_length <= 32768
            ):
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
            if (
                self.configured_reasoning_policy is not None
                and type(self.configured_reasoning_policy) is not bool
            ):
                raise ValueError("cognitive_model_capability_profile_projection_invalid")

        task_fit = _validate_support(
            self.task_fit,
            code="cognitive_model_capability_task_fit_invalid",
        )
        reasoning_support = _validate_support(
            self.reasoning_support,
            code="cognitive_model_capability_reasoning_invalid",
        )
        structured_output_support = _validate_support(
            self.structured_output_support,
            code="cognitive_model_capability_structured_output_invalid",
        )

        _validate_positive_int(
            self.max_verified_context_tokens,
            maximum=D135_VERIFIED_CONTEXT_TOKENS_MAX,
            code="cognitive_model_capability_verified_context_invalid",
        )

        if type(self.latency_observations_ms) is not tuple:
            raise ValueError("cognitive_model_capability_latency_observations_invalid")
        for value in self.latency_observations_ms:
            _validate_positive_int(
                value,
                maximum=D135_OBSERVED_LATENCY_MS_MAX,
                code="cognitive_model_capability_latency_observations_invalid",
            )

        if type(self.evaluation_evidence) is not tuple:
            raise ValueError("cognitive_model_capability_evidence_invalid")
        if len(self.evaluation_evidence) > D135_EVALUATION_EVIDENCE_MAX_COUNT:
            raise ValueError("cognitive_model_capability_evidence_invalid")
        if not all(
            isinstance(item, ModelCapabilityEvaluationEvidence)
            for item in self.evaluation_evidence
        ):
            raise ValueError("cognitive_model_capability_evidence_invalid")
        evidence_ids = tuple(item.evidence_id for item in self.evaluation_evidence)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("cognitive_model_capability_evidence_duplicate")
        if evidence_ids != tuple(sorted(evidence_ids)):
            raise ValueError("cognitive_model_capability_evidence_order_invalid")
        for item in self.evaluation_evidence:
            if (
                item.adapter_id != self.adapter_id
                or item.model_id != self.model_id
                or item.task_kind is not self.task_kind
            ):
                raise ValueError("cognitive_model_capability_evidence_binding_invalid")

        expected_task_fit = _aggregate_support(self.evaluation_evidence, "task_fit")
        expected_reasoning = _aggregate_support(
            self.evaluation_evidence,
            "reasoning_support",
        )
        expected_structured = _aggregate_support(
            self.evaluation_evidence,
            "structured_output_support",
        )
        if (
            task_fit != expected_task_fit
            or reasoning_support != expected_reasoning
            or structured_output_support != expected_structured
        ):
            raise ValueError("cognitive_model_capability_evidence_projection_invalid")

        context_values = tuple(
            item.verified_context_tokens
            for item in self.evaluation_evidence
            if item.verified_context_tokens is not None
        )
        expected_max_context = max(context_values) if context_values else None
        if self.max_verified_context_tokens != expected_max_context:
            raise ValueError("cognitive_model_capability_context_projection_invalid")

        expected_latency = tuple(
            item.observed_latency_ms
            for item in self.evaluation_evidence
            if item.observed_latency_ms is not None
        )
        if self.latency_observations_ms != expected_latency:
            raise ValueError("cognitive_model_capability_latency_projection_invalid")

        if type(self.limitation_codes) is not tuple or any(
            value not in _LIMITATION_CODES for value in self.limitation_codes
        ):
            raise ValueError("cognitive_model_capability_limitation_codes_invalid")
        expected_limitations = _derive_limitation_codes(
            task_fit=task_fit,
            reasoning_support=reasoning_support,
            structured_output_support=structured_output_support,
        )
        if self.limitation_codes != expected_limitations:
            raise ValueError("cognitive_model_capability_limitation_codes_invalid")

        if type(self.evidence_conflict_codes) is not tuple or any(
            value not in _CONFLICT_CODES for value in self.evidence_conflict_codes
        ):
            raise ValueError("cognitive_model_capability_conflict_codes_invalid")
        expected_conflicts = _derive_conflict_codes(
            task_fit=task_fit,
            reasoning_support=reasoning_support,
            structured_output_support=structured_output_support,
        )
        if self.evidence_conflict_codes != expected_conflicts:
            raise ValueError("cognitive_model_capability_conflict_codes_invalid")

        refs = self.envelope.input_reference_digests
        if not refs:
            raise ValueError("cognitive_model_capability_provenance_invalid")
        discovery_input_digest = _validate_digest(
            refs[0],
            code="cognitive_model_capability_provenance_invalid",
        )

        evaluation_source_digests = _evaluation_source_digests(
            self.evaluation_evidence
        )

        if self.profile_id is None:
            profile_input_digest = None
            expected_refs = (discovery_input_digest, *evaluation_source_digests)
        else:
            if self.configured_context_length is None:
                raise ValueError("cognitive_model_capability_profile_projection_invalid")
            profile_input_digest = _profile_input_digest_from_artifact(
                profile_id=self.profile_id,
                task_kind=self.task_kind,
                model_id=self.model_id,
                configured_context_length=self.configured_context_length,
                configured_reasoning_policy=self.configured_reasoning_policy,
            )
            expected_refs = (
                discovery_input_digest,
                profile_input_digest,
                *evaluation_source_digests,
            )
        if refs != expected_refs:
            raise ValueError("cognitive_model_capability_provenance_invalid")

        _validate_digest(
            self.knowledge_fingerprint,
            code="cognitive_model_capability_fingerprint_invalid",
        )
        expected_fingerprint = _knowledge_fingerprint(
            task_kind=self.task_kind,
            adapter_id=self.adapter_id,
            model_id=self.model_id,
            profile_id=self.profile_id,
            adapter_discovery_status=self.adapter_discovery_status,
            discovery_reason_code=self.discovery_reason_code,
            model_discovered=self.model_discovered,
            text_generation_support=text_generation_support,
            locality=self.locality,
            configured_context_length=self.configured_context_length,
            configured_reasoning_policy=self.configured_reasoning_policy,
            task_fit=task_fit,
            reasoning_support=reasoning_support,
            structured_output_support=structured_output_support,
            max_verified_context_tokens=self.max_verified_context_tokens,
            latency_observations_ms=self.latency_observations_ms,
            limitation_codes=self.limitation_codes,
            evidence_conflict_codes=self.evidence_conflict_codes,
            evaluation_evidence=self.evaluation_evidence,
            discovery_input_digest=discovery_input_digest,
            profile_input_digest=profile_input_digest,
            evaluation_source_digests=evaluation_source_digests,
        )
        if self.knowledge_fingerprint != expected_fingerprint:
            raise ValueError("cognitive_model_capability_fingerprint_mismatch")


__all__ = [
    "D135_DISCOVERY_CAPABILITY_MAX_COUNT",
    "D135_DISCOVERY_INPUT_DIGEST_VERSION",
    "D135_DISCOVERY_MODEL_MAX_COUNT",
    "D135_EVALUATION_EVIDENCE_MAX_COUNT",
    "D135_EVALUATION_SOURCE_KIND",
    "D135_MODEL_CAPABILITY_ARTIFACT_TYPE",
    "D135_MODEL_CAPABILITY_CONTRACT_VERSION",
    "D135_MODEL_CAPABILITY_FINGERPRINT_VERSION",
    "D135_OBSERVED_LATENCY_MS_MAX",
    "D135_PROFILE_INPUT_DIGEST_VERSION",
    "D135_VERIFIED_CONTEXT_TOKENS_MAX",
    "CognitiveModelCapabilityKnowledgeArtifact",
    "ModelCapabilityConflictCode",
    "ModelCapabilityEvaluationEvidence",
    "ModelCapabilityEvaluationSupport",
    "ModelCapabilityLimitationCode",
    "ModelCapabilitySupport",
    "ModelLocality",
]
