# D135 — Model Intelligence & Capability Knowledge V1

**Document status:** DESIGN FROZEN — OWNER APPROVED
**Design revision:** Rev 0.2
**Architecture phase:** Brain Formation
**Baseline:** D134 COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED
**Baseline commit:** `601ead6e1d17b3efffa28354d85d7b041992fca0`
**Owner Design Reconciliation A–P:** APPROVED
**Exact Contract Proposal Rev 0.1:** APPROVED / SUPERSEDED
**Exact Contract Proposal Rev 0.2:** APPROVED
**Final Contract Review Rev 0.2:** PASS
**Design Freeze authorization:** YES
**Implementation status:** NOT AUTHORIZED / NOT STARTED
**Implementation code change:** NONE
**Push authorization:** NO

---

## 1. Purpose

D135 creates the bounded **Model Intelligence** organ for O-AI Cognitive Brain V1.

Its output is one deterministic, read-only `ModelCapabilityKnowledge` artifact derived from trusted existing model discovery/profile facts plus optional server-trusted structured evaluation evidence.

The governing invariant is:

```text
Model Intelligence ≠ Model Authority
```

D135 may describe what is known, unknown, limited, unsupported, or conflicted about an intelligence engine. It may not select or authorize that engine.

---

## 2. Canonical Baseline

Exact D135 design baseline:

```text
601ead6e1d17b3efffa28354d85d7b041992fca0
```

D135 is additive. It must not rewrite frozen D34, D98, D104/D105, D111, D125, or D126–D134 semantics.

---

## 3. Authority Boundary

D135 must never:

```text
select a provider
select an adapter
select a model
select a profile
rank models
score models
declare a preferred model
change Workspace AI policy
change D111 routing
change D125 profile/model binding
create an ExecutionPlan
grant ExecutionAuthorization
invoke AIRuntime
retry or fallback provider/model/profile
download/delete models
mutate Memory / Policy / Prompt / Code
execute Tool / Module / Plugin / connector
```

Actual model access remains:

```text
Task Domain
   ↓
Workspace Policy
   ↓
D111 Routing
   ↓
D125 Profile
   ↓
ExecutionPlanner
   ↓
ExecutionGuard
   ↓
AIRuntime
```

---

## 4. Existing Systems Reused

D135 reuses:

```text
D34  AIAdapterDiscovery / AIModelDescriptor / discovery status + reason codes
D111 provider/adapter routing authority
D125 LocalAIProfile facts and server-owned profile/model binding
D126 CognitiveOrgan.MODEL_INTELLIGENCE + CognitiveArtifactEnvelope
D127 CognitiveTaskDescription + authoritative AITaskKind
```

D135 creates no parallel discovery, routing, profile, authorization, or execution system.

---

## 5. Required Separation of Facts

D135 preserves four distinct concepts:

```text
DISCOVERY FACT
model X was/was not discovered; capability Y was/was not declared

≠

PROFILE FACT
model X is configured under profile P with configured runtime behavior

≠

EVALUATION FACT
trusted structured evidence observed model X under task kind T

≠

ROUTING AUTHORITY
therefore choose model X
```

The first three may inform ModelCapabilityKnowledge. The fourth is forbidden.

---

## 6. Exact Constants

```python
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
```

D135 reuses D126 identifier/digest bounds.

---

## 7. Exact Vocabularies

```python
ModelCapabilitySupport = Literal[
    "supported",
    "limited",
    "unsupported",
    "unknown",
    "conflicted",
]

ModelCapabilityEvaluationSupport = Literal[
    "supported",
    "limited",
    "unsupported",
]

ModelLocality = Literal[
    "local",
    "cloud",
    "unknown",
]

ModelCapabilityLimitationCode = Literal[
    "task_fit_limited",
    "task_fit_unsupported",
    "reasoning_limited",
    "reasoning_unsupported",
    "structured_output_limited",
    "structured_output_unsupported",
]

ModelCapabilityConflictCode = Literal[
    "task_fit_conflict",
    "reasoning_support_conflict",
    "structured_output_support_conflict",
]
```

Aggregate semantics:

```text
no trusted evidence      → unknown
one distinct result      → supported / limited / unsupported
more than one result     → conflicted
```

No majority vote, weighting, latest-wins rule, or reputation heuristic is permitted.

---

## 8. Structured Evaluation Evidence

```python
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
```

Rules:

```text
evidence_id: bounded safe trimmed identifier
source_kind: exactly server_evaluation
source_digest: lowercase SHA-256
adapter/model/task: exact target binding
at least one observation field non-None
verified_context_tokens: integer 1..10,000,000
observed_latency_ms: integer 1..3,600,000
evidence IDs unique
maximum evidence count = 32
```

Evidence-level `unknown` and `conflicted` are invalid. Those are aggregate states only.

---

## 9. Trusted Evaluation Source Boundary

D135 V1 accepts only explicit server-trusted structured evaluation evidence.

It must not directly transform any of these into evaluation evidence:

```text
user message
normalized_request
Conversation text
Context text
Memory value
Knowledge text
model output
Draft response
ExperienceCandidate
frontend/browser metadata
arbitrary request metadata
provider exception text
telemetry sample by itself
```

D134 ExperienceCandidate is not automatically D135 evaluation evidence.

---

## 10. Exact Output Artifact

```python
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

    discovery_input_digest: str
    profile_input_digest: str | None
    evaluation_source_digests: tuple[str, ...]

    knowledge_fingerprint: str
```

This artifact grants no routing or execution authority.

---

## 11. Envelope Contract

Exact envelope requirements:

```text
producer_organ = CognitiveOrgan.MODEL_INTELLIGENCE
artifact_type = cognitive.model_capability_knowledge
contract_version = o-ai.cognitive-model-capability-knowledge.v1
status = READY
model_binding_reference = None
```

The artifact is not model-produced.

---

## 12. Task / Turn / Workspace / Context Binding

The coordinator requires a D127 `CognitiveTaskDescription`.

Exact binding:

```text
envelope.turn_id == task.envelope.turn_id
envelope.workspace_id is task.envelope.workspace_id
envelope.context_snapshot_digest == task.envelope.context_snapshot_digest
```

D135 never reads or refreshes Context contents.

---

## 13. Exact Coordinator Interface

```python
class CognitiveModelIntelligenceCoordinator:
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
        ...
```

`target_model_id` identifies the subject of the knowledge artifact. It is not a model-selection instruction.

Forbidden coordinator methods include:

```text
select_model
choose_model
best_model
preferred_model
rank_models
score_models
route
fallback
```

---

## 14. Target Adapter Binding

The target adapter is exactly `discovery.adapter_id`.

Every evaluation item must bind to that exact adapter and target model.

---

## 15. D34 Discovery Bounds and Coherence

D135 accepts only bounded D34 input:

```text
len(discovery.models) <= 256
len(discovery.capability_ids) <= 32
len(each model.capability_ids) <= 32
```

Every model capability set must satisfy:

```text
model.capability_ids ⊆ discovery.capability_ids
```

Violation is fail-closed. D135 performs no truncation, union, dropping, or repair.

---

## 16. Exact D34 Reason-Code Boundary

Accepted D34 reason codes are exactly:

```text
models_discovered
configured_model
adapter_disabled
runtime_unavailable
configured_model_unavailable
discovery_source_missing
model_discovery_unsupported
configured_model_missing
cloud_ai_disabled
cloud_ai_credential_missing
```

No arbitrary discovery reason string is projected.

---

## 17. Discovery Projection

For exact target model:

```text
target descriptor exists → model_discovered = True
target descriptor absent → model_discovered = False
```

`configured_model_id` alone does not prove discovery.

Text generation:

```text
descriptor exists + text_generation present → supported
descriptor exists + text_generation absent  → unsupported
descriptor absent                            → unknown
```

Adapter discovery status remains separate from target model discovery.

---

## 18. Discovery Input Digest

Canonical digest payload:

```json
{
  "digest_version": "o-ai.d135.discovery-input.v1",
  "adapter_id": "<adapter>",
  "status": "<status>",
  "configured_model_id": null,
  "capability_ids": [],
  "models": [
    {"model_id": "<model>", "capability_ids": []}
  ],
  "reason_code": "<reason>"
}
```

The full D34 discovery input is bound, not only the selected target descriptor.

---

## 19. Locality Projection

```text
local_ai.default  → local
chatgpt.default   → cloud
all other adapter → unknown
```

Locality is not privacy/safety/egress authority.

---

## 20. Local AI Profile Binding

When a profile is supplied:

```text
discovery.adapter_id == local_ai.default
local_profile.task_kind is task.authoritative_ai_task_kind
local_profile.model_id == target_model_id
```

The profile must be a valid D125 `LocalAIProfile`.

For non-local adapters, `local_profile` must be `None`.

A discovered Local AI model may be described with `local_profile=None`; this grants no authorization to use it.

---

## 21. Profile Projection

With a valid profile:

```text
profile_id = profile.profile_id
configured_context_length = profile.context_length
configured_reasoning_policy = profile.reasoning_enabled
```

Without a profile all three are `None`.

Profile timeout is not projected as latency evidence.

---

## 22. Configuration Is Not Intrinsic Capability

```text
configured_context_length ≠ intrinsic model maximum context
configured_context_length ≠ verified quality at that size
reasoning_enabled=True     ≠ reasoning supported
reasoning_enabled=False    ≠ reasoning unsupported
```

Reasoning support and verified context require evaluation evidence.

---

## 23. Profile Input Digest

When a profile is supplied, digest only the D135-consumed facts:

```json
{
  "digest_version": "o-ai.d135.profile-input.v1",
  "profile_id": "<profile>",
  "task_kind": "<task-kind>",
  "model_id": "<model>",
  "context_length": 0,
  "reasoning_enabled": null
}
```

When absent: `profile_input_digest = None`.

---

## 24. Evaluation Canonicalization and Aggregation

Evaluation evidence is sorted ascending by `evidence_id`.

Caller order creates no priority.

For each of:

```text
task_fit
reasoning_support
structured_output_support
```

aggregate only non-None observations:

```text
zero distinct values → unknown
one distinct value   → that value
>1 distinct values   → conflicted
```

No majority vote, weighting, latest-wins, or source priority.

---

## 25. Verified Context Observation

```text
no verified_context_tokens observations → None
one or more observations → maximum observed value
```

This means only “maximum explicit context size represented by trusted evidence.” It is not an intrinsic model maximum claim.

---

## 26. Latency Observations

`latency_observations_ms` contains non-None latency observations in canonical evidence order.

D135 computes no fast/slow category, average quality score, latency ranking, preferred model, or routing score.

Existing telemetry is not automatically converted into benchmark evidence.

---

## 27. Derived Limitation Codes

Derived in exact field order:

```text
task_fit
reasoning_support
structured_output_support
```

Mappings:

```text
task_fit limited                  → task_fit_limited
task_fit unsupported              → task_fit_unsupported
reasoning_support limited         → reasoning_limited
reasoning_support unsupported     → reasoning_unsupported
structured_output_support limited → structured_output_limited
structured_output_support unsupported → structured_output_unsupported
```

`unknown`, `supported`, and `conflicted` produce no limitation code.

Caller cannot supply or reorder these codes.

---

## 28. Derived Conflict Codes

Derived in the same exact field order:

```text
task_fit conflicted                  → task_fit_conflict
reasoning_support conflicted         → reasoning_support_conflict
structured_output_support conflicted → structured_output_support_conflict
```

Caller cannot supply or reorder these codes.

---

## 29. Evaluation Source Digests

`evaluation_source_digests` is the unique set of evidence source digests sorted ascending.

Multiple evidence records may reference one trusted source digest.

---

## 30. Envelope Input Reference Digests

Exact sequence:

```text
(
    discovery_input_digest,
    profile_input_digest if present,
    *evaluation_source_digests,
)
```

Maximum possible count:

```text
1 discovery + 1 profile + 32 evaluation sources = 34
```

This remains below D126 reference max 64.

No truncation is permitted.

---

## 31. Unknown Semantics

Absence of trusted evidence means exactly:

```text
unknown
```

D135 must not infer capability from model ID/family, provider reputation, profile name, configured context length, reasoning configuration, or successful discovery alone except where an exact projection rule in this spec explicitly permits it.

---

## 32. Fingerprint

The canonical knowledge fingerprint includes:

```text
fingerprint_version
task_kind
adapter_id
model_id
profile_id
adapter_discovery_status
discovery_reason_code
model_discovered
text_generation_support
locality
configured_context_length
configured_reasoning_policy
task_fit
reasoning_support
structured_output_support
max_verified_context_tokens
latency_observations_ms
limitation_codes
evidence_conflict_codes
evaluation_evidence
discovery_input_digest
profile_input_digest
evaluation_source_digests
```

The full structured evaluation evidence values are included.

It excludes:

```text
turn_id
workspace_id
conversation_id
project_id
ContextSnapshot digest
created_at
```

This fingerprint represents semantic knowledge/provenance shape, not artifact identity or authority.

---

## 33. Canonical JSON / SHA-256

All D135 canonical digests/fingerprints use:

```python
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
```

then UTF-8 → SHA-256 lowercase hexadecimal.

---

## 34. Idempotence and Source Immutability

Same exact inputs including the same envelope produce equal artifacts.

Semantic fingerprint is independent of turn/workspace/Context/time identity when all fingerprint-included inputs/results are equal.

D135 must not mutate task, discovery, model descriptors, profile, or evidence objects.

---

## 35. Contract Error

```python
class CognitiveModelIntelligenceContractError(Exception):
    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

Malformed/incoherent coordinator input yields no fabricated knowledge artifact.

Direct invalid construction of D135 contract dataclasses may raise `ValueError`.

---

## 36. Safe Identifier Rules

D135 identifiers are non-empty, trimmed, valid UTF-8, contain no control characters, and are bounded by D126 `COGNITIVE_ID_MAX_BYTES`.

Profile-bound Local AI model IDs must additionally satisfy D125 validation.

No normalization or rewriting is allowed.

---

## 37. No Benchmark Execution / No LLM

D135 may consume already-formed server-trusted structured evaluation evidence but runs no benchmark workload.

It performs no prompt generation, provider generation, benchmark replay, tournament, quality scoring, or automatic evaluation generation.

D135 model invocation count is exactly:

```text
0
```

D126 invocation purposes remain unchanged:

```text
PRIMARY_SYNTHESIS
CRITIC
REVISION
POST_REVISION_CRITIC
```

---

## 38. Persistence / Background Boundary

D135 V1 is ephemeral/read-only.

No:

```text
DB table/column
Alembic migration
repository
persistent model score
persistent benchmark history
browser persistence
Conversation/Project/Memory persistence
automatic accumulation
scheduler
periodic evaluator
background model scorer
background discovery loop
```

---

## 39. D134 Boundary

D134 ExperienceCandidate does not automatically become D135 evidence.

Forbidden automatic transitions:

```text
ExperienceCandidate → model score
ExperienceCandidate → task strength
ExperienceCandidate → capability rating
ExperienceCandidate → preferred model
ExperienceCandidate → routing change
ExperienceCandidate → profile rewrite
```

---

## 40. D136 Boundary

D136 remains owner of integrated runtime orchestration, including when Model Intelligence is consulted, fresh authorization, invocation purpose, deadlines, budgets, circuit breakers, late-result handling, and Critic/revision orchestration.

D135 provides bounded knowledge only.

---

## 41. No Working-State Mutation

D135 does not modify `backend/app/intelligence/context/cognitive.py` and does not add a D128 Working State field.

D136 will later define integrated runtime consultation.

---

## 42. Hygiene Boundary

D135 artifact/evidence fields must not contain:

```text
normalized_request
raw user/assistant text
Draft text
Context/Knowledge/Memory contents
system/provider prompt
hidden reasoning / chain-of-thought
credentials / API keys / OAuth tokens
arbitrary exception text
arbitrary benchmark/model-review prose
```

Allowed data is bounded structured metadata, safe identifiers, enums/statuses, integer observations, and cryptographic digests.

---

## 43. Exact Implementation Scope

After separate Owner implementation authorization, exactly four NEW paths:

```text
backend/app/contracts/cognitive_model_intelligence.py
backend/app/services/cognitive_model_intelligence.py
backend/tests/test_d135_cognitive_model_intelligence.py
backend/tests/test_d135_cognitive_model_intelligence_security.py
```

Any fifth implementation path:

```text
STOP
→ dependency / contradiction report
→ Owner amendment review
```

---

## 44. Explicitly Unmodified Areas

D135 implementation must not modify:

```text
D34 discovery contracts/services/sources
D98 workspace AI policy
D104/D105 task-aware routing
D111 brain routing
D125 Local AI profiles
D126/D127 core/task contracts
D128-D134 production code
Working State
ExecutionPlanner
ExecutionGuard
AIRuntime
telemetry
Memory
Context
Conversation
Knowledge
DB / Alembic / repositories
API
frontend
```

Historical tests may not be edited to make D135 pass.

---

## 45. Functional Test Contract

Exact file:

```text
backend/tests/test_d135_cognitive_model_intelligence.py
```

Exact count: `F01–F48` (48 tests).

```text
F01 exact constants
F02 exact support vocabularies
F03 exact locality / limitation / conflict vocabularies
F04 exact evaluation source kind and numeric/count bounds
F05 valid task-fit evidence
F06 valid reasoning evidence
F07 valid structured-output evidence
F08 valid context + latency evidence
F09 discovered target + text generation → supported
F10 discovered target without text generation → unsupported
F11 absent target → not discovered + text generation unknown
F12 unavailable adapter may still preserve discovered target
F13 configured_model_id alone does not prove discovery
F14 exact discovery status/reason projection
F15 Local AI locality
F16 ChatGPT cloud locality
F17 unknown adapter locality
F18 General Chat profile projection
F19 Software Engineering profile projection
F20 Local AI model may be described without profile
F21 configured context separate from verified context
F22 configured reasoning policy separate from reasoning support
F23 no evidence → unknown evaluated supports
F24 unanimous supported aggregation
F25 unanimous limited aggregation
F26 unanimous unsupported aggregation
F27 task-fit conflict aggregation
F28 reasoning conflict aggregation
F29 structured-output conflict aggregation
F30 max verified context from explicit observations
F31 absent verified context → None
F32 latency observations canonical order
F33 absent latency → empty tuple
F34 limitation codes exact derived order
F35 conflict codes exact derived order
F36 evidence canonicalized by evidence_id
F37 source digests unique + sorted
F38 discovery digest deterministic
F39 profile digest deterministic
F40 fingerprint deterministic
F41 fingerprint independent of turn/workspace/Context/time identity
F42 fingerprint changes with discovery facts/digest
F43 fingerprint changes with profile facts/digest
F44 fingerprint changes with evaluation facts/source digests
F45 artifact/evidence frozen + slots
F46 exact repeated invocation idempotent
F47 source objects remain unchanged
F48 caller evidence ordering does not change canonical fingerprint
```

---

## 46. Security Test Contract

Exact file:

```text
backend/tests/test_d135_cognitive_model_intelligence_security.py
```

Exact count: `S01–S88` (88 tests).

```text
S01 wrong envelope producer rejected
S02 wrong artifact type rejected
S03 wrong contract version rejected
S04 non-READY envelope rejected
S05 model binding reference rejected
S06 turn mismatch rejected
S07 workspace mismatch rejected
S08 Context digest mismatch rejected
S09 wrong task input type rejected
S10 malformed target model ID rejected
S11 malformed discovery/adapter ID rejected
S12 malformed output fingerprint rejected

S13 discovery models >256 rejected without truncation
S14 adapter capabilities >32 rejected without truncation
S15 model capabilities >32 rejected without truncation
S16 model capability outside adapter set rejected
S17 incoherence not silently unioned
S18 incoherence not silently dropped
S19 unknown D34 reason rejected
S20 malformed D34 status/fact input rejected
S21 duplicate discovered model identity rejected at boundary/upstream
S22 configured model mismatch alone cannot imply target absence/presence

S23 non-local adapter + LocalAIProfile rejected
S24 wrong local-profile type rejected
S25 profile task-kind mismatch rejected
S26 profile model mismatch rejected
S27 invalid D125 profile identity rejected
S28 profile cannot authorize alternate/undiscovered model use
S29 profile context cannot become verified-context evidence
S30 reasoning_enabled true cannot become reasoning-supported evidence
S31 reasoning_enabled false cannot become reasoning-unsupported evidence
S32 profile ID cannot become routing authority
S33 target model ID cannot become execution selection
S34 profile timeout is not latency evidence

S35 evidence count >32 rejected without truncation
S36 duplicate evidence IDs rejected
S37 wrong evidence source_kind rejected
S38 malformed source digest rejected
S39 evidence adapter mismatch rejected
S40 evidence model mismatch rejected
S41 evidence task-kind mismatch rejected
S42 evidence with no observations rejected
S43 invalid task-fit literal rejected
S44 invalid reasoning literal rejected
S45 invalid structured-output literal rejected
S46 evidence-level unknown rejected
S47 evidence-level conflicted rejected
S48 verified-context zero rejected
S49 verified-context overflow rejected
S50 non-integer verified-context rejected
S51 latency zero rejected
S52 latency overflow rejected
S53 non-integer latency rejected
S54 malformed evidence ID rejected

S55 no evidence remains unknown, not unsupported
S56 model name cannot infer task fit
S57 model name cannot infer reasoning support
S58 model name cannot infer structured-output support
S59 provider reputation cannot infer task fit
S60 discovery availability alone cannot infer task fit
S61 configured context cannot infer intrinsic capacity
S62 reasoning policy cannot infer reasoning capability
S63 task-fit conflict never majority-voted
S64 reasoning conflict never latest-wins
S65 structured-output conflict never source-prioritized
S66 conflicted cannot be downgraded to limited
S67 unknown cannot be upgraded to supported
S68 D134 ExperienceCandidate is not automatic evaluation evidence

S69 refs missing discovery digest rejected
S70 refs missing profile digest rejected when profile present
S71 profile digest ref rejected when profile absent
S72 refs missing evaluation source digest rejected
S73 refs adding unknown digest rejected
S74 refs reordering rejected
S75 refs require unique sorted evaluation digests
S76 discovery digest tampering rejected
S77 profile digest tampering rejected
S78 evaluation digest projection tampering rejected
S79 limitation-code tampering rejected
S80 limitation-code reordering rejected
S81 conflict-code tampering rejected
S82 conflict-code reordering rejected
S83 fingerprint mismatch rejected

S84 raw request/response/Context/Memory/Knowledge fields absent
S85 hidden reasoning/prompt/credential/free-text benchmark fields absent
S86 no ranking/preferred-model/routing/selection authority surface
S87 no persistence/DB/repository/scheduler/background evaluator surface
S88 no provider/network/model invocation and no D136 runtime authority surface
```

---

## 47. Exact Targeted Historical Regression

Exactly 27 files:

```text
backend/tests/test_ai_capability_model_discovery.py
backend/tests/test_ai_discovery_contract.py
backend/tests/test_workspace_ai_policy.py
backend/tests/test_d98_workspace_ai_production_wiring.py
backend/tests/test_d98_workspace_ai_routing_security.py
backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
backend/tests/test_d105_task_aware_ai_routing_integration.py
backend/tests/test_d105_task_aware_ai_routing_security.py
backend/tests/test_d111_ai_brain_routing_contract.py
backend/tests/test_d111_ai_brain_routing_service.py
backend/tests/test_d111_ai_brain_runtime_integration.py
backend/tests/test_d111_ai_brain_runtime_security.py
backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py
backend/tests/test_d126_cognitive_brain_core_contracts.py
backend/tests/test_d126_cognitive_brain_core_contracts_security.py
backend/tests/test_d127_cognitive_input_semantics.py
backend/tests/test_d127_cognitive_input_semantics_security.py
backend/tests/test_d134_cognitive_experience.py
backend/tests/test_d134_cognitive_experience_security.py
backend/tests/test_execution_planner.py
backend/tests/test_execution_guard.py
backend/tests/test_ai_runtime.py
backend/tests/test_local_ai_adapter.py
```

Then full backend regression is required.

---

## 48. Validation Protocol

```text
1. branch / baseline / origin / live remote verification
2. frozen D135 spec SHA verification
3. exact four-path implementation scope verification
4. D135 functional F01-F48
5. D135 security S01-S88
6. exact 27-file targeted historical regression
7. full backend regression
8. final exact scope / hashes / frozen-spec verification
9. Owner Guided Acceptance
10. separate local implementation commit authorization
11. independent local implementation commit verification
12. separate normal implementation push authorization
13. independent remote implementation verification
14. milestone close
```

No stage implies authorization for a later stage.

---

## 49. Owner Guided Acceptance Intent

At minimum:

```text
A. Model Intelligence is read-only capability knowledge.
B. D135 cannot select provider, adapter, model, or profile.
C. D98/D111/D125 authority remains unchanged.
D. D34 discovery is reused, not duplicated.
E. Profile configuration is not misrepresented as intrinsic capability.
F. No trusted evidence means unknown.
G. Conflicting trusted evidence means conflicted.
H. No majority vote / latest-wins arbitration.
I. No model/provider-name capability inference.
J. Evaluation evidence is server-trusted structured input.
K. Raw prompt/response/Context/Memory/Knowledge content is absent.
L. Discovery/profile/evaluation provenance is cryptographically bound.
M. Provenance is never silently truncated.
N. D134 ExperienceCandidate cannot auto-change model knowledge/routing.
O. No DB/persistence/scheduler/LLM/background evaluator.
P. D136 retains runtime/invocation/deadline/circuit-breaker ownership.
```

---

## 50. Design Freeze Scope

D135 Design Freeze changes exactly one path:

```text
docs/specs/D135_MODEL_INTELLIGENCE_CAPABILITY_KNOWLEDGE_V1.md
```

Design Freeze commit subject:

```text
docs: freeze D135 model intelligence capability knowledge design
```

This authorization permits the local design-freeze spec commit only.

It does not authorize:

```text
push
implementation
implementation commit
implementation push
reset
rebase
force
force-with-lease
```

---

## 51. Current Gate State at Design Freeze

```text
D134:
COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED

D135 BASELINE:
601ead6e1d17b3efffa28354d85d7b041992fca0

D135 OWNER DESIGN RECONCILIATION A-P:
APPROVED / CONSUMED

D135 EXACT CONTRACT PROPOSAL REV 0.1:
APPROVED / SUPERSEDED

D135 EXACT CONTRACT PROPOSAL REV 0.2:
APPROVED / CONSUMED

D135 FINAL CONTRACT REVIEW REV 0.2:
PASS

D135 DESIGN FREEZE:
OWNER AUTHORIZED

D135 IMPLEMENTATION:
NOT AUTHORIZED / NOT STARTED

IMPLEMENTATION CODE CHANGE:
NONE

GIT PUSH:
NOT AUTHORIZED / NOT PUSHED
```

---

**End of D135 Model Intelligence & Capability Knowledge V1 — Rev 0.2 Frozen Design Baseline**
