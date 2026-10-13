# D130 — Structured Reasoning & Prediction V1

**Roadmap name:** Structured Reasoning & Prediction V1
**Status:** DESIGN FREEZE CANDIDATE — OWNER A-N APPROVED / REPOSITORY FREEZE PENDING
**Design revision:** Rev 0.1 — exact freeze candidate
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN
**D129 baseline:** COMPLETE / PUSHED / REMOTE VERIFIED
**D129 implementation commit:** `ecc80d1a5a362ec35ec6a7d81c6275dbf17f330d`
**Owner Design Review:** PASS — Decisions A-N APPROVED
**Implementation:** NOT STARTED
**Code change:** NONE
**Git commit:** NOT CREATED
**Git push:** NOT PUSHED
**Codex:** NOT USED

---

## 1. Purpose

D130 forms the Brain V1 **Structured Reasoning / Prediction** boundary by reconciling the existing deterministic `ReasoningService` / `ReasoningPlan` foundation with D126 Cognitive Brain provenance contracts, D127 Task Understanding, D129 frozen Context truth, and D128/D129 `CognitiveWorkingState`.

The governing rules are:

> **Reasoning is safe structured cognitive metadata, not hidden chain-of-thought.**

> **Prediction is advisory structured scenario metadata. Prediction is not Fact, Decision, Approval, Execution, or Owner authority.**

> **D130 cognition consumes the already frozen D129 Context truth. It performs no second Memory or Knowledge retrieval and no post-freeze Context refresh.**

> **D130 performs zero provider/model invocations. Model-assisted cognition remains behind the future D136 central authorized invocation boundary.**

D130 adds exactly two Brain-facing organ outputs:

```text
Reasoning
    -> CognitiveReasoningArtifact

Prediction / Simulation
    -> CognitivePredictionArtifact
```

D130 does not wire the live Cognitive Executive. D136 remains the integrated runtime milestone.

---

## 2. Owner Design Reconciliation A-N — APPROVED

### A — Preserve the existing Reasoning foundation

APPROVED:

`ReasoningService` and `ReasoningPlan` remain the canonical historical reasoning foundation.

D130 does not create a second Cognitive Intent classifier, required-information policy, or evidence-mapping subsystem.

D127 remains the canonical Brain Task Understanding taxonomy.

### B — New Brain-facing Reasoning artifact

APPROVED:

D130 introduces immutable `CognitiveReasoningArtifact`.

The artifact contains only safe structured reasoning metadata and bounded references.

It does not persist or expose:

```text
hidden chain-of-thought
scratchpad
token-by-token reasoning
provider prompt internals
system prompt
raw model trace
```

### C — Frozen Context only

APPROVED:

D130 deterministic Reasoning is derived from:

```text
D127 CognitiveTaskDescription
+
D129 CognitiveContextArtifact
+
existing snapshot-derived reasoning compatibility view
```

D130 performs no:

```text
MemoryResolver.resolve()
Knowledge retrieval
ContextResolver.resolve()
ContextSnapshot refresh
repository reread for reasoning evidence
```

after Context freeze.

### D — Evidence identity, not duplicated Context

APPROVED:

D130 Reasoning stores bounded evidence identities and source references.

It does not copy:

```text
Memory values
full Knowledge excerpts
full Conversation text
full Project Context
full ContextSnapshot text payloads
```

into a second cognitive representation.

### E — Extended structured reasoning remains declarative

APPROVED:

D130 supports bounded declarative reasoning categories:

```text
supported_fact
unknown
assumption
hypothesis
constraint
alternative
risk
inference
```

A structured statement is a safe result/claim summary, not a record of the internal process used to reach it.

`SUPPORTED_FACT` and `INFERENCE` statements require explicit evidence references.

`ASSUMPTION` and `HYPOTHESIS` are explicitly non-factual categories.

### F — New Prediction organ

APPROVED:

D130 introduces immutable `CognitivePredictionArtifact` and bounded `CognitivePredictionScenario` records.

Prediction may describe:

```text
alternative
expected_effect
risk
dependency
assumption
supporting evidence
uncertainty reasons
```

Prediction cannot select, approve, execute, rank, or commit an alternative.

### G — Prediction status is explicit

APPROVED:

D130 Prediction uses the existing D126 organ status vocabulary.

Valid D130 Prediction artifact statuses are exactly:

```text
READY
NOT_APPLICABLE
INSUFFICIENT
```

`FAILED` is represented by bounded service/runtime failure handling rather than a valid published D130 Prediction artifact.

The server-owned cognitive policy decides whether Prediction is required.

The model does not decide invocation policy.

### H — No fake precision

APPROVED:

D130 contains no field for:

```text
probability percentage
numeric confidence
calibrated score
success probability
certainty percentage
```

Prediction may carry qualitative `uncertainty_reasons`.

Brain-level confidence classes and "I do not know" behavior belong to D132.

### I — No direct model invocation

APPROVED:

D130 production code does not call:

```text
OpenAI
Ollama
AIAdapter
AIRuntime
ExecutionGuard
raw provider client
```

D130 adds no retry, provider fallback, model fallback, or model switching.

Future model-assisted population of D130 artifacts must enter through D136-authorized invocation and remain subject to the D130 contracts.

### J — Cognitive Working State integration

APPROVED:

`CognitiveWorkingState` gains optional slots:

```text
reasoning: CognitiveReasoningArtifact | None
prediction: CognitivePredictionArtifact | None
```

Reasoning requires Task + frozen Context.

Prediction requires Reasoning.

Both must match exact turn, workspace, and frozen Context digest.

Once attached, equal idempotent reassignment is permitted; different replacement or removal is rejected.

### K — Legacy IntelligenceContext is compatibility state, not second Brain truth

APPROVED:

Historical:

```text
IntelligenceContext.reasoning
```

remains untouched.

D130 does not auto-sync, overwrite, or treat the legacy nested value as canonical Brain state.

The canonical Brain-facing D130 result is the new immutable Cognitive artifact.

Normal Chat / Grounded Knowledge / legacy IntelligenceContext convergence remains D136 ownership.

### L — D131 boundary remains untouched

APPROVED:

D130 does not modify:

```text
PlanningService
PlanningPlan
DecisionService
DecisionAnalysis
GoalService
GoalAnalysis
```

Prediction may describe possible consequences or risks.

It does not choose an option or become Decision / Goal authority.

### M — No persistence / authority / runtime expansion

APPROVED:

D130 adds no:

```text
DB table
migration
repository write
Memory mutation
Project mutation
Conversation mutation
provider/model/profile selection
routing authority
Owner approval
tool permission
execution authority
frontend/API behavior
live ConversationService wiring
live ReasoningStep wiring
```

### N — Failure semantics stay within D126

APPROVED:

D130 adds no new Architecture-level failure code.

Malformed dependency/artifact/coherence failures map to:

```text
CognitiveFailureCode.CONTRACT_VIOLATION
```

Valid lack of predictive support is represented as:

```text
CognitiveOrganStatus.INSUFFICIENT
```

Prediction `NOT_APPLICABLE` is not a failure.

---

## 3. Reconciled Existing Ownership

### 3.1 D126 Brain provenance and failure vocabulary

D130 reuses:

```text
CognitiveArtifactEnvelope
CognitiveOrgan.REASONING
CognitiveOrgan.PREDICTION
CognitiveOrganStatus.READY
CognitiveOrganStatus.NOT_APPLICABLE
CognitiveOrganStatus.INSUFFICIENT
CognitiveFailureCode.CONTRACT_VIOLATION
```

No second Brain-wide envelope, organ enum, status enum, or failure enum is introduced.

### 3.2 D127 Task Understanding

D127 remains the canonical owner of:

```text
CognitiveInteractionIntent
CognitiveIntent
CognitiveTaskDescription
normalized_request
required_information
information_gaps
constraints
authoritative_ai_task_kind
```

D130 does not infer a new authoritative `AITaskKind`.

D130 does not change routing authority.

### 3.3 D129 Context truth

D129 remains the canonical owner of the one verified frozen Context truth:

```text
CognitiveContextArtifact.snapshot
CognitiveContextArtifact.envelope.context_snapshot_digest
```

D130 does not resolve or refresh Context.

### 3.4 Historical Reasoning foundation

The current historical foundation remains:

```text
app.schemas.reasoning.ReasoningPlan
app.schemas.reasoning.ReasoningEvidence
app.services.reasoning.ReasoningService
```

Current deterministic path:

```text
question
-> RuleBasedCognitiveIntentClassifier
-> required information
-> missing information
-> evidence map
-> ReasoningPlan
```

D130 reuses this foundation rather than replacing it.

### 3.5 D97 frozen-snapshot reasoning compatibility

D97 already provides:

```text
reasoning_evidence_from_snapshot(snapshot)
```

It derives Memory/Knowledge reasoning evidence only from the verified frozen snapshot.

D130 uses this read-only compatibility view for deterministic base reasoning.

### 3.6 Historical ReasoningStep

Historical `ReasoningStep` may call `MemoryResolver` directly when configured.

Therefore:

> **Historical `ReasoningStep` is not the canonical D130 Brain-facing reasoning path.**

D130 does not modify it.

D136 later owns live runtime convergence.

### 3.7 D128/D129 Working State

`CognitiveWorkingState` remains the canonical Brain mutable per-turn state.

D130 extends it narrowly with Reasoning and Prediction attachments.

---

## 4. Exact D130 Implementation Scope

The initial D130 implementation scope is frozen to exactly five code/test paths:

```text
NEW    backend/app/contracts/cognitive_reasoning_prediction.py
NEW    backend/app/services/cognitive_reasoning_prediction.py
MODIFY backend/app/intelligence/context/cognitive.py
NEW    backend/tests/test_d130_cognitive_reasoning_prediction.py
NEW    backend/tests/test_d130_cognitive_reasoning_prediction_security.py
```

No other production or test path is authorized without Owner amendment review.

Historical tests may not be modified under the initial D130 authorization.

Any required sixth implementation path means:

```text
STOP
-> dependency/conflict report
-> Owner amendment review
```

The Design Freeze specification itself is the sixth total milestone path:

```text
docs/specs/D130_STRUCTURED_REASONING_PREDICTION_V1.md
```

Thus after implementation the D130 milestone is expected to have exactly six D130 repository paths:

```text
1 frozen spec
5 code/test paths
```

---

## 5. Explicitly Unmodified Production Boundaries

Initial D130 implementation does not modify:

```text
backend/app/services/reasoning.py
backend/app/schemas/reasoning.py
backend/app/intelligence/steps/reasoning_step.py
backend/app/intelligence/context/intelligence.py
backend/app/services/conversations.py

backend/app/services/planning.py
backend/app/schemas/planning.py
backend/app/services/decision.py
backend/app/schemas/decision.py
backend/app/services/goals.py
backend/app/schemas/goals.py

AI routing
D125 profiles
ExecutionPlanner
ExecutionGuard
AIRuntime
AIAdapter
API routes
frontend
DB / ORM / migrations / repositories
```

A need to modify one of these paths during D130 implementation is a scope conflict and requires Owner amendment review.

---

## 6. Exact D130 Constants

`backend/app/contracts/cognitive_reasoning_prediction.py` defines:

```text
D130_REASONING_ARTIFACT_TYPE
    = "cognitive.reasoning"

D130_REASONING_CONTRACT_VERSION
    = "o-ai.cognitive-reasoning.v1"

D130_PREDICTION_ARTIFACT_TYPE
    = "cognitive.prediction"

D130_PREDICTION_CONTRACT_VERSION
    = "o-ai.cognitive-prediction.v1"

D130_REASONING_EVIDENCE_MAX_COUNT
    = 256

D130_REASONING_STATEMENT_MAX_COUNT
    = 64

D130_STATEMENT_TEXT_MAX_BYTES
    = 2048

D130_EVIDENCE_IDENTIFIER_MAX_BYTES
    = 512

D130_PREDICTION_SCENARIO_MAX_COUNT
    = 16

D130_PREDICTION_LIST_MAX_COUNT
    = 16

D130_PREDICTION_MISSING_SUPPORT_MAX_COUNT
    = 32

D130_PREDICTION_TEXT_MAX_BYTES
    = 2048
```

These are bounded structure limits, not cognitive quality scores.

---

## 7. Common D130 Text Rules

All D130 statement/scenario text fields that use D130 free-text rules must:

```text
be exact str
be non-empty
equal value.strip()
contain no Unicode Cc control character
fit the declared UTF-8 byte limit
```

D130 does not silently truncate text.

D130 does not normalize unsupported values into valid values.

Unknown / malformed input fails closed.

D127-owned metadata copied from `CognitiveTaskDescription` retains D127 validation semantics.

---

## 8. `CognitiveReasoningEvidenceRef`

Exact immutable contract:

```text
CognitiveReasoningEvidenceRef
├── evidence_id: str
├── source: ContextSourceRef
├── kind: "memory" | "document"
├── reference: str
├── label: str
└── version: int | None
```

### 8.1 Evidence ID

D130 deterministic base projection assigns:

```text
evidence-1
evidence-2
...
```

in the exact existing `ReasoningPlan.evidence_map` source order.

The ID is local to one `CognitiveReasoningArtifact`.

It is not a repository ID and grants no authority.

### 8.2 Source

`source` is an exact existing `ContextSourceRef`.

It proves which final frozen Context source admitted the evidence.

The source must match the artifact workspace.

### 8.3 Kind / version rules

Exact kinds:

```text
memory
document
```

For `memory`:

```text
version
    exact int
    bool rejected
    >= 1
```

For `document`:

```text
version == None
```

### 8.4 No content payload

The evidence reference contains no:

```text
Memory value
document excerpt
Context text
prompt
provider output
credential
```

---

## 9. `CognitiveReasoningStatement`

Exact immutable contract:

```text
CognitiveReasoningStatement
├── statement_id: str
├── kind: CognitiveReasoningStatementKind
├── summary: str
└── supporting_evidence_ids: tuple[str, ...]
```

Exact statement kinds:

```text
supported_fact
unknown
assumption
hypothesis
constraint
alternative
risk
inference
```

### 9.1 Evidence requirement

The following require at least one supporting evidence ID:

```text
supported_fact
inference
```

The following may have zero supporting evidence IDs because their kind itself marks them as non-established or structural:

```text
unknown
assumption
hypothesis
constraint
alternative
risk
```

Any referenced evidence ID must exist in the containing Reasoning artifact.

### 9.2 Safety semantics

A statement is:

```text
bounded declarative metadata
```

It is not:

```text
hidden step-by-step reasoning
private scratchpad
provider trace
proof of truth
authorization
```

---

## 10. `CognitiveReasoningArtifact`

Exact immutable contract:

```text
CognitiveReasoningArtifact
├── envelope: CognitiveArtifactEnvelope
├── intent: CognitiveIntent
├── normalized_request: str
├── required_information: tuple[str, ...]
├── information_gaps: tuple[str, ...]
├── constraints: tuple[str, ...]
├── evidence: tuple[CognitiveReasoningEvidenceRef, ...]
└── statements: tuple[CognitiveReasoningStatement, ...]
```

### 10.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.REASONING

artifact_type
    == "cognitive.reasoning"

contract_version
    == "o-ai.cognitive-reasoning.v1"

status
    == CognitiveOrganStatus.READY

context_snapshot_digest
    non-null
```

`model_binding_reference` remains provenance metadata only.

The deterministic D130 base projector requires it to be `None`.

A future D136-authorized model-assisted adapter may use the D126 model-binding reference under a separately frozen D136 runtime design without granting authority to the artifact.

### 10.2 Task-semantic fields

```text
intent
normalized_request
required_information
constraints
```

must be compatible with the attached D127 `CognitiveTaskDescription`.

D130 does not reinterpret them.

### 10.3 Information gaps

D130 deterministic base projection combines, in first-occurrence order:

```text
D127 task.information_gaps
+
existing ReasoningPlan.missing_information
```

Duplicates are removed without reordering the first occurrence.

No gap is treated as a fact.

### 10.4 Evidence ordering

Evidence order is deterministic and follows existing `ReasoningPlan.evidence_map` order.

Duplicate semantic evidence entries are rejected.

Duplicate `evidence_id` values are rejected.

### 10.5 Statement ordering

Statements preserve caller order.

Duplicate `statement_id` values are rejected.

Every supporting evidence ID must exist in the artifact.

---

## 11. Deterministic Base Reasoning Projector

Location:

```text
backend/app/services/cognitive_reasoning_prediction.py
```

Conceptual operation:

```text
project_reasoning(
    envelope: CognitiveArtifactEnvelope,
    task: CognitiveTaskDescription,
    context: CognitiveContextArtifact,
) -> CognitiveReasoningArtifact
```

The service may receive an existing `ReasoningService` dependency for testability, but it receives no repository, provider, adapter, runtime, or tool dependency.

### 11.1 Exact input coherence

Required:

```text
envelope.turn_id
    == task.envelope.turn_id
    == context.envelope.turn_id

envelope.workspace_id
    == task.envelope.workspace_id
    == context.envelope.workspace_id

envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest

task.envelope.context_snapshot_digest is None
    OR
task.envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest

envelope.model_binding_reference
    == None
```

### 11.2 Exact deterministic path

```text
snapshot = context.snapshot

historical_evidence =
    reasoning_evidence_from_snapshot(snapshot)

plan =
    ReasoningService.plan_from_evidence_map(
        task.normalized_request,
        historical_evidence,
    )
```

Then verify:

```text
plan.intent
    == task.cognitive_intent

plan.normalized_question
    == task.normalized_request

tuple(plan.required_information)
    == task.required_information
```

Any mismatch is a D130 contract failure.

### 11.3 Evidence/source binding

D130 pairs the snapshot-derived historical evidence with the exact final frozen Memory/Knowledge Context items in source order.

Each new `CognitiveReasoningEvidenceRef.source` must correspond to the final snapshot item from which the compatibility evidence was derived.

No external evidence may be injected by the deterministic base projector.

### 11.4 Deterministic base statements

The D130 deterministic base projector does not invent novel:

```text
facts
assumptions
hypotheses
alternatives
risks
inferences
```

Therefore its initial `statements` output is:

```text
()
```

The contract supports bounded structured statements so a later D136-authorized model-assisted path may populate them without redefining Brain semantics.

D130 itself performs no such model call.

---

## 12. `CognitivePredictionScenario`

Exact immutable contract:

```text
CognitivePredictionScenario
├── scenario_id: str
├── alternative: str
├── expected_effect: str
├── risks: tuple[str, ...]
├── dependencies: tuple[str, ...]
├── assumptions: tuple[str, ...]
├── supporting_evidence_ids: tuple[str, ...]
└── uncertainty_reasons: tuple[str, ...]
```

### 12.1 Scenario semantics

`alternative` identifies the scenario/option being simulated.

`expected_effect` is explicitly predictive.

It is not an established fact.

`risks`, `dependencies`, `assumptions`, and `uncertainty_reasons` are advisory descriptors.

### 12.2 Bounded list rules

Each list:

```text
risks
dependencies
assumptions
uncertainty_reasons
```

has maximum `D130_PREDICTION_LIST_MAX_COUNT`.

Items are non-empty bounded text.

Duplicates are rejected.

Order is preserved.

### 12.3 Evidence support

`supporting_evidence_ids`:

```text
maximum 32
unique
order preserved
```

When projected against a Reasoning artifact, every ID must exist in that Reasoning artifact.

A scenario may have zero evidence references only when its uncertainty/assumption metadata makes clear that it is not evidence-established.

D130 does not convert unsupported prediction into Fact.

### 12.4 Forbidden precision

No scenario has fields for:

```text
probability
confidence_score
certainty_percentage
rank
winner
selected
approved
execute
```

---

## 13. `CognitivePredictionArtifact`

Exact immutable contract:

```text
CognitivePredictionArtifact
├── envelope: CognitiveArtifactEnvelope
├── scenarios: tuple[CognitivePredictionScenario, ...]
└── missing_support: tuple[str, ...]
```

### 13.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.PREDICTION

artifact_type
    == "cognitive.prediction"

contract_version
    == "o-ai.cognitive-prediction.v1"

context_snapshot_digest
    non-null

status
    one of:
        READY
        NOT_APPLICABLE
        INSUFFICIENT
```

`model_binding_reference` is provenance metadata only and grants no model/runtime authority.

D130 performs no invocation regardless of its value.

### 13.2 Exact status cross-field rules

`READY`:

```text
1..16 scenarios
missing_support == ()
```

`NOT_APPLICABLE`:

```text
scenarios == ()
missing_support == ()
```

`INSUFFICIENT`:

```text
scenarios == ()
1..32 missing_support items
```

A `FAILED` envelope is rejected by this artifact contract.

---

## 14. Pure Prediction Projector

D130 exposes a pure projection/validation operation conceptually:

```text
project_prediction(
    envelope: CognitiveArtifactEnvelope,
    reasoning: CognitiveReasoningArtifact,
    scenarios: Sequence[CognitivePredictionScenario] = (),
    missing_support: Sequence[str] = (),
) -> CognitivePredictionArtifact
```

The envelope status determines the cross-field rule.

The projector validates:

```text
same turn
same workspace
same frozen Context digest
scenario evidence IDs belong to Reasoning evidence
```

It performs:

```text
no provider call
no model call
no routing
no fallback
no repository I/O
no Context reread
```

The projector does not decide whether Prediction is required for the task.

D136 server-owned cognitive policy owns that orchestration decision.

---

## 15. No Prediction Policy in D130

D130 freezes Prediction representation and coherence, not runtime stage policy.

Examples from Architecture remain guidance:

```text
simple factual lookup
    may be NOT_APPLICABLE

prediction-required task with inadequate support
    may be INSUFFICIENT

valid bounded scenario analysis
    may be READY
```

The exact per-task requirement matrix is D136 ownership.

A model cannot dynamically declare that Prediction should be skipped.

---

## 16. `CognitiveWorkingState` D130 Extension

`backend/app/intelligence/context/cognitive.py` gains:

```text
reasoning: CognitiveReasoningArtifact | None = None
prediction: CognitivePredictionArtifact | None = None
```

Existing D127-D129 fields remain unchanged.

### 16.1 Reasoning prerequisites

Reasoning may be attached only when:

```text
task is not None
context is not None
```

Memory Retrieval may be empty or absent; Reasoning is bound to the frozen Context, not to a second Memory read.

### 16.2 Reasoning identity checks

Required:

```text
reasoning.envelope.turn_id
    == binding.turn_id

reasoning.envelope.workspace_id
    == binding.workspace_id

reasoning.envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest
```

Task compatibility:

```text
reasoning.intent
    == task.cognitive_intent

reasoning.normalized_request
    == task.normalized_request

reasoning.required_information
    == task.required_information

reasoning.constraints
    == task.constraints

every task.information_gaps item
    appears in reasoning.information_gaps
```

Every Reasoning evidence source must be an exact source present in the frozen Context snapshot.

### 16.3 Prediction prerequisites

Prediction may be attached only when:

```text
reasoning is not None
context is not None
```

Required:

```text
prediction.envelope.turn_id
    == binding.turn_id

prediction.envelope.workspace_id
    == binding.workspace_id

prediction.envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest
```

Every scenario evidence ID must belong to the attached Reasoning artifact.

### 16.4 Freeze-style assignment

For each D130 field independently:

```text
None -> valid artifact
    allowed once

valid artifact -> equal artifact
    idempotent assignment allowed

valid artifact -> different artifact
    rejected

valid artifact -> None
    rejected
```

No refresh API is introduced.

---

## 17. Legacy `IntelligenceContext` Boundary

D130 does not add a `prediction` field to historical:

```text
backend/app/intelligence/context/intelligence.py
```

and does not rewrite:

```text
context.intelligence.reasoning
```

when Brain-facing Reasoning is attached.

This avoids creating silent dual-write behavior.

D136 will reconcile the live historical intelligence pipeline and canonical Brain Working State.

---

## 18. Hidden Chain-of-Thought Boundary

D130 must not persist, return, log, or expose raw hidden reasoning.

Allowed examples:

```text
statement kind = supported_fact
summary = "The configured limit is unavailable in the admitted evidence."
supporting_evidence_ids = ("evidence-2",)

statement kind = assumption
summary = "This scenario assumes the dependency remains available."
```

Forbidden examples:

```text
"First I thought X, then I considered Y..."
token-by-token reasoning transcript
internal scratchpad
provider hidden reasoning
system/developer prompt reconstruction
```

Tests inspect contract fields and module source to ensure no raw hidden-reasoning persistence surface is introduced.

---

## 19. Prediction Is Not Fact or Decision

D130 freezes these distinctions:

```text
Prediction != Fact
Prediction != Decision
Prediction != Recommendation authority
Prediction != Approval
Prediction != Execution Plan
Prediction != Project Action Plan
```

A `READY` Prediction artifact means:

```text
the prediction structure is contract-valid
```

It does not mean:

```text
the predicted outcome is true
the alternative should be selected
the Owner approved it
execution may proceed
```

---

## 20. Model / Provider Boundary

D130 production modules must not import or instantiate:

```text
OpenAI SDK
Ollama client
AIAdapter implementation
AIRuntime
ExecutionGuard
ExecutionPlanner
provider endpoint
credential loader
```

There is no:

```text
model retry
provider fallback
model fallback
hidden inference loop
```

Architecture model-call topology remains future D136 runtime ownership.

---

## 21. Persistence Boundary

D130 adds no persistence.

Forbidden D130 production additions:

```text
database table
ORM model
migration
repository
reasoning artifact store
prediction artifact store
Memory write
Experience write
Conversation write
Project write
```

Reasoning and Prediction remain ephemeral Working State by default.

---

## 22. Authority Boundary

D130 artifacts grant no:

```text
authentication
authorization
Owner approval
routing authority
provider selection
model selection
profile selection
credential access
tool permission
execution permission
Project mutation
Memory mutation
Conversation mutation
```

No artifact may be supplied as execution authorization evidence.

---

## 23. D131 / D132 / D136 Ownership Boundaries

D131 owns:

```text
Cognitive Planning
Decision / Goal cognitive integration
canonical sequencing after Prediction
```

D132 owns:

```text
Brain-level uncertainty
confidence classes
limited / insufficient / unknown behavior
"I do not know" behavior
```

D136 owns:

```text
Cognitive Executive
runtime stage ordering
task policy for Prediction applicability
authorized model invocation
model-assisted cognition
turn deadlines / stage budgets
late-result enforcement
Normal Chat / Grounded Knowledge convergence
```

D130 must not pre-implement these milestones.

---

## 24. D130 Contract Failure

D130 service-level coherence failures use:

```text
CognitiveReasoningPredictionContractError
    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

Examples:

```text
wrong turn
wrong workspace
wrong Context digest
wrong producer organ
wrong artifact type/version
Reasoning before Task/Context
Prediction before Reasoning
Reasoning evidence outside frozen snapshot
Prediction evidence ID outside Reasoning
invalid prediction status cross-fields
```

`INSUFFICIENT` Prediction is not an exception.

It is a valid cognitive result.

---

## 25. Functional Test Matrix

Frozen functional matrix for:

```text
backend/tests/test_d130_cognitive_reasoning_prediction.py
```

| ID | Test |
|---|---|
| F01 | exact D130 artifact type/version constants are exposed |
| F02 | valid Memory `CognitiveReasoningEvidenceRef` constructs |
| F03 | valid document `CognitiveReasoningEvidenceRef` constructs |
| F04 | evidence input collections normalize to immutable tuples where applicable |
| F05 | valid `supported_fact` statement with evidence constructs |
| F06 | valid `inference` statement with evidence constructs |
| F07 | valid `unknown` statement without evidence constructs |
| F08 | valid `assumption` statement without evidence constructs |
| F09 | valid `hypothesis` statement without evidence constructs |
| F10 | valid `constraint` statement without evidence constructs |
| F11 | valid `alternative` statement without evidence constructs |
| F12 | valid `risk` statement without evidence constructs |
| F13 | valid Reasoning READY envelope constructs artifact |
| F14 | Reasoning preserves exact CognitiveIntent |
| F15 | Reasoning preserves normalized request |
| F16 | Reasoning required-information order is preserved |
| F17 | Reasoning information-gap order is preserved |
| F18 | Reasoning constraints order is preserved |
| F19 | Reasoning evidence order is preserved |
| F20 | Reasoning statement order is preserved |
| F21 | deterministic base projector accepts D127 Task + D129 Context |
| F22 | deterministic base projector uses existing `plan_from_evidence_map` |
| F23 | deterministic base projector preserves Task intent |
| F24 | deterministic base projector preserves Task normalized request |
| F25 | deterministic base projector preserves Task required information |
| F26 | deterministic base projector combines Task gaps + ReasoningPlan missing gaps in first-occurrence order |
| F27 | deterministic base projector copies Task constraints |
| F28 | deterministic base projector assigns `evidence-1..N` in source order |
| F29 | deterministic base projector binds each evidence entry to a frozen snapshot source |
| F30 | deterministic base projector emits no invented statements |
| F31 | empty Memory/Knowledge evidence is valid Reasoning with expected gaps |
| F32 | READY Prediction with one scenario constructs |
| F33 | READY Prediction preserves multiple scenario order |
| F34 | READY Prediction preserves risk/dependency/assumption order |
| F35 | READY Prediction preserves qualitative uncertainty reasons |
| F36 | NOT_APPLICABLE Prediction with empty scenarios/support constructs |
| F37 | INSUFFICIENT Prediction with missing support constructs |
| F38 | pure Prediction projector accepts same-turn/same-workspace/same-digest Reasoning |
| F39 | pure Prediction projector validates scenario evidence IDs against Reasoning |
| F40 | model-binding reference remains metadata only when present in a manually constructed valid envelope |
| F41 | Working State accepts Reasoning after Task + Context |
| F42 | Working State allows equal idempotent Reasoning assignment |
| F43 | Working State accepts READY Prediction after Reasoning |
| F44 | Working State accepts NOT_APPLICABLE Prediction after Reasoning |
| F45 | Working State accepts INSUFFICIENT Prediction after Reasoning |
| F46 | Working State allows equal idempotent Prediction assignment |
| F47 | D127-D129 Working State fields remain intact with D130 fields present |
| F48 | legacy `intelligence.reasoning` is not mutated by Brain Reasoning attachment |
| F49 | Reasoning/Prediction construction and projection perform no persistence |
| F50 | Reasoning/Prediction services are deterministic for equal inputs |

Exact functional method marker expectation:

```text
test_f01_...
through
test_f50_...
```

Exactly 50 functional test methods.

---

## 26. Security Test Matrix

Frozen security matrix for:

```text
backend/tests/test_d130_cognitive_reasoning_prediction_security.py
```

| ID | Test |
|---|---|
| S01 | Reasoning wrong producer organ rejected |
| S02 | Reasoning wrong artifact type rejected |
| S03 | Reasoning wrong contract version rejected |
| S04 | Reasoning non-READY status rejected |
| S05 | Reasoning missing Context digest rejected |
| S06 | evidence arbitrary kind rejected |
| S07 | Memory evidence without positive exact-int version rejected |
| S08 | Memory evidence bool version rejected |
| S09 | document evidence with version rejected |
| S10 | evidence empty ID rejected |
| S11 | evidence oversized ID/reference/label rejected |
| S12 | evidence control-character text rejected |
| S13 | duplicate evidence IDs rejected |
| S14 | duplicate semantic evidence rejected |
| S15 | too many evidence entries rejected |
| S16 | statement arbitrary kind rejected |
| S17 | statement empty ID rejected |
| S18 | statement empty summary rejected |
| S19 | statement oversized summary rejected |
| S20 | statement control-character summary rejected |
| S21 | duplicate statement IDs rejected |
| S22 | too many statements rejected |
| S23 | supported_fact without evidence rejected |
| S24 | inference without evidence rejected |
| S25 | statement unknown evidence ID rejected |
| S26 | duplicate statement evidence IDs rejected |
| S27 | caller sequence mutation cannot mutate Reasoning tuples |
| S28 | deterministic projector rejects wrong Task type |
| S29 | deterministic projector rejects wrong Context type |
| S30 | deterministic projector rejects wrong turn |
| S31 | deterministic projector rejects wrong workspace |
| S32 | deterministic projector rejects wrong Context digest |
| S33 | deterministic projector rejects conflicting non-null Task digest |
| S34 | deterministic projector rejects model-bound envelope in deterministic base path |
| S35 | deterministic projector rejects ReasoningPlan intent conflict |
| S36 | deterministic projector rejects normalized-request conflict |
| S37 | deterministic projector rejects required-information conflict |
| S38 | deterministic projector cannot inject evidence outside frozen snapshot |
| S39 | deterministic projector performs no `MemoryResolver` call |
| S40 | deterministic projector performs no Knowledge retrieval |
| S41 | deterministic projector performs no Context re-resolution |
| S42 | deterministic projector performs no provider/network call |
| S43 | deterministic projector performs no DB/repository call |
| S44 | Prediction wrong producer organ rejected |
| S45 | Prediction wrong artifact type rejected |
| S46 | Prediction wrong contract version rejected |
| S47 | Prediction missing Context digest rejected |
| S48 | Prediction FAILED status rejected |
| S49 | Prediction arbitrary status rejected |
| S50 | READY with zero scenarios rejected |
| S51 | READY with missing_support rejected |
| S52 | NOT_APPLICABLE with scenarios rejected |
| S53 | NOT_APPLICABLE with missing_support rejected |
| S54 | INSUFFICIENT with scenario rejected |
| S55 | INSUFFICIENT without missing_support rejected |
| S56 | too many Prediction scenarios rejected |
| S57 | duplicate scenario IDs rejected |
| S58 | scenario empty/oversized/control-character text rejected |
| S59 | scenario duplicate risk/dependency/assumption/uncertainty item rejected |
| S60 | scenario list-count overflow rejected |
| S61 | scenario duplicate evidence IDs rejected |
| S62 | Prediction projector rejects wrong turn/workspace/digest |
| S63 | Prediction projector rejects scenario evidence outside Reasoning |
| S64 | Reasoning attachment before Task rejected |
| S65 | Reasoning attachment before Context rejected |
| S66 | Working State rejects Reasoning turn/workspace/digest mismatch |
| S67 | Working State rejects Reasoning task semantic mismatch |
| S68 | Working State rejects Reasoning evidence source outside frozen Context |
| S69 | different Reasoning replacement rejected |
| S70 | Reasoning removal after freeze rejected |
| S71 | Prediction before Reasoning rejected |
| S72 | Working State rejects Prediction turn/workspace/digest mismatch |
| S73 | Working State rejects Prediction evidence outside Reasoning |
| S74 | different Prediction replacement rejected |
| S75 | Prediction removal after freeze rejected |
| S76 | contract has no probability/confidence-score field |
| S77 | contract has no rank/winner/selected field |
| S78 | contract has no approval/execution field |
| S79 | contract has no raw prompt/system prompt/hidden-CoT field |
| S80 | contract has no raw Context/Memory value field |
| S81 | production modules import no OpenAI/Ollama/provider client |
| S82 | production modules import no AIRuntime/ExecutionGuard/ExecutionPlanner |
| S83 | production modules add no persistence/repository dependency |
| S84 | production modules add no retry/fallback behavior |
| S85 | D130 does not modify legacy `ReasoningService` source |
| S86 | D130 does not modify Planning/Decision/Goal production sources |
| S87 | D130 does not modify ConversationService/API/frontend |
| S88 | D130 does not expand routing/profile authority |

Exact security method marker expectation:

```text
test_s01_...
through
test_s88_...
```

Exactly 88 security test methods.

---

## 27. Exact Targeted Historical Regression Set

Before full backend regression, D130 runs exactly these 40 historical files:

```text
backend/tests/test_context_contract.py
backend/tests/test_context_resolution_contract.py
backend/tests/test_context_resolver.py
backend/tests/test_context_provenance_contract.py
backend/tests/test_context_snapshot.py
backend/tests/test_context_snapshot_persistence.py
backend/tests/test_context_chat.py
backend/tests/test_context_aware_chat_integration.py
backend/tests/test_d94_context_security.py
backend/tests/test_d95_context_resolution_security.py
backend/tests/test_d96_context_snapshot_security.py
backend/tests/test_d97_context_chat_security.py
backend/tests/test_personal_memory.py
backend/tests/test_memory_aware_chat.py
backend/tests/test_conversation_memory.py
backend/tests/test_project_context.py
backend/tests/test_execution_context.py
backend/tests/test_pipeline.py
backend/tests/test_knowledge_pipeline_regression.py
backend/tests/test_conversation_dependency_wiring.py
backend/tests/test_d126_cognitive_brain_core_contracts.py
backend/tests/test_d126_cognitive_brain_core_contracts_security.py
backend/tests/test_d127_cognitive_input_semantics.py
backend/tests/test_d127_cognitive_input_semantics_security.py
backend/tests/test_d128_cognitive_working_state.py
backend/tests/test_d128_cognitive_working_state_security.py
backend/tests/test_d129_cognitive_context_memory.py
backend/tests/test_d129_cognitive_context_memory_security.py
backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
backend/tests/test_d105_task_aware_ai_routing_integration.py
backend/tests/test_d105_task_aware_ai_routing_security.py
backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py
backend/tests/test_reasoning.py
backend/tests/test_planning.py
backend/tests/test_decision.py
backend/tests/test_goals.py
```

No historical test modification is authorized.

After targeted regression, run complete:

```text
backend/tests
```

---

## 28. Validation Sequence

D130 implementation validation order is frozen as:

```text
1. Exact baseline / scope / content-hash gate
2. D130 focused functional tests — exactly 50
3. D130 focused security tests — exactly 88
4. Exact 40-file targeted historical regression
5. Full backend regression
6. Final exact scope/hashes/spec verification
7. Owner Guided Acceptance
8. Separate local implementation commit authorization
9. Separate normal push authorization
10. Independent remote verification
```

A failed gate is diagnosed from current state.

Batch mutation is never blindly reapplied.

No reset/rebase/force remediation is implicit.

---

## 29. Owner Guided Acceptance Targets

D130 Owner Guided Acceptance verifies at least:

```text
A. Reasoning uses frozen Context only.
B. No post-freeze Memory/Knowledge reread exists.
C. Reasoning output is structured metadata, not hidden chain-of-thought.
D. Reasoning evidence refers only to final frozen Context sources.
E. Prediction is explicitly not Fact.
F. Prediction is explicitly not Decision/Approval/Execution.
G. NOT_APPLICABLE and INSUFFICIENT are bounded valid Prediction outcomes.
H. No numeric confidence/probability is introduced.
I. No provider/model call is introduced in D130.
J. CognitiveWorkingState freezes Reasoning/Prediction against replacement.
K. Planning/Decision/Goal and legacy IntelligenceContext remain unchanged.
L. No persistence/routing/authority/API/frontend/runtime expansion occurs.
```

---

## 30. Scope Expansion Rule

If implementation requires any sixth code/test path:

```text
STOP
    ↓
identify exact dependency/conflict
    ↓
Owner review
    ↓
D130 Amendment if justified
    ↓
freeze amendment
    ↓
resume
```

No implicit scope expansion is authorized.

---

## 31. Codex Budget Policy

Frozen:

```text
CODEX = NO
```

Reason:

```text
two isolated new production modules
one bounded Working State modification
two focused test modules
no live runtime wiring
no caller migration
no broad refactor
```

Codex requires a new explicit Owner decision.

---

## 32. D130 Acceptance Criteria

D130 is complete only when all applicable gates pass:

```text
Owner Design Reconciliation A-N                 PASS
D130 Design Freeze                              PASS
Exact 5-path implementation scope               PASS
Functional D130 tests — 50/50                  PASS
Security D130 tests — 88/88                    PASS
Exact 40-file targeted regression               PASS
Full backend regression                         PASS
No historical test modification                 PASS
No legacy ReasoningService modification         PASS
No Planning/Decision/Goal modification          PASS
No ConversationService/API/frontend change      PASS
No DB/migration/persistence change              PASS
No routing/profile authority change             PASS
No provider/model invocation                    PASS
No post-freeze Context/Memory reread             PASS
No hidden chain-of-thought persistence          PASS
No numeric prediction confidence/probability    PASS
git diff --check                                PASS
Exact implementation commit scope               PASS
Working tree clean                              PASS
Owner Guided Acceptance                         PASS
Normal non-force push                           PASS
Independent remote verification                 PASS
```

---

## 33. Explicit Non-Goals / Future Ownership

```text
Planning / Decision / Goal cognitive integration  -> D131
Metacognition / uncertainty / confidence classes  -> D132
Critic / Publication Gate                         -> D133
Experience / Learning boundary                    -> D134
Model capability knowledge                        -> D135
Cognitive Executive / model-assisted runtime      -> D136
Newborn Brain integration / security / Birth      -> D137
```

D130 also excludes:

```text
Browser autonomy
tool autonomy
workflow autonomy
automatic provider/model fallback
autonomous Memory mutation
autonomous experience promotion
self-modifying code
background cognitive loops
```

---

## 34. Current Freeze Candidate Status

```text
D130 — STRUCTURED REASONING & PREDICTION V1

READ-ONLY DISCOVERY:          COMPLETE
DESIGN RECONCILIATION A-N:   OWNER APPROVED
DESIGN FREEZE CONTENT:       PREPARED — REV 0.1
REPOSITORY DESIGN FREEZE:    PENDING

IMPLEMENTATION:              NOT STARTED
CODE CHANGE:                 NONE
CODEX USED:                  NO
COMMIT:                      NONE
PUSH:                        NONE

BASELINE:
ecc80d1a5a362ec35ec6a7d81c6275dbf17f330d
```

---

**End of D130 Structured Reasoning & Prediction V1 — Design Freeze Candidate**
