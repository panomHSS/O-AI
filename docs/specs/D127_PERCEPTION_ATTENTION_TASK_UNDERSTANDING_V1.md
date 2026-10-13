# D127 — Perception / Attention / Task Understanding V1

**Status:** DESIGN FROZEN - OWNER APPROVED
**Design revision:** Rev 1.0 - FROZEN DESIGN BASELINE
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN
**D126 baseline:** COMPLETE / PUSHED / REMOTE FROZEN
**D126 implementation commit:** `e84365990ef9cd3595fb32dd36fada89add361d2`
**Live `origin/main` rechecked before Draft 0.2:** `e84365990ef9cd3595fb32dd36fada89add361d2`
**Owner Design Review:** PASS - Decisions A-J APPROVED
**Implementation:** NOT STARTED
**Code change:** NONE
**Git commit:** DESIGN FREEZE COMMIT
**Git push:** NOT PUSHED
**Codex:** NOT USED

---

## 1. Purpose

D127 forms three Brain V1 organs as canonical contracts and deterministic compatibility services:

1. **Perception**
2. **Attention**
3. **Goal & Task Understanding**

The governing rule remains:

> **Perception observes. Attention records deterministic focus. Task Understanding describes the task. None of them grants authority.**

D127 must reconcile existing O-AI foundations rather than create parallel retrieval, ranking, intent, routing, persistence, or execution systems.

The frozen architecture relation remains:

```text
Owner Goal
   ↓
Interaction Intent
   ↓
Cognitive Intent
   ↓
Task Domain
   ↓
Server-owned Model / Runtime Policy
```

with the strict separations:

```text
Interaction Intent ≠ Cognitive Intent
Cognitive Intent   ≠ Task Domain
Task Description   ≠ routing authority
Perception         ≠ authorization
Attention          ≠ provider/model selection
```

---

## 2. Draft 0.1 Owner Decisions — APPROVED

The Owner approved all Draft 0.1 decisions A–F.

### A — Interaction Intent vocabulary

APPROVED:

```text
chat
action_request
approval_related_input
runtime_status_request
unknown
```

### B — Cognitive Intent ownership

APPROVED:

The exact live `ReasoningIntent` vocabulary becomes canonical D127 `CognitiveIntent`:

```text
factual_lookup
explanation
comparison
procedure
troubleshooting
summary
general
```

Historical `ReasoningIntent` remains a compatibility alias.

### C — Perception / Attention strategy

APPROVED:

```text
D94/D95 remain the Context substrate
ContextCandidate remains source-candidate substrate
ContextResolver remains selection/budget/dedupe authority
D127 creates brain-facing metadata projections only
```

### D — Interaction classification authority

APPROVED:

D127 does not infer action/approval/runtime lanes from arbitrary Owner text.

Current deterministic compatibility mapping is limited to:

```text
chat_message -> chat
unknown      -> unknown
```

Other Interaction Intent values require a server-owned lane signal.

### E — Task Domain authority

APPROVED:

`CognitiveTaskDescription.authoritative_ai_task_kind` must be an exact existing `AITaskKind` supplied by the server-owned authority path.

Cognitive Intent can never derive or mutate it.

### F — Runtime integration boundary

APPROVED:

D127 does not modify:

```text
ConversationService
ContextResolver
AI routing runtime
ExecutionGuard
AIRuntime
D125 model/profile mapping
```

D128/D129/D136 own later runtime integration.

---

## 3. Reconciled Existing Ownership

### 3.1 Perception foundation

Existing:

```text
ContextResolveRequest
ContextSourcePort
ContextCandidate

ConversationContextSource
ProjectContextSource
MemoryContextSource
KnowledgeContextSource
```

`ContextCandidate` already carries:

```text
source
text
label
relevance
order_key
```

D127 will not duplicate raw candidate text into a second cognitive payload.

### 3.2 Attention foundation

Existing deterministic Attention-like behavior remains owned by D95:

```text
source candidate ordering
memory relevance scoring
knowledge search rank
conversation recency
project current-state projection
workspace validation
identity dedupe/conflict detection
per-layer candidate limits
whole-item budget enforcement
layer ordering
```

Exact Context layer order remains:

```text
CONVERSATION
PROJECT
MEMORY
KNOWLEDGE
```

D127 does not introduce a universal cross-layer score.

### 3.3 Interaction Intent foundation

Existing command-level vocabulary:

```text
CommandIntent =
    chat_message
    unknown
```

Existing `provider_preference_hint` values remain routing hints and are explicitly outside D127 Interaction Intent.

Connector-specific `ChatPluginIntentOutcome` remains connector/action-lane metadata and does not create Task Domain values.

### 3.4 Cognitive Intent foundation

Existing live vocabulary and classifier:

```text
ReasoningIntent
RuleBasedIntentClassifier
```

become the compatibility foundation for canonical D127 Cognitive Intent.

The live behavior is preserved semantically:

```text
comparison
procedure
troubleshooting
summary
explanation
factual_lookup
general
```

No classifier keyword/order change is authorized in D127.

### 3.5 Task Domain authority

Existing exact task-domain authority remains:

```text
AITaskKind.GENERAL_CHAT
AITaskKind.SOFTWARE_ENGINEERING
```

No additional task kind is introduced.

---

## 4. Exact D127 Production Modules

D127 proposes exactly two production modules as its new canonical ownership points.

```text
NEW backend/app/contracts/cognitive_input_semantics.py
NEW backend/app/services/cognitive_input_semantics.py
```

Two existing reasoning files receive narrow compatibility edits:

```text
MODIFY backend/app/schemas/reasoning.py
MODIFY backend/app/services/reasoning.py
```

No other production module is authorized by Draft 0.2.

---

## 5. Exact Contract Constants

`backend/app/contracts/cognitive_input_semantics.py` will define:

```text
D127_PERCEPTION_ARTIFACT_TYPE
    = "cognitive.perception"

D127_PERCEPTION_CONTRACT_VERSION
    = "o-ai.cognitive-perception.v1"

D127_ATTENTION_ARTIFACT_TYPE
    = "cognitive.attention"

D127_ATTENTION_CONTRACT_VERSION
    = "o-ai.cognitive-attention.v1"

D127_TASK_DESCRIPTION_ARTIFACT_TYPE
    = "cognitive.task_description"

D127_TASK_DESCRIPTION_CONTRACT_VERSION
    = "o-ai.cognitive-task-description.v1"

D127_ATTENTION_SELECTION_POLICY
    = "d95_context_resolver.v1"

D127_NORMALIZED_REQUEST_MAX_BYTES
    = 16_384

D127_TASK_METADATA_ITEM_MAX_BYTES
    = 128

D127_TASK_METADATA_MAX_COUNT
    = 32

D127_PERCEPTION_MAX_PERCEPTS
    = 16_384

D127_ATTENTION_MAX_SELECTED_SOURCES
    = 256
```

Derivation notes:

```text
16_384 normalized request bytes
    = existing CONTEXT_RESOLVE_QUERY_MAX_BYTES

16_384 perception refs
    = 4 Context layers × existing max 4,096 candidates per layer

256 attention refs
    = existing CONTEXT_BUNDLE_MAX_ITEMS
```

D127 freezes these values explicitly rather than allowing future unrelated Context changes to silently alter the D127 contract.

---

## 6. Exact Canonical Intent Types

To preserve historical Pydantic and serialized behavior, Draft 0.2 uses `Literal` type aliases rather than changing existing intent strings into Enums.

### 6.1 `CognitiveInteractionIntent`

Exact:

```python
CognitiveInteractionIntent = Literal[
    "chat",
    "action_request",
    "approval_related_input",
    "runtime_status_request",
    "unknown",
]
```

### 6.2 `CognitiveIntent`

Exact:

```python
CognitiveIntent = Literal[
    "factual_lookup",
    "explanation",
    "comparison",
    "procedure",
    "troubleshooting",
    "summary",
    "general",
]
```

Rules:

- exact lowercase values only;
- no aliases;
- no case folding at contract validation;
- no dynamic extension;
- arbitrary string values fail closed when constructing D127 artifacts;
- the type itself grants no routing or execution authority.

### 6.3 Historical alias

`app/schemas/reasoning.py` becomes:

```text
ReasoningIntent = CognitiveIntent
```

with no change to serialized `ReasoningPlan.intent`.

---

## 7. Shared Exact Validation Rules

### 7.1 Metadata identifier

For `required_information`, `information_gaps`, and `constraints`, each item must be:

```text
exact str
non-empty
trimmed
UTF-8 length <= 128 bytes
contains no Unicode category Cc
```

Collection rules:

```text
accept finite Sequence except str/bytes/bytearray
copy immediately to tuple
max 32 items
duplicate exact values rejected
source order preserved
```

No silent trimming or case normalization.

### 7.2 Normalized Owner request

`normalized_request` must be:

```text
exact str
non-empty
UTF-8 length <= 16,384 bytes
contains no NUL / Unicode Cc
equals " ".join(value.split())
```

Therefore leading/trailing/repeated whitespace and tabs/newlines must be normalized before contract construction.

The D127 service performs this normalization before constructing the contract.

### 7.3 Exact existing authority types

D127 requires exact existing contract objects:

```text
WorkspaceId
ContextSourceRef
ContextBundle
AITaskKind
CognitiveArtifactEnvelope
```

Raw string substitutes fail closed where runtime validation applies.

---

## 8. `CognitivePerceptRef`

Exact immutable data contract:

```text
CognitivePerceptRef
├── source: ContextSourceRef
├── candidate_rank: int
└── relevance: int | float | None
```

Validation:

```text
source
    exact ContextSourceRef

candidate_rank
    exact int
    bool rejected
    1 <= value <= 16,384

relevance
    None allowed
    otherwise finite int|float
    bool rejected
    NaN/infinity rejected
```

`candidate_rank` records source-candidate position supplied to the D127 projector, not a global cross-layer score.

D127 does not calculate new relevance.

### Duplicate-source refinement from Draft 0.1

Draft 0.2 intentionally does **not** reject duplicate `ContextSourceRef` values in Perception.

Reason:

- Perception represents observed pre-selection candidates;
- D95 already owns duplicate collapse and conflicting-projection rejection;
- D127 must not preempt D95 dedupe semantics;
- `candidate_rank` preserves observation position.

Therefore:

```text
Perception may observe duplicate source identity.
Attention may not contain duplicate selected source identity.
```

---

## 9. `CognitivePerceptionArtifact`

Exact immutable contract:

```text
CognitivePerceptionArtifact
├── envelope: CognitiveArtifactEnvelope
└── percepts: tuple[CognitivePerceptRef, ...]
```

Envelope requirements:

```text
producer_organ == CognitiveOrgan.PERCEPTION
artifact_type == "cognitive.perception"
contract_version == "o-ai.cognitive-perception.v1"
```

Percept collection requirements:

```text
input copied to tuple
max 16,384 entries
each item exact CognitivePerceptRef
candidate ranks exactly 1..N in artifact order
every source.workspace_id == envelope.workspace_id
```

An empty Perception artifact is valid.

The artifact has no raw Context text, raw prompt, provider/model/profile, approval, execution authorization, tool permission, routing directive, or memory-mutation field.

---

## 10. `CognitiveAttentionArtifact`

Exact immutable contract:

```text
CognitiveAttentionArtifact
├── envelope: CognitiveArtifactEnvelope
├── selected_sources: tuple[ContextSourceRef, ...]
└── selection_policy: str
```

Envelope requirements:

```text
producer_organ == CognitiveOrgan.ATTENTION
artifact_type == "cognitive.attention"
contract_version == "o-ai.cognitive-attention.v1"
```

Selection requirements:

```text
selection_policy == "d95_context_resolver.v1"
selected_sources copied to tuple
max 256 entries
every item exact ContextSourceRef
every source.workspace_id == envelope.workspace_id
duplicate exact source identities rejected
source order preserved exactly
```

Empty Attention is valid.

Attention records D95-selected focus. It does not rank, retrieve, dedupe, budget, truncate, reorder, select a provider/model/profile, or authorize execution.

---

## 11. `CognitiveTaskDescription`

Exact immutable contract:

```text
CognitiveTaskDescription
├── envelope: CognitiveArtifactEnvelope
├── interaction_intent: CognitiveInteractionIntent
├── cognitive_intent: CognitiveIntent
├── authoritative_ai_task_kind: AITaskKind
├── normalized_request: str
├── required_information: tuple[str, ...]
├── information_gaps: tuple[str, ...]
└── constraints: tuple[str, ...]
```

Envelope requirements:

```text
producer_organ == CognitiveOrgan.TASK_UNDERSTANDING
artifact_type == "cognitive.task_description"
contract_version == "o-ai.cognitive-task-description.v1"
```

`interaction_intent` and `cognitive_intent` must be exact D127 values.

`authoritative_ai_task_kind` must be an exact existing `AITaskKind`; raw strings fail closed.

The field is an observational copy of server-owned Task Domain authority. The D127 artifact does not grant that authority.

All metadata sequences are copied to immutable tuples.

---

## 12. Exact Task-Semantics Independence Invariant

D127 must explicitly prove all four combinations valid:

```text
troubleshooting + GENERAL_CHAT
troubleshooting + SOFTWARE_ENGINEERING
explanation     + GENERAL_CHAT
explanation     + SOFTWARE_ENGINEERING
```

Therefore no mapping table from Cognitive Intent to `AITaskKind` exists in D127.

---

## 13. `RuleBasedCognitiveIntentClassifier`

New canonical pure service:

```text
RuleBasedCognitiveIntentClassifier
```

Location:

```text
backend/app/services/cognitive_input_semantics.py
```

It must preserve existing `RuleBasedIntentClassifier` behavior without changing:

```text
rule order
keywords
explicit "A or B" comparison behavior
case-folding behavior
fallback behavior
Thai behavior
English behavior
```

Exact current priority remains:

```text
comparison
procedure
troubleshooting
summary
explanation
factual_lookup
general
```

Historical `app/services/reasoning.py` keeps `RuleBasedIntentClassifier` as compatibility alias or equivalent behavior-preserving wrapper.

---

## 14. Exact Required-Information Semantics

D127 centralizes only deterministic task-structure requirements.

Pure function:

```text
required_information_for_cognitive_intent(intent)
```

Exact outputs:

```text
general
    -> ("user_question",)

summary
    -> ("user_question",)

factual_lookup
    -> ("user_question", "document_evidence")

explanation
    -> ("user_question", "document_evidence")

procedure
    -> ("user_question", "document_evidence")

troubleshooting
    -> ("user_question", "document_evidence")

comparison
    -> (
         "user_question",
         "document_evidence",
         "comparison_basis",
       )
```

Existing `MissingInformationDetector` remains responsible for historical Reasoning evidence-gap behavior.

D132 later owns Brain-level uncertainty/insufficiency policy.

---

## 15. `CognitiveInteractionIntentMapper`

Pure compatibility mapper:

```text
CommandDecision.intent == chat_message -> chat
CommandDecision.intent == unknown      -> unknown
```

Malformed or unsupported values fail closed.

The mapper ignores provider preference, disposition, reason code, adapter selection, and task routing for Interaction Intent classification.

This proves provider-routing hints cannot alter D127 cognitive semantics.

---

## 16. `CognitivePerceptionAttentionProjector`

Pure deterministic service.

### 16.1 `project_perception`

Input:

```text
CognitiveArtifactEnvelope
Sequence[ContextCandidate]
```

Behavior:

1. validate exact Perception envelope;
2. enforce max candidate count;
3. require exact existing `ContextCandidate`;
4. preserve source identity and existing relevance;
5. assign 1-based rank in input order;
6. copy only metadata;
7. copy no candidate text;
8. perform no source read;
9. perform no dedupe;
10. perform no ranking/reorder.

### 16.2 `project_attention`

Input:

```text
CognitiveArtifactEnvelope
ContextBundle
```

Behavior:

1. validate exact Attention envelope;
2. require exact `ContextBundle`;
3. require bundle workspace == envelope workspace;
4. preserve `bundle.items` source order exactly;
5. copy source references only;
6. emit exact selection policy;
7. perform no retrieval;
8. perform no ranking;
9. perform no budget logic;
10. perform no provider/model selection.

---

## 17. `CognitiveTaskUnderstandingService`

Conceptual signature:

```text
understand(
    envelope,
    owner_request,
    interaction_intent,
    authoritative_ai_task_kind,
    *,
    information_gaps=(),
    constraints=(),
) -> CognitiveTaskDescription
```

Exact behavior:

1. require exact Task Understanding envelope;
2. require exact string Owner request;
3. normalize with `" ".join(owner_request.split())`;
4. reject empty normalized result;
5. reject normalized request over 16,384 UTF-8 bytes;
6. classify Cognitive Intent;
7. derive exact `required_information`;
8. copy structured `information_gaps`;
9. copy structured `constraints`;
10. preserve exact supplied `AITaskKind`;
11. construct immutable task description.

The service has no provider preference, provider, adapter, model, profile, route directive, execution plan, approval, or tool-permission parameter.

---

## 18. D126 Envelope Compatibility

All D127 artifacts reuse `CognitiveArtifactEnvelope`.

D127 creates no second provenance model.

D127 does not universally require non-null `context_snapshot_digest` because Perception/Attention/Task Understanding may legitimately exist before D129 final Context-freeze enforcement.

D127 validates producer organ, artifact type, contract version, workspace consistency, and its own fields only.

---

## 19. Historical Reasoning Compatibility Edits

### `backend/app/schemas/reasoning.py`

Only taxonomy ownership changes:

```text
ReasoningIntent = CognitiveIntent
```

`ReasoningPlan` field names and serialized values remain unchanged.

### `backend/app/services/reasoning.py`

Allowed compatibility changes only:

```text
import/reuse canonical D127 classifier
retain RuleBasedIntentClassifier historical name
reuse required_information_for_cognitive_intent()
```

The following remain unchanged:

```text
MissingInformationDetector evidence-gap behavior
EvidenceMapper behavior
ReasoningPlan structure
ReasoningContextBuilder semantics
provider behavior
persistence behavior
```

No D127 prompt rewrite is authorized.

---

## 20. Import / Dependency Boundaries

The new contract module may import only authority-neutral contracts/constants plus Python standard library.

Allowed application imports:

```text
app.contracts.cognitive_brain
app.contracts.context
app.contracts.task_aware_ai_routing
```

The new service module may import pure compatibility dependencies:

```text
app.contracts.cognitive_input_semantics
app.contracts.command_decision
app.contracts.context
app.contracts.context_resolution
app.services.context_sources
```

D127 modules must not depend on repositories, DB, provider SDKs, AIRuntime, ExecutionGuard, or ExecutionPlanner.

---

## 21. No Side Effects

Construction/classification/projection must not perform:

```text
network I/O
filesystem I/O
DB access
repository access
provider calls
AI calls
tool calls
connector calls
Git writes
Memory writes
Project writes
Conversation writes
```

D127 artifacts are ephemeral unless a later separately frozen milestone defines persistence.

---

## 22. Exact Scope Lifecycle

### 22.1 Design Freeze

Exactly one new docs file:

```text
NEW docs/specs/D127_PERCEPTION_ATTENTION_TASK_UNDERSTANDING_V1.md
```

No production/test file changes in the Design Freeze commit.

### 22.2 Implementation after freeze

Exactly six code/test files:

```text
NEW    backend/app/contracts/cognitive_input_semantics.py
NEW    backend/app/services/cognitive_input_semantics.py
MODIFY backend/app/schemas/reasoning.py
MODIFY backend/app/services/reasoning.py
NEW    backend/tests/test_d127_cognitive_input_semantics.py
NEW    backend/tests/test_d127_cognitive_input_semantics_security.py
```

The frozen D127 spec remains unchanged during implementation.

### 22.3 Total milestone

```text
7 repository files total
1 Design Freeze docs file
6 implementation code/test files
```

Any eighth total path requires STOP → exact dependency report → Owner review → amendment if justified.

---

## 23. Exact Functional Test Matrix

```text
F01 exact five Interaction Intent values
F02 exact seven Cognitive Intent values
F03 ReasoningIntent compatibility-equivalent to CognitiveIntent
F04 existing English classifier behavior unchanged
F05 existing Thai classifier behavior unchanged
F06 explicit "A or B" comparison behavior unchanged
F07 classifier fallback remains general
F08 classification deterministic

F09 valid PERSONAL Perception
F10 valid COMPANY Perception
F11 candidate rank exact 1..N
F12 None relevance preserved
F13 finite numeric relevance preserved
F14 candidate text absent from artifact
F15 duplicate source may appear at distinct Perception ranks
F16 Perception sequence copied immutably
F17 empty Perception valid

F18 valid PERSONAL Attention
F19 valid COMPANY Attention
F20 ContextBundle source order preserved
F21 exact selection policy emitted
F22 empty Attention valid
F23 selected source sequence copied immutably

F24 deterministic request normalization
F25 GENERAL_CHAT preserved exactly
F26 SOFTWARE_ENGINEERING preserved exactly
F27 troubleshooting + GENERAL_CHAT valid
F28 troubleshooting + SOFTWARE_ENGINEERING valid
F29 explanation + GENERAL_CHAT valid
F30 explanation + SOFTWARE_ENGINEERING valid
F31 general required-information exact
F32 summary required-information exact
F33 factual lookup required-information exact
F34 explanation required-information exact
F35 procedure required-information exact
F36 troubleshooting required-information exact
F37 comparison required-information exact
F38 constraints immutable/order-preserving
F39 information gaps immutable/order-preserving
F40 task description equality deterministic

F41 chat_message -> chat
F42 unknown -> unknown
F43 Local provider hint does not change Interaction Intent
F44 Cloud provider hint does not change Interaction Intent
F45 Automatic provider hint does not change Interaction Intent
F46 historical ReasoningPlan intent serialization unchanged
F47 historical Reasoning missing-information behavior unchanged
F48 historical ReasoningContextBuilder semantics unchanged
```

---

## 24. Exact Security Test Matrix

```text
S01 arbitrary Interaction Intent rejected
S02 wrong-case Interaction Intent rejected
S03 arbitrary Cognitive Intent rejected
S04 wrong-case Cognitive Intent rejected
S05 raw general_chat rejected as authoritative task kind
S06 raw software_engineering rejected as authoritative task kind
S07 troubleshooting rejected as authoritative task kind
S08 plugin target cannot create AITaskKind

S09 wrong Perception producer rejected
S10 wrong Perception artifact type rejected
S11 wrong Perception contract version rejected
S12 cross-workspace percept rejected
S13 non-ContextSourceRef rejected
S14 rank zero rejected
S15 negative rank rejected
S16 bool rank rejected
S17 rank gap/non-1..N rejected
S18 too many percepts rejected
S19 NaN relevance rejected
S20 infinite relevance rejected
S21 bool relevance rejected

S22 wrong Attention producer rejected
S23 wrong Attention artifact type rejected
S24 wrong Attention contract version rejected
S25 cross-workspace Attention source rejected
S26 duplicate Attention source rejected
S27 too many Attention sources rejected
S28 wrong selection policy rejected
S29 projector does not reorder ContextBundle

S30 wrong Task Understanding producer rejected
S31 wrong Task artifact type rejected
S32 wrong Task contract version rejected
S33 empty normalized request rejected
S34 over-limit normalized request rejected
S35 non-canonical whitespace rejected at contract boundary
S36 control-character request rejected
S37 invalid task metadata rejected
S38 duplicate task metadata rejected
S39 too many task metadata items rejected
S40 caller mutation cannot change stored tuples

S41 no owner_approval field
S42 no execution_authorization field
S43 no execution_plan field
S44 no provider/adapter/model/profile fields
S45 no api_key/credential/provider_secret field
S46 no raw_prompt/system_prompt/hidden reasoning/CoT field
S47 no tool_permission field
S48 no memory/project/repository write field
S49 contract construction has no network/DB/repository call
S50 projector performs no source read
S51 projector performs no Context resolution
S52 classifier performs no provider/network/DB call
S53 task understanding performs no provider/network/DB call
S54 no retry/fallback operation

S55 provider preference cannot change Cognitive Intent
S56 provider preference cannot change AITaskKind
S57 Cognitive Intent cannot change AITaskKind
S58 D104 exact task taxonomy unchanged
S59 D125 model/profile authority unchanged
S60 D126 task semantics version unchanged
```

---

## 25. Targeted Historical Regression

At minimum:

```text
Workspace contracts

D94 Context contracts/security
D95 Context resolver/security
D96 Context snapshot/security
D97 Context Chat integration/security

Command contracts
CommandDecision contracts/service
Command input pipeline
Chat Calendar intent

Reasoning
Planning
Decision

D104/D105 task-aware routing
D111 Brain runtime routing
D125 Local AI runtime profiles
D126 Cognitive Brain contracts/security

ExecutionGuard
AIRuntime
```

Exact filenames must be revalidated at implementation gate.

No historical test modification is pre-authorized. Any conflict means STOP and Owner review.

---

## 26. Acceptance Criteria

D127 is complete only when all applicable gates pass:

```text
Read-only reconciliation                          PASS
Draft 0.1 Owner A-F                              PASS
Draft 0.2 Owner Design Review                    PASS
D127 Design Freeze                               PASS

Design Freeze exact one-doc scope                PASS
Implementation exact six-file scope              PASS
Frozen D127 spec unchanged during implementation PASS

D127 functional tests                            PASS
D127 security tests                              PASS
Reasoning intent compatibility                   PASS
ReasoningPlan serialization compatibility        PASS
D95 Context compatibility                        PASS
D104/D105 routing compatibility                  PASS
D125 model/profile authority compatibility       PASS
D126 provenance compatibility                    PASS

Targeted historical regression                   PASS
Full backend regression                          PASS

No frontend production change                    PASS
No DB/migration change                           PASS
No API route change                              PASS
No ConversationService change                    PASS
No ContextResolver change                        PASS
No routing/profile authority change              PASS
No provider/AI call introduced                   PASS
No persistence introduced                        PASS
No retry/fallback introduced                     PASS

git diff --check                                 PASS
Exact local commit scope                         PASS
Working tree clean                               PASS
Owner guided acceptance                          PASS
Final push / remote freeze                       PASS
```

---

## 27. Guided Acceptance Shape

Contract/behavior inspection only, not UI acceptance.

Owner confirms:

```text
A. exact five Interaction Intent values
B. exact seven Cognitive Intent values
C. Perception contains safe source metadata, not copied Context text
D. Attention preserves D95-selected order and does not rank again
E. Cognitive Intent and AITaskKind are independent
F. Provider preference does not affect cognitive semantics
G. no provider/model/profile/execution authority in D127 artifacts
H. historical Reasoning behavior unchanged
```

---

## 28. Codex Budget

Default:

```text
CODEX = NO
```

Expected implementation:

```text
2 new pure modules
2 narrow compatibility edits
2 focused test modules
```

Codex becomes justified only if implementation review proves broad unexpected caller coupling around `ReasoningIntent`, `RuleBasedIntentClassifier`, or required-information derivation.

---

## 29. Final Owner Design Decisions - APPROVED

Owner-approved A–F remain unchanged.

Owner also approved G-J. The following final design decisions are frozen.

### G — Literal compatibility strategy

Approve exact `Literal` vocabularies for `CognitiveIntent` and `CognitiveInteractionIntent`, preserving historical string serialization.

**Owner decision:** APPROVED.

### H — Perception duplicate refinement

Approve:

```text
Perception may represent duplicate source identity at different candidate ranks.
D127 does not dedupe.
D95 remains dedupe/conflict authority.

Attention rejects duplicate selected source identity.
```

**Owner decision:** APPROVED.

### I — Exact numeric metadata limits

Approve:

```text
normalized request        16,384 bytes
task metadata item        128 bytes
task metadata collection  32 items
Perception refs            16,384 max
Attention refs             256 max
```

**Owner decision:** APPROVED.

### J — Freeze / implementation scope split

Approve:

```text
Design Freeze commit:
    exactly 1 NEW docs/spec file

Implementation phase:
    exactly 6 code/test files

Total D127 milestone:
    exactly 7 repository files
```

No eighth total path without Amendment review.

**Owner decision:** APPROVED.

---

## 30. Frozen Status

```text
D127 — PERCEPTION / ATTENTION / TASK UNDERSTANDING V1

READ-ONLY RECONCILIATION: COMPLETE

DRAFT 0.1:
OWNER DECISIONS A-F:      APPROVED

DRAFT 0.2:
EXACT CONTRACTS:          DEFINED
VALIDATION RULES:         DEFINED
FUNCTIONAL TEST MATRIX:   DEFINED
SECURITY TEST MATRIX:     DEFINED
OWNER REVIEW G-J:         APPROVED
OWNER DESIGN REVIEW:      PASS

DESIGN FREEZE:            FROZEN - OWNER APPROVED

IMPLEMENTATION:           NOT STARTED
CODE CHANGE:              NONE
COMMIT:                   DESIGN FREEZE COMMIT
PUSH:                     NOT PUSHED
CODEX USED:               NO
```
