# D131 — Planning / Decision Cognitive Integration V1

**Roadmap name:** Planning / Decision Cognitive Integration V1
**Status:** DESIGN FREEZE CANDIDATE — OWNER A–N APPROVED / REPOSITORY FREEZE PENDING
**Design revision:** Rev 0.1 — exact freeze candidate
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN
**D130 baseline:** COMPLETE / PUSHED / REMOTE VERIFIED
**D130 Design Freeze commit:** `a9de51f99134c7b3b1dd9c0974c78a72b1bbe467`
**D130 implementation commit / exact D131 parent baseline:** `5c6a646f3ec7f18dc6bbb93669a17924658c99f9`
**Owner Design Review:** PASS — Decisions A–N APPROVED
**Implementation:** NOT STARTED
**Code change:** NONE
**Git commit:** NOT CREATED
**Git push:** NOT PUSHED
**Codex:** NOT USED

---

## 1. Purpose

D131 forms the Brain V1 **Cognitive Planning / Decision & Goal** boundary by reconciling the existing deterministic `PlanningService` / `PlanningPlan`, `DecisionService` / `DecisionAnalysis`, and `GoalService` / `GoalAnalysis` foundations with D126 Cognitive Brain provenance contracts, D130 Structured Reasoning / Prediction, and D128-D130 `CognitiveWorkingState`.

The governing rules are:

> **Cognitive Planning is safe response-organization metadata. It is not an executable workflow, approval, schedule, or proof that work has been completed.**

> **Decision metadata may expose alternatives and trade-offs, but it never ranks, scores, selects, approves, or executes an alternative on behalf of the Owner.**

> **Goal / Project output is candidate metadata only. D131 does not create, persist, activate, schedule, or execute a Goal or Project.**

> **D131 consumes the already frozen D130 Reasoning / Prediction chain. It performs no Context, Memory, Knowledge, provider, model, persistence, routing, or execution I/O.**

> **D131 performs zero provider/model invocations. Model-assisted cognition remains behind the future D136 central authorized invocation boundary.**

D131 adds exactly two Brain-facing organ outputs:

```text
Cognitive Planning
    -> CognitivePlanningArtifact

Decision / Goal
    -> CognitiveDecisionGoalArtifact
```

The canonical Brain sequence frozen by D131 is:

```text
D127 Task Understanding
        ↓
D129 Frozen Context / Memory
        ↓
D130 Structured Reasoning
        ↓
D130 Prediction
        ↓
D131 Cognitive Planning
        ↓
D131 Decision / Goal
        ↓
D132 Metacognition / Uncertainty
```

D131 does not wire the live Cognitive Executive. D136 remains the integrated runtime milestone.

---

## 2. Owner Design Reconciliation A–N — APPROVED

### A — Preserve the existing Planning / Decision / Goal foundations

APPROVED:

`PlanningService` / `PlanningPlan`, `DecisionService` / `DecisionAnalysis`, and `GoalService` / `GoalAnalysis` remain the canonical historical deterministic foundations.

D131 does not create a second planning algorithm, alternative parser, decision-ranking engine, goal parser, or project-activation subsystem.

### B — New Brain-facing Cognitive Planning artifact

APPROVED:

D131 introduces immutable `CognitivePlanningArtifact` plus bounded immutable planning child records.

The artifact is safe non-operational metadata only.

It does not contain hidden chain-of-thought, tool commands, execution steps, schedule authority, approval, or proof of completion.

### C — New Brain-facing Decision / Goal artifact

APPROVED:

D131 introduces immutable `CognitiveDecisionGoalArtifact` plus bounded immutable alternative, trade-off, Goal-candidate, and Project-candidate records.

The artifact is explanatory metadata only.

It grants no decision, approval, project, persistence, tool, or execution authority.

### D — Canonical sequencing after Prediction

APPROVED:

D131 freezes this order:

```text
Reasoning
-> Prediction
-> Cognitive Planning
-> Decision / Goal
```

Planning requires a valid same-turn D130 Reasoning artifact and a valid same-turn D130 Prediction artifact.

Decision / Goal requires valid same-turn Reasoning, Prediction, and Cognitive Planning artifacts.

Prediction status may be `READY`, `NOT_APPLICABLE`, or `INSUFFICIENT`; D131 treats Prediction as an upstream sequencing/coherence dependency, not as selection or execution authority.

### E — Planning uses existing PlanningService

APPROVED:

The deterministic D131 Planning projector constructs a compatibility `ReasoningPlan` from the already-frozen D130 `CognitiveReasoningArtifact`, then calls the existing:

```text
PlanningService.plan(reasoning_plan)
```

D131 does not perform a second Reasoning classification or Context read.

### F — Decision / Goal uses existing services

APPROVED:

The deterministic D131 Decision / Goal projector reconstructs safe compatibility inputs from D130 Reasoning and D131 Cognitive Planning, then calls the existing:

```text
DecisionService.analyze(reasoning_plan, planning_plan)
GoalService.analyze(reasoning_plan, planning_plan, decision_analysis)
```

D131 does not create a second alternative parser, decision status policy, Goal parser, or Project parser.

### G — Evidence identity only

APPROVED:

D131 Decision evidence is represented only by D130 `evidence_id` references.

D131 does not duplicate:

```text
Memory values
document excerpts
Context text
Conversation text
Project Context text
provider prompts
provider output
```

The deterministic Decision / Goal projector maps historical `DecisionAnalysis.evidence_map` entries back to exact D130 evidence IDs by semantic identity.

### H — Planning remains non-executable

APPROVED:

Planning phases, tasks, dependencies, risks, and information gaps are response-organization metadata only.

They do not mean:

```text
work is approved
work is scheduled
work has started
work has completed
a tool may execute
an external side effect is authorized
```

### I — Decision remains Owner-controlled

APPROVED:

D131 never selects a winning alternative.

It contains no:

```text
rank
winner
selected
score
weight
probability
numeric confidence
auto recommendation
auto approval
```

`owner_decision_required` means exactly that the Owner remains the decision authority.

### J — Goal / Project remains candidate-only

APPROVED:

D131 Goal / Project output is candidate metadata derived from the existing deterministic `GoalService`.

D131 does not:

```text
create a persisted Goal
create a persisted Project
activate a Goal
change a Project
schedule work
write Calendar state
invoke a tool
claim progress or completion
```

### K — Working State integration

APPROVED:

`CognitiveWorkingState` gains optional slots:

```text
planning: CognitivePlanningArtifact | None
decision_goal: CognitiveDecisionGoalArtifact | None
```

Planning requires Reasoning + Prediction + frozen Context.

Decision / Goal requires Reasoning + Prediction + Planning + frozen Context.

All artifacts must match exact turn, workspace, and frozen Context digest.

Once attached, equal idempotent reassignment is permitted; different replacement or removal is rejected.

### L — Historical objects remain compatibility state

APPROVED:

Historical `PlanningPlan`, `DecisionAnalysis`, `GoalAnalysis`, and legacy `IntelligenceContext` remain compatibility structures.

D131 does not auto-sync or overwrite legacy nested state.

Canonical Brain-facing D131 truth is the new immutable Cognitive artifacts.

Live Chat / Grounded Knowledge / legacy IntelligenceContext convergence remains D136 ownership.

### M — No persistence / authority / runtime expansion

APPROVED:

D131 adds no:

```text
DB table
migration
repository write
Memory mutation
Project mutation
Conversation mutation
Calendar mutation
provider/model/profile selection
routing authority
Owner approval
tool permission
execution authority
frontend/API behavior
live ConversationService wiring
live Cognitive Executive wiring
```

### N — Failure semantics stay within D126

APPROVED:

D131 adds no new Architecture-level failure code.

Malformed dependency/artifact/coherence failures map to:

```text
CognitiveFailureCode.CONTRACT_VIOLATION
```

Valid Decision / Goal insufficiency is represented as:

```text
CognitiveOrganStatus.INSUFFICIENT
```

`NOT_APPLICABLE` is a valid result, not a failure.

---

## 3. Reconciled Existing Ownership

### 3.1 D126 Brain provenance and organ vocabulary

D131 reuses:

```text
CognitiveArtifactEnvelope
CognitiveOrgan.COGNITIVE_PLANNING
CognitiveOrgan.DECISION_GOAL
CognitiveOrganStatus.READY
CognitiveOrganStatus.NOT_APPLICABLE
CognitiveOrganStatus.INSUFFICIENT
CognitiveFailureCode.CONTRACT_VIOLATION
```

No second Brain-wide envelope, organ enum, status enum, or failure enum is introduced.

### 3.2 D130 Reasoning / Prediction

D130 remains canonical owner of:

```text
CognitiveReasoningArtifact
CognitiveReasoningEvidenceRef
CognitivePredictionArtifact
CognitivePredictionScenario
```

D131 does not modify or reinterpret D130 contract semantics.

D131 Planning consumes D130 Reasoning semantically and requires D130 Prediction as the frozen upstream sequencing/coherence dependency.

D131 Decision / Goal consumes D130 Reasoning plus D131 Planning; D130 Prediction remains a required same-turn upstream dependency but grants no selection authority.

### 3.3 Historical Planning foundation

The existing deterministic Planning foundation remains:

```text
app.schemas.planning.PlanningPlan
app.schemas.planning.PlanningPhase
app.schemas.planning.PlanningTask
app.schemas.planning.PlanningDependency
app.schemas.planning.PlanningRisk
app.services.planning.PlanningService
```

Existing Planning is response organization only.

Stable historical plan-kind mapping remains:

```text
general          -> response_organization
factual_lookup   -> response_organization
explanation      -> response_organization
summary          -> response_organization
procedure        -> procedure_outline
comparison       -> comparison_structure
troubleshooting  -> troubleshooting_structure
```

Historical approved Planning missing-information codes remain exactly:

```text
no_retrieved_context
no_document_evidence
comparison_basis
```

### 3.4 Historical Decision foundation

The existing deterministic Decision foundation remains:

```text
app.schemas.decision.DecisionAnalysis
app.schemas.decision.DecisionAlternative
app.schemas.decision.DecisionTradeOff
app.services.decision.DecisionService
```

Historical recommendation statuses remain exactly:

```text
not_applicable
insufficient_information
owner_decision_required
```

Historical Decision never ranks, scores, or selects an alternative.

Historical deterministic alternative cap remains eight.

### 3.5 Historical Goal / Project foundation

The existing deterministic Goal / Project foundation remains:

```text
app.schemas.goals.GoalAnalysis
app.schemas.goals.Goal
app.schemas.goals.Project
app.services.goals.GoalService
```

Historical Goal states remain exactly:

```text
candidate
not_applicable
```

`candidate` means explicit text was recognized; no object was created.

### 3.6 D128-D130 Working State

`CognitiveWorkingState` remains the canonical Brain mutable per-turn state.

D131 extends it narrowly with Planning and Decision / Goal attachments.

---

## 4. Exact D131 Implementation Scope

The initial D131 implementation scope is frozen to exactly five code/test paths:

```text
NEW    backend/app/contracts/cognitive_planning_decision_goal.py
NEW    backend/app/services/cognitive_planning_decision_goal.py
MODIFY backend/app/intelligence/context/cognitive.py
NEW    backend/tests/test_d131_cognitive_planning_decision_goal.py
NEW    backend/tests/test_d131_cognitive_planning_decision_goal_security.py
```

No other production or test path is authorized without Owner amendment review.

Historical tests may not be modified under the initial D131 authorization.

Any required sixth implementation path means:

```text
STOP
-> dependency/conflict report
-> Owner amendment review
```

The Design Freeze specification itself is the sixth total milestone path:

```text
docs/specs/D131_PLANNING_DECISION_COGNITIVE_INTEGRATION_V1.md
```

Thus after implementation the D131 milestone is expected to have exactly six D131 repository paths:

```text
1 frozen spec
5 code/test paths
```

---

## 5. Explicitly Unmodified Production Boundaries

Initial D131 implementation does not modify:

```text
backend/app/contracts/cognitive_brain.py
backend/app/contracts/cognitive_reasoning_prediction.py
backend/app/services/cognitive_reasoning_prediction.py

backend/app/services/reasoning.py
backend/app/schemas/reasoning.py
backend/app/services/planning.py
backend/app/schemas/planning.py
backend/app/services/decision.py
backend/app/schemas/decision.py
backend/app/services/goals.py
backend/app/schemas/goals.py

backend/app/intelligence/steps/reasoning_step.py
backend/app/intelligence/context/intelligence.py
backend/app/services/conversations.py

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

A need to modify one of these paths during D131 implementation is a scope conflict and requires Owner amendment review.

---

## 6. Exact D131 Constants

`backend/app/contracts/cognitive_planning_decision_goal.py` defines:

```text
D131_PLANNING_ARTIFACT_TYPE
    = "cognitive.planning"

D131_PLANNING_CONTRACT_VERSION
    = "o-ai.cognitive-planning.v1"

D131_DECISION_GOAL_ARTIFACT_TYPE
    = "cognitive.decision_goal"

D131_DECISION_GOAL_CONTRACT_VERSION
    = "o-ai.cognitive-decision-goal.v1"

D131_IDENTIFIER_MAX_BYTES
    = 512

D131_TEXT_MAX_BYTES
    = 2048

D131_PLANNING_PHASE_MAX_COUNT
    = 16

D131_PLANNING_TASK_MAX_COUNT
    = 64

D131_PLANNING_DEPENDENCY_MAX_COUNT
    = 128

D131_PLANNING_RISK_MAX_COUNT
    = 32

D131_MISSING_INFORMATION_MAX_COUNT
    = 32

D131_DECISION_ALTERNATIVE_MAX_COUNT
    = 8

D131_DECISION_CRITERION_MAX_COUNT
    = 16

D131_DECISION_TRADE_OFF_MAX_COUNT
    = 128

D131_DECISION_EVIDENCE_MAX_COUNT
    = 256

D131_GOAL_CANDIDATE_MAX_COUNT
    = 16

D131_PROJECT_CANDIDATE_MAX_COUNT
    = 16

D131_DECISION_ALTERNATIVE_LABEL_MAX_CHARS
    = 120

D131_CANDIDATE_TITLE_MAX_CHARS
    = 160
```

These are bounded structure limits, not cognitive quality scores.

---

## 7. Common D131 Text / Collection Rules

All D131 free-text fields subject to D131 validation must:

```text
be exact str
be non-empty
equal value.strip()
contain no Unicode Cc control character
fit the declared UTF-8 byte limit
```

D131 does not silently truncate or normalize malformed values into valid values.

Unknown / malformed input fails closed.

All public collection fields are normalized to immutable tuples.

Duplicate IDs, duplicate semantic edges, duplicate criteria, duplicate evidence IDs, and duplicate candidate IDs are rejected where applicable.

---

## 8. Cognitive Planning Child Contracts

### 8.1 `CognitivePlanningPhase`

```text
CognitivePlanningPhase
├── id: str
└── title: str
```

`id` is unique inside one Planning artifact.

### 8.2 `CognitivePlanningTask`

```text
CognitivePlanningTask
├── id: str
├── phase_id: str
└── description: str
```

Every task must reference an existing phase.

### 8.3 `CognitivePlanningDependency`

```text
CognitivePlanningDependency
├── task_id: str
└── depends_on: str
```

Required invariants:

```text
both task references exist
no self-dependency
no duplicate edge
task ordering is topological
```

### 8.4 `CognitivePlanningRisk`

```text
CognitivePlanningRisk
├── code: str
└── description: str
```

`code` must be one of the exact approved historical Planning information-gap codes:

```text
no_retrieved_context
no_document_evidence
comparison_basis
```

Risk codes must exactly match Planning `missing_information` in the same order.

---

## 9. `CognitivePlanningArtifact`

Exact immutable contract:

```text
CognitivePlanningArtifact
├── envelope: CognitiveArtifactEnvelope
├── intent: CognitiveIntent
├── plan_kind: CognitivePlanKind
├── phases: tuple[CognitivePlanningPhase, ...]
├── tasks: tuple[CognitivePlanningTask, ...]
├── dependencies: tuple[CognitivePlanningDependency, ...]
├── risks: tuple[CognitivePlanningRisk, ...]
└── missing_information: tuple[str, ...]
```

`CognitivePlanKind` exact values:

```text
response_organization
procedure_outline
comparison_structure
troubleshooting_structure
```

### 9.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.COGNITIVE_PLANNING

artifact_type
    == "cognitive.planning"

contract_version
    == "o-ai.cognitive-planning.v1"

status
    == CognitiveOrganStatus.READY

context_snapshot_digest
    non-null
```

The immutable contract may carry a D126 `model_binding_reference` only as provenance metadata.

The deterministic D131 base projector requires:

```text
model_binding_reference == None
```

### 9.2 Plan-kind mapping

`plan_kind` must match `intent` by the exact existing historical mapping.

### 9.3 Missing-information rules

Planning `missing_information` contains only the exact approved historical Planning codes.

Order preserves first occurrence.

No duplicate code is allowed.

Planning risks must correspond one-for-one, in the same order, to `missing_information`.

### 9.4 Graph validation

The artifact validates:

```text
unique phase IDs
unique task IDs
valid task -> phase references
unique dependency edges
valid task references in dependencies
no self-dependency
topological task ordering
```

---

## 10. Deterministic Planning Compatibility Projection

Location:

```text
backend/app/services/cognitive_planning_decision_goal.py
```

Conceptual operation:

```text
project_planning(
    envelope: CognitiveArtifactEnvelope,
    reasoning: CognitiveReasoningArtifact,
    prediction: CognitivePredictionArtifact,
) -> CognitivePlanningArtifact
```

### 10.1 Exact upstream coherence

Required:

```text
envelope.turn_id
    == reasoning.envelope.turn_id
    == prediction.envelope.turn_id

envelope.workspace_id
    == reasoning.envelope.workspace_id
    == prediction.envelope.workspace_id

envelope.context_snapshot_digest
    == reasoning.envelope.context_snapshot_digest
    == prediction.envelope.context_snapshot_digest

reasoning.envelope.context_snapshot_digest
    non-null

prediction status
    in {READY, NOT_APPLICABLE, INSUFFICIENT}

envelope.model_binding_reference
    == None
```

Prediction content does not authorize, rank, or alter the historical Planning algorithm in D131 V1.

### 10.2 Compatibility `ReasoningPlan`

D131 creates an in-memory historical compatibility value only:

```text
ReasoningPlan(
    intent=reasoning.intent,
    normalized_question=reasoning.normalized_request,
    required_information=list(reasoning.required_information),
    missing_information=list(reasoning.information_gaps),
    evidence_map=[
        ReasoningEvidence(
            kind=item.kind,
            reference=item.reference,
            label=item.label,
            version=item.version,
        )
        for item in reasoning.evidence
    ],
)
```

No Context, Memory, Knowledge, repository, or provider read occurs.

### 10.3 Existing PlanningService call

Exact base call:

```text
planning_plan = PlanningService.plan(reasoning_plan)
```

The returned value must be a valid `PlanningPlan` and must match D130 Reasoning intent.

Every historical Planning missing-information code must already exist in D130 Reasoning `information_gaps`.

The projector then creates an immutable `CognitivePlanningArtifact` preserving historical order exactly.

---

## 11. Decision / Goal Child Contracts

### 11.1 `CognitiveDecisionAlternative`

```text
CognitiveDecisionAlternative
├── id: str
└── label: str
```

Alternative labels are capped at the historical 120-character Decision boundary.

Alternative order is source order.

### 11.2 `CognitiveDecisionTradeOff`

```text
CognitiveDecisionTradeOff
├── alternative_id: str
├── criterion: str
└── description: str
```

Every trade-off must reference an existing alternative.

The pair:

```text
(alternative_id, criterion)
```

must be unique.

Trade-offs are advisory only and contain no score or ranking.

### 11.3 `CognitiveGoalCandidate`

```text
CognitiveGoalCandidate
├── id: str
└── title: str
```

Title is capped at the historical 160-character Goal boundary.

A candidate is not a persisted or active Goal.

### 11.4 `CognitiveProjectCandidate`

```text
CognitiveProjectCandidate
├── id: str
└── title: str
```

Title is capped at the historical 160-character Project boundary.

A candidate is not a persisted or active Project.

---

## 12. `CognitiveDecisionGoalArtifact`

Exact immutable contract:

```text
CognitiveDecisionGoalArtifact
├── envelope: CognitiveArtifactEnvelope
├── intent: CognitiveIntent
├── alternatives: tuple[CognitiveDecisionAlternative, ...]
├── evaluation_criteria: tuple[str, ...]
├── trade_offs: tuple[CognitiveDecisionTradeOff, ...]
├── supporting_evidence_ids: tuple[str, ...]
├── recommendation_status: RecommendationStatus
├── goals: tuple[CognitiveGoalCandidate, ...]
├── projects: tuple[CognitiveProjectCandidate, ...]
├── goal_status: GoalState
└── missing_information: tuple[str, ...]
```

Exact `RecommendationStatus` values:

```text
not_applicable
insufficient_information
owner_decision_required
```

Exact `GoalState` values:

```text
candidate
not_applicable
```

### 12.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.DECISION_GOAL

artifact_type
    == "cognitive.decision_goal"

contract_version
    == "o-ai.cognitive-decision-goal.v1"

context_snapshot_digest
    non-null

status
    in {READY, NOT_APPLICABLE, INSUFFICIENT}
```

`FAILED` is not a valid published D131 Decision / Goal artifact.

The immutable contract may carry a D126 `model_binding_reference` only as provenance metadata.

The deterministic D131 base projector requires:

```text
model_binding_reference == None
```

### 12.2 Decision alternative rules

Historical semantics are retained exactly:

```text
owner_decision_required
    requires >= 2 alternatives
    requires missing_information == ()

insufficient_information
    requires >= 2 alternatives
    requires missing_information != ()

not_applicable
    requires < 2 alternatives
```

No alternative is selected.

### 12.3 Evidence rules

`supporting_evidence_ids` contains only D130 Reasoning evidence IDs.

The artifact contains no duplicated `ReasoningEvidence` value and no Context content.

All IDs are unique and order-preserving.

### 12.4 Goal / Project rules

```text
goal_status == candidate
    iff at least one Goal or Project candidate exists

goal_status == not_applicable
    iff goals == () and projects == ()
```

### 12.5 Exact organ-status resolution

D131 freezes the following deterministic precedence:

```text
if recommendation_status == insufficient_information:
    expected organ status = INSUFFICIENT

elif recommendation_status == owner_decision_required:
    expected organ status = READY

elif goal_status == candidate:
    expected organ status = READY

else:
    expected organ status = NOT_APPLICABLE
```

Therefore:

> **Decision insufficiency takes precedence over Goal / Project candidate readiness.**

This is an organ-level completeness rule only. It does not invalidate a recognized candidate.

---

## 13. Deterministic Decision / Goal Compatibility Projection

Location:

```text
backend/app/services/cognitive_planning_decision_goal.py
```

Conceptual operation:

```text
project_decision_goal(
    envelope: CognitiveArtifactEnvelope,
    reasoning: CognitiveReasoningArtifact,
    prediction: CognitivePredictionArtifact,
    planning: CognitivePlanningArtifact,
) -> CognitiveDecisionGoalArtifact
```

### 13.1 Exact upstream coherence

Required:

```text
same turn
same workspace
same frozen Context digest
same CognitiveIntent between Reasoning and Planning
valid D130 Prediction status
```

The supplied Decision / Goal envelope status must equal the deterministic status derived from the historical Decision / Goal outputs.

The deterministic base projector requires:

```text
envelope.model_binding_reference == None
```

### 13.2 Compatibility inputs

D131 reconstructs a temporary historical `ReasoningPlan` from D130 Reasoning exactly as defined in section 10.2.

D131 reconstructs a temporary historical `PlanningPlan` from the immutable Cognitive Planning artifact preserving exact phase/task/dependency/risk/missing-information order.

These are in-memory compatibility values only.

### 13.3 Existing Decision / Goal calls

Exact base calls:

```text
decision_analysis =
    DecisionService.analyze(reasoning_plan, planning_plan)

goal_analysis =
    GoalService.analyze(
        reasoning_plan,
        planning_plan,
        decision_analysis,
    )
```

### 13.4 Evidence-ID mapping

Each historical `DecisionAnalysis.evidence_map` entry is matched to one D130 `CognitiveReasoningEvidenceRef` by exact semantic identity:

```text
(kind, reference, label, version)
```

The resulting Brain-facing Decision evidence is the corresponding D130 `evidence_id` only.

Any unmatched, ambiguous, reordered-incoherent, or invented Decision evidence fails closed as `CONTRACT_VIOLATION`.

### 13.5 Goal / Project projection

Historical Goal and Project candidates are copied into immutable candidate records preserving ID, title, and source order.

No persistence or activation occurs.

---

## 14. Prediction Interaction Boundary

D131 V1 does not treat D130 Prediction as Fact, Decision, or authority.

Prediction is required before Planning to freeze sequencing and coherence.

Exact rule:

```text
Prediction READY
Prediction NOT_APPLICABLE
Prediction INSUFFICIENT
```

are all valid upstream inputs to D131 if they are contract-valid and match turn/workspace/digest.

D131 V1 does not:

```text
convert a Prediction scenario into a selected alternative
rank Prediction scenarios
copy Prediction probability/confidence
block Planning solely because Prediction is NOT_APPLICABLE
block Planning solely because Prediction is INSUFFICIENT
promote Prediction into evidence
```

D132 remains responsible for Brain-level uncertainty behavior.

---

## 15. Cognitive Working State Integration

`backend/app/intelligence/context/cognitive.py` adds:

```text
planning: CognitivePlanningArtifact | None = None
decision_goal: CognitiveDecisionGoalArtifact | None = None
```

### 15.1 Planning attachment prerequisites

Planning attachment requires:

```text
context is present
reasoning is present
prediction is present
```

Required consistency:

```text
planning.turn_id == binding.turn_id
planning.workspace_id == binding.workspace_id
planning.context_digest == frozen context digest
planning.intent == reasoning.intent
planning.missing_information is an ordered subset of reasoning.information_gaps
```

### 15.2 Decision / Goal attachment prerequisites

Decision / Goal attachment requires:

```text
context is present
reasoning is present
prediction is present
planning is present
```

Required consistency:

```text
decision_goal.turn_id == binding.turn_id
decision_goal.workspace_id == binding.workspace_id
decision_goal.context_digest == frozen context digest
decision_goal.intent == reasoning.intent == planning.intent
decision_goal.missing_information == planning.missing_information
all decision supporting_evidence_ids exist in reasoning.evidence
```

### 15.3 Freeze / reassignment behavior

For both new slots:

```text
None -> valid artifact
    allowed

same equal artifact -> same equal artifact
    allowed

different artifact replacement
    rejected

artifact -> None removal
    rejected
```

Existing upstream D128-D130 freeze behavior remains unchanged.

---

## 16. Legacy Compatibility Boundary

D131 does not modify:

```text
IntelligenceContext.reasoning
historical provider prompt composition
historical PlanningContextBuilder
historical DecisionContextBuilder
historical GoalContextBuilder
```

Attaching D131 Brain artifacts does not mutate legacy Intelligence state.

D136 later owns live runtime convergence.

---

## 17. Determinism

For equal validated inputs, deterministic D131 base projectors must return equal Brain artifacts apart from caller-supplied envelope provenance fields that are themselves equal inputs.

D131 performs no:

```text
random sampling
time-based policy branching
provider call
model call
network lookup
repository lookup
retry loop
fallback
```

---

## 18. Model / Provider Boundary

D131 production modules must not import or instantiate:

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
model switching
hidden inference loop
```

Future model-assisted D131 artifact population, if separately approved, must enter through D136-authorized invocation and remain subject to the immutable D131 contracts.

---

## 19. Persistence Boundary

D131 adds no persistence.

Forbidden D131 production additions:

```text
database table
ORM model
migration
repository
Planning artifact store
Decision artifact store
Goal artifact store
Memory write
Experience write
Conversation write
Project write
Calendar write
```

Planning and Decision / Goal remain ephemeral Working State by default.

---

## 20. Authority Boundary

D131 artifacts grant no:

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
Goal activation
Memory mutation
Conversation mutation
Calendar mutation
```

No Planning task, Decision alternative, Goal candidate, or Project candidate may be supplied as execution authorization evidence.

---

## 21. D132 / D133 / D136 Ownership Boundaries

D132 owns:

```text
Brain-level uncertainty
confidence classes
limited / insufficient / unknown behavior
"I do not know" behavior
```

D133 owns:

```text
Verification / Critic
Publication Gate
response-quality acceptance / rejection
```

D136 owns:

```text
Cognitive Executive
runtime stage ordering
central authorized model invocation
model-assisted cognition
turn deadlines / stage budgets
late-result enforcement
Normal Chat / Grounded Knowledge convergence
side-effect handoff to approved execution systems
```

D131 must not pre-implement these milestones.

---

## 22. D131 Contract Failure

D131 service-level coherence failures use:

```text
CognitivePlanningDecisionGoalContractError
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
Planning before Reasoning
Planning before Prediction
Decision / Goal before Planning
Planning intent mismatch
Decision / Goal intent mismatch
Planning missing-information outside Reasoning gaps
Decision evidence outside D130 Reasoning
malformed planning graph
wrong Decision / Goal envelope status
historical service output type mismatch
invented historical evidence mapping
```

Valid `INSUFFICIENT` and `NOT_APPLICABLE` Decision / Goal results are not exceptions.

---

## 23. Functional Test Matrix — EXACTLY 50

Frozen functional matrix for:

```text
backend/tests/test_d131_cognitive_planning_decision_goal.py
```

| ID | Test |
|---|---|
| F01 | exact D131 artifact type/version and structural constants are exposed |
| F02 | valid `CognitivePlanningPhase` constructs |
| F03 | valid `CognitivePlanningTask` constructs |
| F04 | valid `CognitivePlanningDependency` constructs |
| F05 | valid `CognitivePlanningRisk` constructs |
| F06 | valid READY `CognitivePlanningArtifact` constructs |
| F07 | Planning collection inputs normalize to immutable tuples |
| F08 | general intent maps to `response_organization` |
| F09 | procedure intent maps to `procedure_outline` |
| F10 | comparison intent maps to `comparison_structure` |
| F11 | troubleshooting intent maps to `troubleshooting_structure` |
| F12 | Planning phase order is preserved |
| F13 | Planning task order is preserved |
| F14 | Planning dependency order is preserved |
| F15 | Planning risk / missing-information order is preserved |
| F16 | Planning projector accepts D130 Reasoning + READY Prediction |
| F17 | Planning projector accepts D130 NOT_APPLICABLE Prediction |
| F18 | Planning projector accepts D130 INSUFFICIENT Prediction |
| F19 | Planning projector calls existing `PlanningService.plan` |
| F20 | compatibility `ReasoningPlan` preserves D130 intent / request / required information |
| F21 | compatibility `ReasoningPlan` maps D130 evidence in exact source order |
| F22 | compatibility `ReasoningPlan` carries D130 information gaps before historical Planning normalization |
| F23 | Cognitive Planning projection mirrors historical `PlanningPlan` exactly |
| F24 | Planning projection is deterministic for equal inputs |
| F25 | Working State accepts Planning after Reasoning + Prediction |
| F26 | Working State allows equal idempotent Planning assignment |
| F27 | valid `CognitiveDecisionAlternative` constructs |
| F28 | valid `CognitiveDecisionTradeOff` constructs |
| F29 | valid `CognitiveGoalCandidate` constructs |
| F30 | valid `CognitiveProjectCandidate` constructs |
| F31 | READY Decision / Goal artifact with `owner_decision_required` constructs |
| F32 | INSUFFICIENT Decision / Goal artifact constructs |
| F33 | NOT_APPLICABLE Decision / Goal artifact constructs |
| F34 | READY Goal-only candidate artifact constructs |
| F35 | READY Project-only candidate artifact constructs |
| F36 | Decision / Goal collection inputs normalize to immutable tuples |
| F37 | Decision / Goal projector accepts full coherent upstream chain |
| F38 | Decision / Goal projector calls existing `DecisionService.analyze` |
| F39 | Decision / Goal projector calls existing `GoalService.analyze` |
| F40 | Decision alternative order is preserved |
| F41 | evaluation-criteria order is preserved |
| F42 | trade-off order is preserved |
| F43 | historical Decision evidence maps to exact D130 evidence IDs |
| F44 | historical recommendation status is preserved |
| F45 | historical Goal candidate is preserved |
| F46 | historical Project candidate is preserved |
| F47 | Decision insufficiency takes precedence over candidate readiness for organ status |
| F48 | Working State accepts Decision / Goal after Planning |
| F49 | Working State allows equal idempotent Decision / Goal assignment |
| F50 | D131 attachments leave D128-D130 artifacts and legacy Intelligence compatibility state unchanged |

Exact functional method marker expectation:

```text
test_f01_...
through
test_f50_...
```

Exactly 50 functional test methods.

---

## 24. Security Test Matrix — EXACTLY 88

Frozen security matrix for:

```text
backend/tests/test_d131_cognitive_planning_decision_goal_security.py
```

| ID | Test |
|---|---|
| S01 | Planning wrong producer organ rejected |
| S02 | Planning wrong artifact type rejected |
| S03 | Planning wrong contract version rejected |
| S04 | Planning non-READY status rejected |
| S05 | Planning missing Context digest rejected |
| S06 | arbitrary Planning `plan_kind` rejected |
| S07 | Planning `plan_kind` / intent mismatch rejected |
| S08 | Planning phase invalid empty/oversized/control-character text rejected |
| S09 | duplicate Planning phase IDs rejected |
| S10 | too many Planning phases rejected |
| S11 | Planning task invalid text rejected |
| S12 | duplicate Planning task IDs rejected |
| S13 | Planning task unknown phase rejected |
| S14 | too many Planning tasks rejected |
| S15 | duplicate Planning dependency edge rejected |
| S16 | Planning dependency unknown task rejected |
| S17 | Planning self-dependency rejected |
| S18 | non-topological Planning dependency rejected |
| S19 | too many Planning dependencies rejected |
| S20 | Planning risk invalid text/code rejected |
| S21 | duplicate Planning risk codes rejected |
| S22 | too many Planning risks rejected |
| S23 | Planning arbitrary missing-information code rejected |
| S24 | duplicate Planning missing-information code rejected |
| S25 | Planning risks / missing-information code sequence mismatch rejected |
| S26 | too many Planning missing-information codes rejected |
| S27 | caller sequence mutation cannot mutate Planning tuples |
| S28 | Planning projector rejects wrong Reasoning type |
| S29 | Planning projector rejects wrong Prediction type |
| S30 | Planning projector rejects wrong turn |
| S31 | Planning projector rejects wrong workspace |
| S32 | Planning projector rejects wrong Context digest |
| S33 | Planning projector rejects incoherent Reasoning / Prediction provenance |
| S34 | deterministic Planning projector rejects model-bound envelope |
| S35 | Planning projector rejects non-`PlanningPlan` historical service output |
| S36 | Planning projector rejects historical Planning intent conflict |
| S37 | Planning projector rejects historical missing-information outside D130 Reasoning gaps |
| S38 | malformed historical Planning graph fails closed as contract violation |
| S39 | Planning projector performs no `MemoryResolver` call |
| S40 | Planning projector performs no Knowledge retrieval or Context resolution |
| S41 | Planning projector performs no provider/network call |
| S42 | Planning projector performs no DB/repository call |
| S43 | D131 production modules add no retry/fallback behavior |
| S44 | D131 production modules import no AIRuntime/ExecutionGuard/ExecutionPlanner |
| S45 | Decision / Goal wrong producer organ rejected |
| S46 | Decision / Goal wrong artifact type rejected |
| S47 | Decision / Goal wrong contract version rejected |
| S48 | Decision / Goal missing Context digest rejected |
| S49 | Decision / Goal FAILED status rejected |
| S50 | Decision / Goal arbitrary status rejected |
| S51 | READY Decision / Goal with neither applicable decision nor candidate rejected |
| S52 | NOT_APPLICABLE with applicable owner decision rejected |
| S53 | NOT_APPLICABLE with Goal / Project candidate rejected |
| S54 | INSUFFICIENT without `insufficient_information` decision rejected |
| S55 | READY with `insufficient_information` decision rejected |
| S56 | Decision alternative invalid empty/oversized/control-character text rejected |
| S57 | duplicate Decision alternative IDs rejected |
| S58 | too many Decision alternatives rejected |
| S59 | evaluation criterion invalid/duplicate/count-overflow rejected |
| S60 | Decision trade-off invalid text rejected |
| S61 | duplicate Decision trade-off pair rejected |
| S62 | Decision trade-off unknown alternative rejected |
| S63 | too many Decision trade-offs rejected |
| S64 | supporting evidence ID invalid/duplicate/count-overflow rejected |
| S65 | `owner_decision_required` with fewer than two alternatives rejected |
| S66 | `insufficient_information` with fewer than two alternatives rejected |
| S67 | `insufficient_information` without missing information rejected |
| S68 | `owner_decision_required` with missing information rejected |
| S69 | Goal candidate invalid/duplicate/count-overflow rejected |
| S70 | Project candidate invalid/duplicate/count-overflow rejected |
| S71 | Goal state `candidate` without Goal / Project candidate rejected |
| S72 | Goal state `not_applicable` with candidate rejected |
| S73 | Decision / Goal missing-information invalid/duplicate/count-overflow rejected |
| S74 | caller sequence mutation cannot mutate Decision / Goal tuples |
| S75 | Decision / Goal projector rejects wrong Planning type |
| S76 | Decision / Goal projector rejects wrong turn/workspace/digest |
| S77 | Decision / Goal projector rejects incoherent Reasoning / Prediction / Planning intent or provenance |
| S78 | deterministic Decision / Goal projector rejects model-bound envelope |
| S79 | Decision / Goal projector rejects non-`DecisionAnalysis` historical Decision output |
| S80 | Decision / Goal projector rejects non-`GoalAnalysis` or incoherent Goal output |
| S81 | Decision evidence outside D130 Reasoning fails closed |
| S82 | Working State rejects Planning before Reasoning or Prediction |
| S83 | Working State rejects Planning mismatch, replacement, or removal |
| S84 | Working State rejects Decision / Goal before Planning, mismatch, replacement, or removal |
| S85 | D131 contracts contain no rank/winner/selected/score/probability/confidence/approval/execution/raw-prompt/hidden-CoT fields |
| S86 | D131 production modules import no provider client, persistence repository, ORM, or network dependency |
| S87 | D131 does not modify historical Reasoning / Planning / Decision / Goal / D130 production sources |
| S88 | D131 does not expand ConversationService/API/frontend/routing/profile/execution authority |

Exact security method marker expectation:

```text
test_s01_...
through
test_s88_...
```

Exactly 88 security test methods.

---

## 25. Exact Targeted Historical Regression Set — 42 FILES

Before full backend regression, D131 runs exactly these 42 historical files:

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
backend/tests/test_d130_cognitive_reasoning_prediction.py
backend/tests/test_d130_cognitive_reasoning_prediction_security.py
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

## 26. Validation Sequence

D131 implementation validation order is frozen as:

```text
1. Exact baseline / scope / content-hash gate
2. D131 focused functional tests — exactly 50
3. D131 focused security tests — exactly 88
4. Exact 42-file targeted historical regression
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

## 27. Owner Guided Acceptance Targets

D131 Owner Guided Acceptance verifies at least:

```text
A. Planning occurs only after same-turn Reasoning + Prediction.
B. Planning reuses existing PlanningService and does not create a second algorithm.
C. Planning is non-executable metadata only.
D. Prediction status does not become selection or execution authority.
E. Decision / Goal occurs only after coherent Planning.
F. Decision reuses existing DecisionService and never ranks/scores/selects an option.
G. Decision evidence references only D130 evidence IDs.
H. owner_decision_required leaves the Owner as authority.
I. Goal / Project reuses existing GoalService and remains candidate-only.
J. Decision insufficiency maps to INSUFFICIENT and takes precedence over candidate readiness.
K. Working State freezes Planning and Decision / Goal against replacement/removal.
L. No Context/Memory/Knowledge reread occurs.
M. No provider/model invocation, retry, or fallback occurs.
N. No persistence/routing/API/frontend/execution authority expands.
O. Historical Planning/Decision/Goal/D130 sources remain unchanged.
```

---

## 28. Scope Expansion Rule

If implementation requires any sixth code/test path:

```text
STOP
    ↓
identify exact dependency/conflict
    ↓
Owner review
    ↓
D131 Amendment if justified
    ↓
freeze amendment
    ↓
resume
```

No implicit scope expansion is authorized.

---

## 29. Dependency Policy

Expected new dependency requirement:

```text
NONE
```

D131 must use the standard library and existing project dependencies only.

If implementation requires a new package:

```text
STOP
-> DEPENDENCY DESIGN DECISION REQUIRED
```

---

## 30. Codex Budget Policy

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
no provider/model integration
no broad refactor
```

Codex requires a new explicit Owner decision.

---

## 31. D131 Acceptance Criteria

D131 is complete only when all applicable gates pass:

```text
Owner Design Reconciliation A-N                    PASS
D131 Design Freeze                                 PASS
Exact 5-path implementation scope                  PASS
Functional D131 tests — 50/50                     PASS
Security D131 tests — 88/88                       PASS
Exact 42-file targeted regression                  PASS
Full backend regression                            PASS
No historical test modification                    PASS
No historical Reasoning modification               PASS
No historical Planning modification                PASS
No historical Decision modification                PASS
No historical Goal modification                    PASS
No D130 contract/service modification              PASS
No ConversationService/API/frontend change         PASS
No DB/migration/persistence change                 PASS
No routing/profile authority change                PASS
No provider/model invocation                       PASS
No Context/Memory/Knowledge reread                  PASS
No ranking/scoring/selection authority              PASS
No Goal/Project persistence or activation           PASS
No execution authority                             PASS
git diff --check                                   PASS
Exact implementation commit scope                  PASS
Working tree clean                                 PASS
Owner Guided Acceptance                            PASS
Normal non-force push                              PASS
Independent remote verification                    PASS
```

---

## 32. Explicit Non-Goals / Future Ownership

```text
Metacognition / uncertainty / confidence classes  -> D132
Critic / Publication Gate                         -> D133
Experience / Learning boundary                    -> D134
Model capability knowledge                        -> D135
Cognitive Executive / model-assisted runtime      -> D136
Newborn Brain integration / security / Birth      -> D137
```

D131 also excludes:

```text
Browser autonomy
tool autonomy
workflow autonomy
automatic provider/model fallback
autonomous Goal activation
autonomous Project creation
autonomous Memory mutation
autonomous experience promotion
self-modifying code
background cognitive loops
Calendar writes
external side effects
```

---

## 33. Design Resolution Notes — Rev 0.1

Rev 0.1 resolves the following details within the already Owner-approved A–N boundary:

### 33.1 Prediction is sequencing/coherence, not Planning semantics

D131 requires a valid Prediction before Planning but does not feed Prediction scenarios into the historical Planning algorithm.

This preserves both:

```text
canonical sequence after Prediction
existing PlanningService authority boundary
```

### 33.2 Decision insufficiency has organ-status precedence

When a valid Goal / Project candidate exists in the same turn as an applicable but insufficient Decision:

```text
CognitiveDecisionGoalArtifact.envelope.status
    == INSUFFICIENT
```

The candidate remains present and candidate-only.

This fails safe without erasing recognized Goal / Project metadata.

### 33.3 Broad D130 information gaps remain owned upstream

D131 Planning preserves only the existing PlanningService-approved gap vocabulary.

Any other D130 information gaps remain available in D130 Reasoning for D132 Metacognition / uncertainty handling.

D131 does not invent a second gap taxonomy.

---

## 34. Current Freeze Candidate Status

```text
D131 — PLANNING / DECISION COGNITIVE INTEGRATION V1

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
5c6a646f3ec7f18dc6bbb93669a17924658c99f9
```

---

**End of D131 Planning / Decision Cognitive Integration V1 — Design Freeze Rev 0.1 Candidate**
