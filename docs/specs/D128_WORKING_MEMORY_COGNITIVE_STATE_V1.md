# D128 — Working Memory / Cognitive State V1

**Status:** DESIGN FROZEN - OWNER APPROVED
**Design revision:** Rev 1.0 - FROZEN DESIGN BASELINE
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN
**D127 baseline:** COMPLETE / PUSHED / REMOTE FROZEN
**D127 implementation commit:** `1ab118dcbc04dcd215ea906fc32d0f5e95d03b67`
**Live `origin/main` rechecked before D128 Design Freeze preparation:** `1ab118dcbc04dcd215ea906fc32d0f5e95d03b67`
**Owner Design Review:** PASS - Decisions A-L APPROVED
**Implementation:** NOT STARTED
**Code change:** NONE
**Git commit:** NOT CREATED
**Git push:** NOT PUSHED
**Codex:** NOT USED

---

## 1. Purpose

D128 forms the Brain V1 **Working Memory / Cognitive Working State** foundation and defines the bounded same-conversation concurrency contract needed by the later Cognitive Executive.

The governing rule is:

> **Working Memory is the bounded mutable scratch state of one cognitive turn. It is not durable Memory, not authority, and not execution state.**

D128 reconciles two existing state shapes rather than creating a third unrelated pipeline:

```text
Grounded Knowledge
    -> ExecutionContext

Normal Chat
    -> ChatTurnResult
```

into one canonical Brain-facing state:

```text
CognitiveWorkingState
    is-a ExecutionContext
    + exact cognitive turn binding
    + D126 Working Memory envelope
    + optional D127 Perception / Attention / Task slots
```

The second D128 responsibility is to freeze a deterministic, process-local concurrency primitive for:

```text
one active Cognitive Turn
per (workspace, conversation)
```

without queueing, waiting, retrying, persistence, or runtime wiring.

---

## 2. Owner Design Decisions A-L — APPROVED

### A — Canonical state strategy

APPROVED:

`CognitiveWorkingState` is the canonical Brain working state and **subclasses the existing `ExecutionContext`**.

D128 extends the existing state substrate. It does not replace or fork the intelligence pipeline.

### B — Ephemeral mutable state

APPROVED:

Working State is ephemeral and mutable for one turn.

It is not:

```text
confirmed Memory
durable persistence
authorization
approval
execution permission
provider routing authority
```

### C — D126 / D127 slots

APPROVED:

D128 adds:

```text
Working Memory provenance envelope
Perception slot
Attention slot
Task Understanding slot
```

while existing reasoning / planning / decision / goals remain in `IntelligenceContext`.

### D — Future-organ boundary

APPROVED:

D128 does not create Prediction, Metacognition, Verification/Critic, Model Intelligence, Experience, or Cognitive Executive behavior before their milestones.

### E — State convergence

APPROVED:

D128 creates pure deterministic convergence from:

```text
legacy ExecutionContext
Normal Chat ChatTurnResult
```

into the same `CognitiveWorkingState` class.

Convergence does not rerun cognition or invoke AI.

### F — Identity consistency

APPROVED:

Conversation/project identity must match the immutable cognitive binding before state convergence succeeds.

Cross-conversation, cross-project, or cross-workspace state contamination fails closed.

### G — D129 boundary

APPROVED:

D128 does not move, refetch, resolve, or reinterpret Memory/Context truth.

D129 remains the owner of Brain-facing Context/Memory integration and bounded Context stabilization.

### H — Same-conversation lease contract

APPROVED:

D128 defines a process-local turn lease keyed by:

```text
(workspace_id, conversation_id)
```

with one active turn per key.

### I — No queue / no wait / no retry

APPROVED:

A second acquire for the same active key fails immediately with D126:

```text
CognitiveFailureCode.TURN_IN_PROGRESS
```

No queue, wait loop, retry loop, or hidden fallback exists.

### J — Stale release protection

APPROVED:

A release must match the exact lease generation.

A stale/mismatched release can never release a newer active turn.

Different conversations and different workspaces remain independently acquirable.

### K — Runtime integration deferred

APPROVED:

D128 creates the contract and tested service only.

It does **not** wire the guard or canonical state into `ConversationService`, API routes, provider invocation, or the live Cognitive Executive.

D136 owns integrated runtime enforcement.

### L — No authority or persistence expansion

APPROVED:

D128 adds no:

```text
DB schema / migration
repository persistence
provider/model/profile routing
Memory mutation
ContextResolver behavior
AIRuntime change
ExecutionGuard change
frontend change
tool/action authority
execution authority
```

---

## 3. Reconciled Existing Ownership

### 3.1 `ExecutionContext`

Current canonical pipeline substrate:

```text
ExecutionContext
├── request: RequestContext
├── conversation: ConversationContext
├── knowledge: KnowledgeContext
├── intelligence: IntelligenceContext
├── response: ResponseContext
└── runtime: RuntimeContext
```

Existing `DomainStep` intentionally mutates this shared object.

Existing `Pipeline` executes ordered steps over it.

D128 preserves this behavior.

### 3.2 `ChatTurnResult`

Normal Chat currently returns a frozen result containing:

```text
reply
conversation_id
project_id
memories_used
reasoning_plan
planning_plan
decision_analysis
goal_analysis
project_context
project_action_analysis
project_action_plan
project_action_execution_proposal
context_usage
```

D128 may project safe cognitive result fields into Working State, but action/execution proposal fields do not become cognitive authority.

### 3.3 Grounded Knowledge

`KnowledgeAnswerService` already creates and mutates `ExecutionContext`.

Therefore Grounded Knowledge is the strongest existing Working Memory prototype.

D128 must preserve its current mutation semantics and pipeline compatibility.

### 3.4 D126 provenance and failure vocabulary

D128 reuses:

```text
CognitiveArtifactEnvelope
CognitiveOrgan.WORKING_MEMORY
CognitiveOrganStatus
CognitiveFailureCode.TURN_IN_PROGRESS
CognitiveFailureCode.CONTRACT_VIOLATION
COGNITIVE_ID_MAX_BYTES
```

No duplicate Brain-wide provenance/failure vocabulary is created.

### 3.5 D127 input semantics

D128 stores D127 artifacts by reference/type:

```text
CognitivePerceptionArtifact
CognitiveAttentionArtifact
CognitiveTaskDescription
```

D128 does not reinterpret or recompute them.

---

## 4. Exact D128 Production Modules

D128 implementation is frozen to exactly four production paths:

```text
NEW    backend/app/contracts/cognitive_working_state.py
NEW    backend/app/intelligence/context/cognitive.py
MODIFY backend/app/intelligence/context/__init__.py
NEW    backend/app/services/cognitive_working_state.py
```

Focused tests are exactly two paths:

```text
NEW    backend/tests/test_d128_cognitive_working_state.py
NEW    backend/tests/test_d128_cognitive_working_state_security.py
```

No other implementation path is authorized without Owner amendment review.

---

## 5. Exact D128 Constants

`backend/app/contracts/cognitive_working_state.py` defines:

```text
D128_WORKING_STATE_ARTIFACT_TYPE
    = "cognitive.working_state"

D128_WORKING_STATE_CONTRACT_VERSION
    = "o-ai.cognitive-working-state.v1"

D128_CONCURRENCY_POLICY
    = "one_active_turn_per_conversation.v1"
```

D128 reuses `COGNITIVE_ID_MAX_BYTES` from D126 for `turn_id`.

No new task semantics, routing taxonomy, or provider vocabulary is introduced.

---

## 6. `CognitiveWorkingStateBinding`

Exact immutable binding:

```text
CognitiveWorkingStateBinding
├── turn_id: str
├── workspace_id: WorkspaceId
├── conversation_id: UUID
└── project_id: UUID | None
```

Validation:

```text
turn_id
    exact str
    non-empty
    trimmed
    UTF-8 length <= COGNITIVE_ID_MAX_BYTES
    no Unicode category Cc

workspace_id
    exact existing WorkspaceId object

conversation_id
    exact UUID object

project_id
    None or exact UUID object
```

The binding is the canonical D128 identity anchor.

It does not grant authority.

The mutable legacy `RequestContext` is a compatibility mirror and is never the source of workspace authority.

---

## 7. `CognitiveTurnLease`

Exact immutable lease:

```text
CognitiveTurnLease
├── binding: CognitiveWorkingStateBinding
├── generation: int
└── policy: str
```

Validation:

```text
binding
    exact CognitiveWorkingStateBinding

generation
    exact int
    bool rejected
    >= 1

policy
    exactly "one_active_turn_per_conversation.v1"
```

`generation` is allocated monotonically by one `CognitiveTurnGuard` instance.

Generation protects against stale release even if a later turn reuses the same conversation or turn identifier.

A lease is a concurrency token only.

```text
lease ≠ authorization
lease ≠ approval
lease ≠ execution permission
```

---

## 8. `CognitiveWorkingState`

Location:

```text
backend/app/intelligence/context/cognitive.py
```

Exact inheritance:

```text
CognitiveWorkingState(ExecutionContext)
```

Additional exact fields:

```text
binding: CognitiveWorkingStateBinding
working_memory_envelope: CognitiveArtifactEnvelope
perception: CognitivePerceptionArtifact | None = None
attention: CognitiveAttentionArtifact | None = None
task: CognitiveTaskDescription | None = None
```

The existing inherited fields remain:

```text
request
conversation
knowledge
intelligence
response
runtime
```

No duplicate reasoning/planning/decision/goal fields are added.

---

## 9. Working Memory envelope rules

`working_memory_envelope` must satisfy:

```text
producer_organ == CognitiveOrgan.WORKING_MEMORY
artifact_type == "cognitive.working_state"
contract_version == "o-ai.cognitive-working-state.v1"
status == CognitiveOrganStatus.READY
turn_id == binding.turn_id
workspace_id == binding.workspace_id
```

`context_snapshot_digest` may remain `None` in D128.

Reason:

D129 owns final Brain-facing Context/Memory integration and Context freeze enforcement.

D128 creates no second Context digest.

---

## 10. Request / binding consistency

At Working State construction:

```text
request.request_id == binding.turn_id
request.conversation_id == binding.conversation_id
request.project_id == binding.project_id
```

`request.question` remains the existing Owner-request compatibility field.

The top-level `binding`, `working_memory_envelope`, and `request` references are frozen against replacement in the D128 model.

Nested legacy contexts remain mutable because existing pipeline steps intentionally mutate them.

The immutable D128 `binding` remains the canonical identity if legacy nested state is later mutated by compatibility code.

---

## 11. D127 artifact attachment rules

For every non-null D127 artifact:

```text
artifact.envelope.turn_id == binding.turn_id
artifact.envelope.workspace_id == binding.workspace_id
```

For `task` additionally:

```text
task.normalized_request
    == " ".join(request.question.split())
```

Context digest compatibility:

```text
if both
    working_memory_envelope.context_snapshot_digest
and
    artifact.envelope.context_snapshot_digest
are non-null,

they must be equal.
```

A null digest on either side remains valid in D128 because D129 owns freeze enforcement.

D128 never edits D127 artifacts.

---

## 12. Mutation semantics

`CognitiveWorkingState` remains a mutable Working Memory object.

Allowed legacy mutations include existing pipeline behavior such as:

```text
conversation.history
conversation.memories
conversation.project_context

knowledge.intent
knowledge.queries
knowledge.evidence
knowledge.context
knowledge.conflicts
knowledge.records

intelligence.reasoning
intelligence.planning
intelligence.decision
intelligence.goals

response.answer
response.citations
response.evidence_quality

runtime transient fields
```

D128 does not change existing `DomainStep.execute(context) -> None` semantics.

D128 top-level D127 artifact assignments are validated against the immutable binding/envelope.

---

## 13. `CognitiveWorkingStateConvergenceService`

Location:

```text
backend/app/services/cognitive_working_state.py
```

The service is deterministic and performs no I/O.

### 13.1 `from_execution_context`

Conceptual signature:

```text
from_execution_context(
    binding,
    working_memory_envelope,
    context,
    *,
    perception=None,
    attention=None,
    task=None,
) -> CognitiveWorkingState
```

Requirements:

1. exact `CognitiveWorkingStateBinding`;
2. exact D128 Working Memory envelope;
3. source must be an `ExecutionContext`;
4. source request identity must match binding;
5. copy the existing context containers into one new `CognitiveWorkingState`;
6. preserve request, conversation, knowledge, intelligence, response, and runtime values;
7. attach optional D127 artifacts under D128 invariants;
8. perform no reasoning, planning, decision, goal, retrieval, provider, repository, or persistence call.

The result must not be an alias of the caller's top-level mutable context containers.

Caller mutation of the original `ExecutionContext` after convergence must not mutate the stored D128 state.

### 13.2 `from_chat_turn_result`

Conceptual signature:

```text
from_chat_turn_result(
    binding,
    working_memory_envelope,
    owner_request,
    result,
    *,
    perception=None,
    attention=None,
    task=None,
) -> CognitiveWorkingState
```

Requirements:

1. exact binding/envelope;
2. exact non-empty Owner request after canonical whitespace normalization;
3. exact existing `ChatTurnResult`;
4. `result.conversation_id == binding.conversation_id`;
5. `result.project_id == binding.project_id`;
6. build `RequestContext` with `request_id=binding.turn_id`;
7. map `result.project_context` to `ConversationContext.project_context`;
8. create an empty D128 `KnowledgeContext`;
9. map existing reasoning/planning/decision/goals to `IntelligenceContext`;
10. map `result.reply` to `ResponseContext.answer`;
11. use default transient `RuntimeContext`;
12. attach optional D127 artifacts;
13. do not rerun any cognition.

---

## 14. Explicit Normal Chat projection exclusions

D128 intentionally does not project these `ChatTurnResult` fields into canonical cognitive state:

```text
memories_used
context_usage
project_action_analysis
project_action_plan
project_action_execution_proposal
```

Reasons:

```text
memories_used / context_usage
    -> D129 owns canonical Brain-facing Context/Memory integration

project action fields
    -> action/execution-adjacent data must not become cognitive authority
```

The fields remain present on `ChatTurnResult`; D128 does not change its public shape.

Exclusion is not deletion from the historical result. It is only a D128 convergence rule.

---

## 15. Normal Chat / Grounded Knowledge convergence invariant

D128 proves:

```text
Normal Chat ChatTurnResult
    -> CognitiveWorkingState

Grounded Knowledge ExecutionContext
    -> CognitiveWorkingState
```

Both become the same canonical class with:

```text
same binding contract
same Working Memory envelope contract
same inherited ExecutionContext shape
same D127 artifact slots
```

D128 does not require both lanes to populate identical cognitive data.

Convergence means **shared state architecture**, not identical information content.

---

## 16. `CognitiveTurnGuard`

Location:

```text
backend/app/services/cognitive_working_state.py
```

The guard is process-local and thread-safe.

Internal active key:

```text
(binding.workspace_id, binding.conversation_id)
```

Internal active value:

```text
(turn_id, generation)
```

No DB/repository/store/network dependency is permitted.

### 16.1 Acquire

Conceptual signature:

```text
acquire(
    binding: CognitiveWorkingStateBinding,
) -> CognitiveTurnLease
```

Atomic behavior under one internal lock:

```text
if key inactive:
    increment guard generation
    register exact (turn_id, generation)
    return lease

if key active:
    raise CognitiveTurnInProgressError
        failure_code = CognitiveFailureCode.TURN_IN_PROGRESS
```

No queue.

No wait.

No retry.

No sleep.

### 16.2 Release

Conceptual signature:

```text
release(
    lease: CognitiveTurnLease,
) -> None
```

Atomic behavior:

```text
if exact key + turn_id + generation is active:
    remove active entry

otherwise:
    raise CognitiveTurnLeaseError
        failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

A failed release must not mutate active state.

### 16.3 Read-only inspection

The guard may expose one bounded diagnostic method:

```text
active_turn_id(
    workspace_id,
    conversation_id,
) -> str | None
```

This grants no authority.

---

## 17. Concurrency semantics

Exact D128 behavior:

```text
same workspace + same conversation
    -> max one active lease

same workspace + different conversation
    -> independent

different workspace + same UUID conversation_id
    -> independent

released conversation
    -> next acquire allowed

stale old lease after newer acquire
    -> rejected
    -> newer turn remains active
```

Thread contention must produce at most one successful acquire for one inactive key.

D128 does not promise distributed/process-wide exclusion.

Process restart clears this ephemeral guard.

Distributed/durable locking is not introduced.

---

## 18. Accepted event vs active Cognitive Turn

Existing O-AI may persist the Owner's user message before inference completes.

D128 preserves the architecture distinction:

```text
Conversation Event Accepted
    ≠
Cognitive Turn Completed
```

The D128 guard is not a message transaction and does not alter current conversation persistence.

D136 later owns where acquire/release occurs in the integrated lifecycle.

---

## 19. Failure semantics

Exact service errors:

```text
CognitiveTurnInProgressError
    failure_code = CognitiveFailureCode.TURN_IN_PROGRESS

CognitiveTurnLeaseError
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

Errors expose bounded safe codes only.

No provider exception, DB exception, credential, prompt, or hidden reasoning is embedded.

D128 does not add a public API error mapping.

---

## 20. Import / dependency boundaries

### 20.1 Contract module

Allowed application imports:

```text
app.contracts.cognitive_brain
app.contracts.workspace
```

plus Python standard library.

The D128 contract module does not import:

```text
repositories
DB
providers
adapters
AIRuntime
ExecutionGuard
ContextResolver
ConversationService
```

### 20.2 Cognitive context module

Allowed application imports:

```text
app.contracts.cognitive_brain
app.contracts.cognitive_input_semantics
app.contracts.cognitive_working_state
app.intelligence.context.execution
app.intelligence.context.request
```

plus Pydantic / standard library as required.

### 20.3 Service module

Allowed application dependencies are compatibility-only:

```text
app.contracts.cognitive_brain
app.contracts.cognitive_input_semantics
app.contracts.cognitive_working_state
app.intelligence.context
app.services.conversations
```

and Python threading / standard library.

No provider/runtime/repository/DB dependency is authorized.

---

## 21. No side effects

D128 binding/state construction and convergence must not perform:

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
Context resolution
Memory resolution
reasoning recomputation
planning recomputation
decision recomputation
goal recomputation
```

The process-local guard mutates only its own in-memory lease table.

---

## 22. Explicit non-goals

D128 does not implement:

```text
ContextSnapshot stabilization
Memory retrieval integration
Prediction
Metacognition
Verification/Critic
Model Intelligence
Experience
Cognitive Executive
provider invocation coordination
turn deadline
stage budget
late provider result enforcement
publication gate
durable Cognitive Turn Manifest persistence
distributed lock
cross-process lock
background worker
queue
retry/fallback
frontend state
```

Those remain later milestone responsibilities.

---

## 23. Exact scope lifecycle

### 23.1 Design Freeze

Exactly one new docs file:

```text
NEW docs/specs/D128_WORKING_MEMORY_COGNITIVE_STATE_V1.md
```

No production/test file change is allowed in the Design Freeze commit.

### 23.2 Implementation after remote freeze and separate authorization

Exactly six code/test paths:

```text
NEW    backend/app/contracts/cognitive_working_state.py
NEW    backend/app/intelligence/context/cognitive.py
MODIFY backend/app/intelligence/context/__init__.py
NEW    backend/app/services/cognitive_working_state.py
NEW    backend/tests/test_d128_cognitive_working_state.py
NEW    backend/tests/test_d128_cognitive_working_state_security.py
```

### 23.3 Total D128 milestone

```text
7 repository files total
1 Design Freeze docs file
6 implementation code/test files
```

Any eighth total path requires:

```text
STOP
-> exact dependency report
-> Owner review
-> amendment if justified
```

---

## 24. Exact Functional Test Matrix

```text
F01 valid PERSONAL WorkingStateBinding
F02 valid COMPANY WorkingStateBinding
F03 optional project_id preserved
F04 valid CognitiveTurnLease exact policy
F05 lease generation preserved exactly

F06 CognitiveWorkingState is an ExecutionContext
F07 exact Working Memory envelope accepted
F08 binding/request turn_id mirror exact
F09 binding/request conversation_id mirror exact
F10 binding/request project_id mirror exact
F11 empty D127 artifact slots valid
F12 valid Perception attachment
F13 valid Attention attachment
F14 valid Task attachment
F15 matching non-null Context digest accepted
F16 inherited RuntimeContext default preserved

F17 existing DomainStep can mutate CognitiveWorkingState
F18 existing Pipeline executes CognitiveWorkingState in order
F19 inherited ConversationContext remains mutable
F20 inherited KnowledgeContext remains mutable
F21 inherited IntelligenceContext remains mutable
F22 inherited ResponseContext remains mutable

F23 ExecutionContext convergence preserves request
F24 ExecutionContext convergence preserves conversation
F25 ExecutionContext convergence preserves knowledge
F26 ExecutionContext convergence preserves intelligence
F27 ExecutionContext convergence preserves response
F28 ExecutionContext convergence preserves runtime
F29 ExecutionContext convergence does not alias source top-level containers
F30 ExecutionContext convergence deterministic

F31 ChatTurnResult convergence maps reply
F32 ChatTurnResult convergence maps conversation identity
F33 ChatTurnResult convergence maps optional project identity
F34 ChatTurnResult convergence maps project_context
F35 ChatTurnResult convergence maps reasoning
F36 ChatTurnResult convergence maps planning
F37 ChatTurnResult convergence maps decision
F38 ChatTurnResult convergence maps goals
F39 ChatTurnResult convergence creates empty KnowledgeContext
F40 ChatTurnResult convergence uses default RuntimeContext
F41 memories_used not projected in D128
F42 context_usage not projected in D128
F43 project action analysis not projected in D128
F44 project action plan not projected in D128
F45 project action execution proposal not projected in D128
F46 Normal Chat and Grounded Knowledge converge to same canonical class

F47 first guard acquire succeeds
F48 second same-key acquire fails TURN_IN_PROGRESS
F49 release exact lease succeeds
F50 release allows next acquire
F51 generation increases on next acquire
F52 different conversations acquire independently
F53 same conversation UUID in different workspaces acquires independently
F54 active_turn_id reports exact active turn
F55 active_turn_id returns None after release
F56 stale release is rejected and newer turn remains active
F57 concurrent same-key acquisition yields exactly one success

F58 historical ExecutionContext construction unchanged
F59 historical Pipeline ordering unchanged
F60 historical KnowledgeOrchestrator accepts ExecutionContext behavior unchanged
F61 historical ChatTurnResult public field shape unchanged
```

---

## 25. Exact Security Test Matrix

```text
S01 empty turn_id rejected
S02 whitespace-padded turn_id rejected
S03 control-character turn_id rejected
S04 over-limit turn_id rejected
S05 raw workspace string rejected
S06 raw conversation UUID string rejected
S07 raw project UUID string rejected

S08 non-binding lease input rejected
S09 bool lease generation rejected
S10 zero lease generation rejected
S11 negative lease generation rejected
S12 wrong lease policy rejected

S13 wrong Working Memory producer rejected
S14 wrong Working Memory artifact type rejected
S15 wrong Working Memory contract version rejected
S16 non-READY Working Memory envelope rejected
S17 envelope turn mismatch rejected
S18 envelope workspace mismatch rejected
S19 request_id / binding turn mismatch rejected
S20 request conversation / binding mismatch rejected
S21 request project / binding mismatch rejected

S22 Perception turn mismatch rejected
S23 Perception workspace mismatch rejected
S24 Attention turn mismatch rejected
S25 Attention workspace mismatch rejected
S26 Task turn mismatch rejected
S27 Task workspace mismatch rejected
S28 Task normalized request mismatch rejected
S29 conflicting Perception Context digest rejected
S30 conflicting Attention Context digest rejected
S31 conflicting Task Context digest rejected

S32 no owner_approval field
S33 no execution_authorization field
S34 no execution_plan field
S35 no provider/adapter/model/profile field
S36 no credential/api_key/provider_secret field
S37 no tool_permission field
S38 no raw_prompt/system_prompt/hidden_reasoning/CoT field
S39 no memory/project/repository write field
S40 lease grants no execution or approval field

S41 wrong ExecutionContext source type rejected
S42 ChatTurnResult conversation mismatch rejected
S43 ChatTurnResult project mismatch rejected
S44 empty normalized Owner request rejected
S45 convergence performs no Context resolution
S46 convergence performs no Memory resolution
S47 convergence performs no Reasoning/Planning/Decision/Goal recomputation
S48 convergence performs no provider/network/DB/repository call
S49 caller mutation of source ExecutionContext cannot mutate converged state
S50 Normal Chat action proposal objects are not copied into Working State

S51 duplicate same-key acquire has no queue/wait behavior
S52 stale release cannot clear newer active turn
S53 wrong lease type release rejected
S54 mismatched turn release does not mutate active state
S55 mismatched generation release does not mutate active state
S56 same conversation UUID across workspaces does not collide
S57 concurrent same-key acquire never grants two leases
S58 guard performs no DB/repository/network call
S59 guard contains no sleep/wait/condition queue operation
S60 no retry/fallback operation

S61 D126 TURN_IN_PROGRESS vocabulary unchanged
S62 D126 CONTRACT_VIOLATION vocabulary unchanged
S63 D127 Perception contract unchanged
S64 D127 Attention contract unchanged
S65 D127 Task contract unchanged
S66 D104 exact task taxonomy unchanged
S67 D125 model/profile authority unchanged
S68 ConversationService not modified
S69 ContextResolver not modified
S70 AIRuntime / ExecutionGuard not modified
```

---

## 26. Targeted Historical Regression

At minimum, implementation validation must include exact current files for:

```text
backend/tests/test_execution_context.py
backend/tests/test_pipeline.py
backend/tests/test_knowledge_pipeline_regression.py
backend/tests/test_conversation_dependency_wiring.py
backend/tests/test_conversation_memory.py

backend/tests/test_workspace_contract.py
backend/tests/test_context_contract.py
backend/tests/test_context_resolution_contract.py
backend/tests/test_context_resolver.py
backend/tests/test_context_snapshot.py
backend/tests/test_d94_context_security.py
backend/tests/test_d95_context_resolution_security.py
backend/tests/test_d96_context_snapshot_security.py
backend/tests/test_d97_context_chat_security.py

backend/tests/test_reasoning.py
backend/tests/test_planning.py
backend/tests/test_decision.py

backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
backend/tests/test_d105_task_aware_ai_routing_integration.py
backend/tests/test_d105_task_aware_ai_routing_security.py

backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py

backend/tests/test_d126_cognitive_brain_core_contracts.py
backend/tests/test_d126_cognitive_brain_core_contracts_security.py
backend/tests/test_d127_cognitive_input_semantics.py
backend/tests/test_d127_cognitive_input_semantics_security.py

backend/tests/test_execution_guard.py
backend/tests/test_ai_runtime.py
```

Exact filenames must be revalidated before implementation mutation.

No historical test modification is pre-authorized.

Any required historical test edit means STOP and Owner review.

---

## 27. Acceptance Criteria

D128 is complete only when all applicable gates pass:

```text
Read-only reconciliation                           PASS
Owner Design Reconciliation A-L                   PASS
D128 Design Freeze                                PASS

Design Freeze exact one-doc scope                 PASS
Implementation exact six-file scope               PASS
Frozen D128 spec unchanged during implementation  PASS

D128 functional tests                             PASS
D128 security tests                               PASS

ExecutionContext compatibility                    PASS
Pipeline mutation compatibility                   PASS
Knowledge pipeline compatibility                  PASS
ChatTurnResult compatibility                      PASS
D126 provenance/failure compatibility             PASS
D127 artifact compatibility                       PASS
D104/D125 authority compatibility                 PASS

Same-conversation single-active-turn primitive    PASS
No queue/wait/retry                               PASS
Stale release protection                          PASS
Workspace-key isolation                           PASS
Thread contention atomicity                       PASS

Targeted historical regression                    PASS
Full backend regression                           PASS

No frontend production change                     PASS
No DB/migration change                            PASS
No API route change                               PASS
No ConversationService change                     PASS
No ContextResolver change                         PASS
No AIRuntime/ExecutionGuard change                PASS
No provider/model/profile authority change        PASS
No persistence introduced                         PASS
No runtime guard wiring introduced                PASS

git diff --check                                  PASS
Exact local commit scope                          PASS
Working tree clean                                PASS
Owner guided acceptance                           PASS
Final push / remote freeze                        PASS
```

---

## 28. Guided Acceptance Shape

Owner confirms:

```text
A. CognitiveWorkingState remains an ExecutionContext-compatible shared state
B. Working State binding is immutable and workspace/conversation/project safe
C. D127 Perception/Attention/Task attach without changing their semantics
D. Normal Chat and Grounded Knowledge converge to the same state class
E. Normal Chat action/execution proposal fields do not become cognitive authority
F. one active turn per workspace+conversation is enforced by the D128 primitive
G. duplicate acquire fails immediately with TURN_IN_PROGRESS and no queue/wait/retry
H. stale lease release cannot release a newer turn
I. no persistence/provider/model/execution authority is added
J. ConversationService/runtime wiring remains deferred to D136
```

---

## 29. Codex Budget

Default:

```text
CODEX = NO
```

Expected implementation is bounded:

```text
1 new contract module
1 new cognitive context module
1 narrow context export edit
1 new pure convergence/guard service
2 focused test modules
```

Codex becomes justified only if implementation reconciliation proves unexpected broad Pydantic inheritance/caller coupling or non-local concurrency dependencies.

If Codex becomes necessary:

```text
STOP
-> report exact reason
-> Owner review
```

---

## 30. Frozen Status

```text
D128 — WORKING MEMORY / COGNITIVE STATE V1

READ-ONLY RECONCILIATION:  COMPLETE
OWNER DECISIONS A-L:       APPROVED
EXACT CONTRACTS:           DEFINED
STATE CONVERGENCE:         DEFINED
CONCURRENCY CONTRACT:      DEFINED
FUNCTIONAL TEST MATRIX:    DEFINED
SECURITY TEST MATRIX:      DEFINED
IMPLEMENTATION SCOPE:      EXACTLY 6 CODE/TEST PATHS

DESIGN FREEZE:             FROZEN - OWNER APPROVED

IMPLEMENTATION:            NOT STARTED
CODE CHANGE:               NONE
COMMIT:                    NOT CREATED
PUSH:                      NOT PUSHED
CODEX USED:                NO
```

---

**End of D128 — Working Memory / Cognitive State V1 Design Freeze**
