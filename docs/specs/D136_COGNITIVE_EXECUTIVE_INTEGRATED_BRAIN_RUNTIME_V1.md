# D136 — Cognitive Executive / Integrated Brain Runtime V1

**Document status:** DESIGN FREEZE REV 0.1 — REPOSITORY ARTIFACT CANDIDATE
**Architecture phase:** Brain Formation
**Baseline:** D135 COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED
**Baseline commit:** `fc4a5915043397877a9a37692861183ab54126cc`
**Owner Design Reconciliation A–P:** APPROVED
**Independent semantic design review:** PASS
**Independent repository baseline verification:** PASS
**Implementation planning / exact-scope reconciliation:** PASS
**Implementation status:** NOT AUTHORIZED / NOT STARTED
**Implementation code change:** NONE
**Design-freeze commit:** NOT AUTHORIZED / NOT CREATED
**Push:** NOT AUTHORIZED / NOT PUSHED

---

## 1. Purpose

D136 creates the bounded **Cognitive Executive / Integrated Brain Runtime V1** for O-AI Cognitive Brain V1.

The Cognitive Executive coordinates already-frozen cognitive organs and the already-authoritative AI execution path into one bounded turn lifecycle.

The governing invariant is:

```text
Cognitive Executive = deterministic orchestration
Cognitive Executive ≠ autonomous agent
Cognitive Executive ≠ execution authority
Cognitive Executive ≠ routing authority
Cognitive Executive ≠ model/profile authority
```

D136 integrates cognition. It does not replace the systems that own routing, authorization, execution, persistence, Workspace policy, or Owner approval.

---

## 2. Canonical Baseline

Exact D136 design baseline:

```text
fc4a5915043397877a9a37692861183ab54126cc
```

D136 is evolutionary and additive. It must preserve D35/D36/D49, D98, D104/D105, D111, D125, and D126–D135 authority and semantics unless this document explicitly defines a narrow integration seam.

---

## 3. Frozen Architecture Source

D136 implements the already-frozen Cognitive Brain architecture boundary:

```text
D136
Cognitive Executive / Integrated Brain Runtime V1

Primary existing assets:
Pipeline
DomainStep
KnowledgeOrchestrator
ExecutionPlanner
ExecutionGuard
AIRuntime
CognitiveWorkingState
CognitiveTurnGuard
D127–D135 cognitive organs/contracts

Primary new work:
Generalized Cognitive Executive
Central invocation coordination
Fresh authorization per model call
Turn deadline
Stage budget checks
Circuit-breaker integration
Late-result enforcement
Bounded Critic revision
Live normal-chat integration
```

The architecture rule remains:

```text
If an existing component already owns a responsibility,
D136 must reuse or compose it before introducing a parallel system.
```

---

## 4. Authority Boundary

D136 may:

```text
coordinate
sequence
validate
check remaining turn budget
request fresh planning
request fresh authorization
invoke AIRuntime only with valid fresh authorization
observe safe binding metadata
enforce same-turn binding continuity
record bounded safe trace metadata
reject stale or late results
perform one bounded revision when D133 requires it
derive a terminal cognitive outcome
```

D136 must never:

```text
choose a provider outside D111/D35 routing
choose a model outside existing routing/profile authority
choose or rewrite a Local AI profile
create ExecutionAuthorization itself
bypass ExecutionGuard
invoke a provider directly
hold a raw provider client
grant Tool / Module / Plugin / connector authority
grant Owner approval
modify Workspace AI policy
modify Memory / Knowledge / Prompt / Policy / Code
persist hidden reasoning
create autonomous background cognition
create unbounded retry or fallback
```

The authority chain remains:

```text
server-owned task / workspace policy
        ↓
D111 / existing routing
        ↓
ExecutionPlanner
        ↓
ExecutionGuard
        ↓
AIRuntime
        ↓
AIAdapter
        ↓
Local AI / Cloud AI
```

---

## 5. Existing Systems Reused

D136 reuses, without semantic replacement:

```text
D35  ExecutionPlanner
D36  ExecutionGuard
D49  AIRuntime / normal-chat orchestration foundation
D94–D97 Context truth / snapshot path
D98  Workspace AI policy
D104/D105 task-aware routing
D111 Brain routing
D125 Local AI task profiles
D126 Cognitive Brain constitution
D127 Perception / Attention / Task Understanding
D128 Working Memory / CognitiveWorkingState / CognitiveTurnGuard
D129 Context / Memory integration
D130 Reasoning / Prediction
D131 Planning / Decision / Goal
D132 Metacognition / Uncertainty
D133 Verification / Critic / Publication Gate
D134 ExperienceCandidate boundary
D135 Model Intelligence capability knowledge
ChatService rendering foundation
ConversationService Context/persistence boundary
CommandOrchestrator normal-chat execution boundary
FastAPI dependency composition
```

No parallel routing, authorization, runtime, conversation store, Context store, or persistence layer is created.

---

## 6. Cognitive Executive Organ

D136 uses the already-frozen identity:

```python
CognitiveOrgan.COGNITIVE_EXECUTIVE
```

D136 must not modify the D126 organ enum.

The Executive output is one immutable bounded artifact:

```text
artifact_type:
cognitive.executive_outcome

contract_version:
o-ai.cognitive-executive.v1
```

Its producer organ must be exactly:

```text
CognitiveOrgan.COGNITIVE_EXECUTIVE
```

---

## 7. Exact D136 Constants

```python
D136_EXECUTIVE_ARTIFACT_TYPE = "cognitive.executive_outcome"
D136_EXECUTIVE_CONTRACT_VERSION = "o-ai.cognitive-executive.v1"
D136_EXECUTIVE_TRACE_VERSION = "o-ai.cognitive-executive-trace.v1"
D136_INVOCATION_BINDING_VERSION = "o-ai.cognitive-invocation-binding.v1"

D136_MAX_MODEL_INVOCATIONS = 4
D136_MAX_DRAFT_GENERATIONS = 2
D136_MAX_TRACE_EVENTS = 64
D136_MAX_SAFE_REASON_CODES = 32
```

D136 reuses:

```text
COGNITIVE_REVISION_COUNT_MAX = 1
CognitiveInvocationPurpose
CognitiveTurnState
CognitiveFailureCode
CognitiveOrganStatus
CognitiveArtifactEnvelope
```

No duplicate invocation-purpose enum is authorized.

---

## 8. Bounded Invocation Topology

The only valid model invocation purposes are the four D126 values:

```text
PRIMARY_SYNTHESIS
CRITIC
REVISION
POST_REVISION_CRITIC
```

Maximum topology:

```text
PRIMARY_SYNTHESIS          max 1
CRITIC                     max 1 when required by server policy
REVISION                   max 1
POST_REVISION_CRITIC       max 1 when required by server policy
```

Therefore:

```text
maximum draft generations = 2
maximum model invocations = 4
maximum revision count     = 1
```

No fifth invocation is permitted.

No invocation purpose may be created dynamically from model output, user text, Memory, Context, plugin output, or tool output.

---

## 9. Fresh Authorization Per Invocation

Every model invocation must execute this chain independently:

```text
D136 Cognitive Invocation Coordinator
        ↓
ExecutionPlanner.plan(...)
        ↓
ExecutionGuard.authorize(...)
        ↓
AIRuntime.execute(...) / AIRuntime.bind(...)
```

A prior `ExecutionPlanningOutcome`, `ExecutionAuthorization`, bound runtime adapter, or plan digest must not be reused as authority for a later model invocation.

Each call receives a distinct bounded server-owned invocation request identity.

Fresh authorization means:

```text
PRIMARY_SYNTHESIS authorization ≠ CRITIC authorization
CRITIC authorization           ≠ REVISION authorization
REVISION authorization         ≠ POST_REVISION_CRITIC authorization
```

even when all calls resolve to the same authorized adapter/model/profile.

---

## 10. Binding Continuity

Fresh authorization does not permit silent authority switching.

After the first successful authorized model binding, D136 records safe binding metadata:

```text
adapter_id
model_id
profile_id if applicable
task_kind
routing mode / policy identity where available
plan digest
```

Subsequent model calls must be independently planned and authorized, then checked against the first-call binding policy.

If a later fresh authorization would silently change provider, adapter, model, profile, Workspace, task domain, or authority path:

```text
FAIL CLOSED
```

D136 must not accept the changed binding as fallback.

D136 performs comparison only. It does not select the replacement binding.

---

## 11. Model Intelligence Boundary

D135 Model Intelligence may be observed as read-only capability knowledge.

It must not become:

```text
routing authority
ranking authority
preferred-model authority
authorization evidence
fallback policy
execution permission
```

In D136 V1:

```text
D135 knowledge may explain / constrain safe coordination
but may not override D111 / D125 / D35 / D36
```

Unknown or conflicted D135 evidence never authorizes a model switch.

---

## 12. Turn Deadline

Each Cognitive Turn owns one server-generated monotonic deadline.

The deadline is:

```text
server-owned
monotonic
transient
not model-controlled
not extendable by an organ
not derived from wall-clock text
not persisted as hidden cognition
```

D136 receives or creates the monotonic deadline from trusted server runtime policy.

No organ may extend it.

At every expensive or externally blocking boundary:

```text
remaining_budget = deadline - monotonic_now
```

If:

```text
remaining_budget <= 0
```

D136 terminates with:

```text
CognitiveFailureCode.TURN_DEADLINE_EXCEEDED
```

No further model invocation is permitted.

---

## 13. Effective Runtime Timeout Preflight

D136 must know the trusted server-owned effective maximum timeout for the exact authorized AI binding before invoking AIRuntime.

For Local AI:

```text
effective timeout comes from the already-authorized D125 LocalAIProfile
```

For Cloud AI:

```text
effective timeout comes from trusted server configuration / dependency wiring
```

The effective timeout source is descriptive runtime configuration only. It does not select provider/model/profile.

Before invocation:

```text
effective_runtime_timeout <= remaining_turn_budget
```

must hold.

If D136 cannot determine a trusted effective timeout:

```text
FAIL CLOSED
```

If the configured runtime timeout exceeds remaining turn budget:

```text
do not invoke
→ TURN_DEADLINE_EXCEEDED-class bounded outcome
```

D136 does not modify AIRuntime, provider timeout settings, or profile timeout settings in V1.

---

## 14. Late-Result Enforcement

After every model/runtime return, D136 rechecks:

```text
turn lease still valid
turn not terminal
deadline not expired
same Workspace / Conversation / Project binding
same ContextSnapshot binding
```

A result that arrives after terminality or deadline is:

```text
STALE
```

and maps to:

```text
CognitiveFailureCode.STALE_LATE_RESULT
```

A stale result must not:

```text
attach to CognitiveWorkingState
replace Draft
change Verification
change Publication Gate
publish a response
write assistant Message
create authoritative Experience outcome
change routing / policy / authorization
```

Correctness must not depend on cancellation succeeding.

---

## 15. Stage Budget Semantics

D136 performs bounded pre/post budget checks around stages.

Pure deterministic local stages must remain fail-fast and receive no autonomous retry loop.

Potentially blocking stages must check remaining budget before entry and must reject their output if the turn becomes stale before attachment.

D136 V1 does not create a general thread pool, scheduler, background worker, or detached cognitive task system.

---

## 16. Circuit Breaker V1

D136 V1 circuit breaker is bounded operational resilience metadata.

Default V1 scope:

```text
one Cognitive Turn
```

A breaker may:

```text
observe bounded runtime failures
open for the remaining turn
reject later dependent invocation attempts early
record a safe reason code
```

A breaker may not:

```text
switch provider
switch model
switch profile
change Workspace
change task domain
grant authority
create retry
persist learning
mutate D135 knowledge
```

V1 introduces no breaker database, scheduler, recovery worker, or autonomous probe loop.

A future durable/shared breaker requires a separately frozen milestone.

---

## 17. Cognitive Turn Lifecycle

D136 preserves the D126 lifecycle:

```text
RECEIVED
↓
ACCEPTED
↓
COGNITIVE_LANE
↓
BOUND
↓
CONTEXT_RESOLVING
↓
CONTEXT_FROZEN
↓
THINKING
↓
MODEL_READY
↓
GENERATING
↓
VERIFYING
↓
REVISING?      bounded to one revision
↓
FINALIZING
↓
PERSISTING
↓
COMPLETED
```

Alternative terminal states:

```text
FAILED
INSUFFICIENT
```

D136 must not create a parallel lifecycle vocabulary for equivalent states.

---

## 18. Context Freeze

D136 respects D129 Context freeze semantics.

Once Context is frozen:

```text
no silent refresh
no selective patch
no merge with later source state
no model-triggered refresh
no Critic-triggered refresh
```

A permitted D129 pre-freeze stabilization attempt remains exactly bounded by D129.

D136 does not create a second Context retry policy.

---

## 19. Working-State Binding

D136 coordinates one `CognitiveWorkingState` bound to:

```text
turn_id
workspace_id
conversation_id
project_id
context_snapshot_digest
```

The binding must remain coherent through the turn.

D136 may not silently rebind the turn to a different Workspace, Conversation, Project, or ContextSnapshot.

---

## 20. Same-Conversation Concurrency

D136 reuses D128 `CognitiveTurnGuard` / `CognitiveTurnLease`.

No second active cognitive turn for the same Workspace + Conversation may silently mutate shared conversation order.

A stale or mismatched lease fails closed.

D136 creates no second concurrency registry.

---

## 21. Pre-Model Cognitive Sequence

The canonical deterministic cognitive sequence before primary synthesis is:

```text
Perception / Attention / Task Understanding
↓
Working State
↓
Context / Memory
↓
Reasoning
↓
Prediction
↓
Cognitive Planning
↓
Decision / Goal
↓
Metacognition
↓
MODEL_READY
```

A stage may be `NOT_APPLICABLE` only under server-owned policy and frozen organ semantics.

D136 does not reimplement the internal algorithm of any organ.

---

## 22. Primary Synthesis

Primary synthesis is at most one authorized model invocation.

The request may use only bounded server-prepared material derived from the frozen cognitive state and verified Context.

Model output becomes a candidate Draft only after:

```text
same-turn binding validation
late-result check
bounded size / contract validation
```

Model output is never Fact, Policy, Memory, or authority.

---

## 23. Verification / Critic

D136 reuses D133:

```text
CognitiveVerificationCoordinator
CognitiveVerificationArtifact
CognitivePublicationGateArtifact
```

D136 does not create a competing verification vocabulary.

D133 result values remain:

```text
pass
revise
insufficient_evidence
invalid_cognition
```

Critic model assistance, when required, is advisory and must pass through the same fresh authorization boundary.

---

## 24. Bounded Revision

Revision policy:

```text
verification = pass
→ proceed toward publication

verification = revise
and revision_count = 0
→ exactly one REVISION generation may occur

verification = revise
and revision_count = 1
→ critic exhausted
→ no third Draft generation

verification = insufficient_evidence
→ bounded insufficient result

verification = invalid_cognition
→ fail closed
```

After Revision #1, an optional POST_REVISION_CRITIC may run only when required by server-owned policy and budget permits.

There is no third autonomous revision.

---

## 25. Critic Unavailability

If a required Critic cannot run because of:

```text
deadline
provider/runtime failure
open D136 turn-local circuit breaker
authorization failure
binding mismatch
```

D136 must not silently treat Critic as PASS.

Use:

```text
CognitiveFailureCode.CRITIC_UNAVAILABLE
```

or a stricter already-applicable failure code.

Only a server-owned task policy may permit deterministic-only verification for an eligible task class.

---

## 26. Publication Boundary

D136 does not independently decide factual correctness.

Publication eligibility comes from D133 Publication Gate.

D136 coordinates the transition:

```text
verified Draft
↓
D133 Publication Gate
↓
eligible / bounded insufficiency / blocked
```

No blocked or revision-required Draft may be persisted as a normal successful assistant response.

---

## 27. Communication / Response Boundary

D136 reuses existing Chat/response formatting foundations.

The existing normal-chat rendering logic must be exposed through a narrow side-effect-free rendering seam rather than copied into D136.

D136 must not duplicate Context rendering or legacy provider formatting.

D136 may orchestrate final output, but Conversation persistence remains owned by existing conversation persistence code.

---

## 28. Conversation Persistence Boundary

D136 does not create a new Conversation repository or Message writer.

The live normal-chat integration must preserve the existing transaction/persistence boundary.

Required rule:

```text
only a non-stale publication-eligible final response
may proceed to normal assistant-message completion
```

A failed/insufficient turn may use an explicitly bounded safe response path according to existing response contracts.

---

## 29. Experience Boundary

D134 ExperienceCandidate formation is a bounded post-turn hook.

D136 may request ExperienceCandidate formation only from terminal safe metadata.

If ExperienceCandidate formation fails after a user turn already reached successful terminal publication:

```text
the user turn remains successful
```

D134 failure must not retroactively change:

```text
COMPLETED → FAILED
```

ExperienceCandidate still cannot become Memory, Policy, routing, Prompt rewrite, model selection, or code modification.

---

## 30. Executive Trace

D136 creates bounded safe orchestration trace metadata.

Allowed examples:

```text
sequence
CognitiveTurnState
organ / stage identity
stage status
safe reason code
invocation purpose
invocation ordinal
plan digest
safe adapter/model/profile identifiers
artifact digests
revision count
publication disposition
terminal state
failure code
```

Forbidden trace content:

```text
raw owner prompt
raw model prompt
raw provider request/response body
hidden chain-of-thought
system prompt
provider secret
API key
OAuth token
credential
raw Memory content
raw Context text
raw Knowledge content
full Draft text
arbitrary exception detail
```

D136 trace is audit/debug metadata, not private reasoning.

---

## 31. Determinism

For identical trusted inputs, frozen cognitive artifacts, server policy, authorized binding state, and modeled dependency outcomes, D136 must produce the same:

```text
stage ordering
invocation-purpose ordering
revision eligibility
binding-continuity decision
publication transition
normalized failure classification
executive artifact structure
```

Wall-clock/monotonic observations are operational inputs and are not cognitive reasoning.

No random model-selection heuristic is permitted.

---

## 32. Failure Semantics

D136 reuses D126 failure vocabulary where applicable.

At minimum D136 must distinguish:

```text
TURN_IN_PROGRESS
TURN_DEADLINE_EXCEEDED
CONTEXT_UNSTABLE
INVALID_COGNITION
INSUFFICIENT_EVIDENCE
CRITIC_UNAVAILABLE
STALE_LATE_RESULT
CONTRACT_VIOLATION
```

Dependency-specific provider exception details must be normalized before entering executive trace or owner-facing output.

Failure of one stage must remain attributable to that stage.

---

## 33. Fail-Closed Rules

D136 must fail closed when it cannot prove:

```text
valid same-turn binding
valid Context binding
valid stage dependency
valid fresh authorization
valid runtime timeout source
sufficient remaining budget
same binding policy across later invocations
valid revision count
valid D133 publication state
non-stale result
```

D136 must not fabricate missing organ output or silently skip a required stage.

---

## 34. No Autonomous Agent Loop

D136 V1 explicitly excludes:

```text
open-ended self-planning
recursive self-prompting
dynamic tool acquisition
autonomous task creation
background cognition
unbounded Critic loops
self-modifying execution graphs
self-editing prompt/policy/code
automatic Experience promotion
```

The Executive is a bounded state machine.

---

## 35. No New Side-Effect Authority

D136 does not authorize:

```text
Tool execution
Module execution
Plugin execution
connector writes
Calendar mutation
email sending
file mutation
project mutation
Memory mutation
model download/delete
Local AI control
```

If cognition recommends an external action, that action remains subject to its existing explicit planning/approval/execution boundary.

---

## 36. Live Normal-Chat Integration

D136 V1 is not a test-only runtime.

The existing normal-chat route already reaches:

```text
CommandInputPipeline
↓
CommandOrchestrator
↓
ExecutionPlanner
↓
ExecutionGuard
↓
AIRuntime
↓
authorized AI adapter
↓
ConversationService
```

D136 must integrate into this existing route without introducing a second normal-chat API.

No `backend/app/api/v1/chat.py` modification is authorized by D136 Rev 0.1.

The existing route continues to call `CommandOrchestrator`; dependency composition supplies the D136 Executive.

---

## 37. Rendering Seam

`ChatService` may receive one narrow additive, side-effect-free rendering API so D136 can reuse the exact existing Context/Reasoning/Planning/Decision/Goal prompt construction without invoking a provider.

Existing provider-calling methods must retain backward compatibility.

The rendering seam:

```text
formats only
performs no provider call
performs no routing
performs no authorization
performs no persistence
```

---

## 38. Conversation Seam

`ConversationService` may be narrowly refactored so D136 can coordinate:

```text
Context acquisition/freeze
deterministic cognitive preparation
user-message persistence
final assistant-message completion
```

without duplicating repository or Context logic.

The refactor must preserve existing transaction semantics.

D136 must not create a second conversation persistence service.

---

## 39. Command Orchestrator Seam

`CommandOrchestrator` remains the normal-chat application orchestration entrypoint.

D136 may replace the current single-call normal-chat execution sequence inside `process_chat()` with delegation to the injected Cognitive Executive.

Tool execution behavior in `CommandOrchestrator.execute_tool()` is outside D136 and must remain unchanged.

---

## 40. Dependency Wiring Seam

`backend/app/api/dependencies.py` may compose:

```text
CognitiveInvocationCoordinator
CognitiveExecutive
trusted Cloud AI timeout value
LocalAIProfileResolver
ExecutionPlanner
ExecutionGuard
AIRuntime
existing cognitive services
ConversationService
ChatService
```

Dependency construction performs no model call.

No new route is created.

---

## 41. Exact Implementation Scope

After separate Owner implementation authorization, D136 Rev 0.1 implementation changes exactly **9 paths**:

```text
NEW    backend/app/contracts/cognitive_executive.py
NEW    backend/app/services/cognitive_invocation.py
NEW    backend/app/services/cognitive_executive.py

MODIFY backend/app/services/chat.py
MODIFY backend/app/services/conversations.py
MODIFY backend/app/services/command_orchestrator.py
MODIFY backend/app/api/dependencies.py

NEW    backend/tests/test_d136_cognitive_executive.py
NEW    backend/tests/test_d136_cognitive_executive_security.py
```

Any tenth implementation path:

```text
STOP
→ dependency / contradiction report
→ D136 design amendment review
→ Owner approval required
```

No implementation path may be added merely for convenience.

---

## 42. Explicitly Unmodified Production Areas

D136 Rev 0.1 implementation must not modify:

```text
backend/app/contracts/cognitive_brain.py
backend/app/contracts/cognitive_working_state.py
backend/app/intelligence/context/cognitive.py
backend/app/services/cognitive_working_state.py

backend/app/contracts/cognitive_input_semantics.py
backend/app/services/cognitive_input_semantics.py
backend/app/contracts/cognitive_context_memory.py
backend/app/services/cognitive_context_memory.py
backend/app/contracts/cognitive_reasoning_prediction.py
backend/app/services/cognitive_reasoning_prediction.py
backend/app/contracts/cognitive_planning_decision_goal.py
backend/app/services/cognitive_planning_decision_goal.py
backend/app/contracts/cognitive_metacognition.py
backend/app/services/cognitive_metacognition.py
backend/app/contracts/cognitive_verification.py
backend/app/services/cognitive_verification.py
backend/app/contracts/cognitive_experience.py
backend/app/services/cognitive_experience.py
backend/app/contracts/cognitive_model_intelligence.py
backend/app/services/cognitive_model_intelligence.py

backend/app/services/execution_planner.py
backend/app/services/execution_guard.py
backend/app/services/ai_runtime.py

backend/app/services/ai_brain_routing.py
backend/app/services/ai_router.py
backend/app/services/local_ai_profile.py

backend/app/intelligence/pipeline/pipeline.py
backend/app/intelligence/protocols/domain_step.py
backend/app/intelligence/orchestrator/knowledge_orchestrator.py

backend/app/api/v1/chat.py

database
ORM models
repositories
Alembic
provider implementations
AI adapters
Tool runtime
Module runtime
Plugin runtime
```

If D136 cannot be implemented without modifying an item above:

```text
STOP
```

and report the exact contradiction.

---

## 43. Functional Test Contract

Exact file:

```text
backend/tests/test_d136_cognitive_executive.py
```

Required functional matrix: **F01–F56**.

```text
F01 construct valid Executive outcome
F02 Executive envelope requires COGNITIVE_EXECUTIVE
F03 exact executive artifact type/version
F04 completed terminal outcome valid
F05 failed terminal outcome valid
F06 insufficient terminal outcome valid
F07 trace event ordering deterministic
F08 trace event count bounded
F09 safe reason-code collection bounded
F10 revision count reuses D126 maximum

F11 PRIMARY_SYNTHESIS is first model invocation
F12 PRIMARY_SYNTHESIS occurs at most once
F13 CRITIC occurs at most once
F14 REVISION occurs at most once
F15 POST_REVISION_CRITIC occurs at most once
F16 total model invocations never exceed four
F17 draft generations never exceed two
F18 no Critic when policy does not require it
F19 no Revision after PASS
F20 one Revision permitted after first REVISE

F21 second REVISE produces critic-exhausted terminal handling
F22 insufficient evidence maps to bounded insufficient outcome
F23 invalid cognition fails closed
F24 required Critic unavailable does not become PASS
F25 optional deterministic-only verification follows server policy only
F26 publication eligible completes normally
F27 blocked publication cannot complete normally
F28 revision-required publication cannot complete before revision
F29 bounded-insufficiency disposition maps coherently
F30 Experience failure after successful publication does not fail turn

F31 every invocation calls planner
F32 every invocation calls guard
F33 every invocation calls AIRuntime only after authorization
F34 fresh planning object required per invocation
F35 fresh authorization object required per invocation
F36 distinct invocation request identity per call
F37 first authorized binding captured
F38 later identical authorized binding accepted
F39 later provider/adapter switch rejected
F40 later model/profile switch rejected

F41 Local AI effective timeout derived from authorized D125 profile
F42 Cloud AI effective timeout supplied by trusted server wiring
F43 unknown effective timeout fails closed
F44 timeout greater than remaining budget prevents invocation
F45 expired deadline before stage fails
F46 result before deadline accepted
F47 result after deadline rejected as stale
F48 terminal turn rejects later provider result
F49 stale lease rejects attachment
F50 same-turn Workspace/Conversation/Project binding preserved

F51 Chat rendering seam formats without provider call
F52 Conversation preparation preserves Context snapshot semantics
F53 Conversation completion persists only accepted final output
F54 CommandOrchestrator delegates normal chat to D136 Executive
F55 tool execution path remains unchanged
F56 dependency composition constructs Executive without network/model call
```

---

## 44. Security Test Contract

Exact file:

```text
backend/tests/test_d136_cognitive_executive_security.py
```

Required security matrix: **S01–S96**.

```text
S01 wrong Executive producer rejected
S02 wrong artifact type rejected
S03 wrong contract version rejected
S04 wrong turn binding rejected
S05 wrong Workspace binding rejected
S06 wrong Context digest rejected
S07 malformed trace sequence rejected
S08 trace count overflow rejected
S09 malformed safe reason code rejected
S10 reason-code overflow rejected

S11 arbitrary invocation purpose rejected
S12 fifth invocation rejected
S13 second PRIMARY_SYNTHESIS rejected
S14 second CRITIC rejected
S15 second REVISION rejected
S16 second POST_REVISION_CRITIC rejected
S17 third Draft generation rejected
S18 revision count >1 rejected
S19 model output cannot create invocation purpose
S20 user input cannot create invocation purpose

S21 invocation cannot bypass planner
S22 invocation cannot bypass guard
S23 invocation cannot call raw provider
S24 invocation cannot call raw adapter directly
S25 blocked authorization cannot reach AIRuntime
S26 rejected authorization cannot reach AIRuntime
S27 authorization request mismatch rejected
S28 plan digest mismatch rejected
S29 prior authorization reuse rejected
S30 prior bound adapter reuse as later authority rejected

S31 later adapter switch fails closed
S32 later provider switch fails closed
S33 later model switch fails closed
S34 later profile switch fails closed
S35 later task-domain switch fails closed
S36 later Workspace switch fails closed
S37 D135 preferred-model inference absent
S38 D135 ranking authority absent
S39 D135 unknown evidence grants no authority
S40 D135 conflicted evidence grants no authority

S41 Local profile timeout cannot be supplied by model
S42 Cloud timeout cannot be supplied by model
S43 user timeout value cannot override server timeout
S44 missing trusted timeout source fails closed
S45 non-finite timeout rejected
S46 non-positive timeout rejected
S47 timeout above server bound rejected
S48 insufficient remaining budget prevents invocation
S49 expired deadline prevents invocation
S50 organ cannot extend deadline

S51 late PRIMARY_SYNTHESIS result rejected
S52 late CRITIC result rejected
S53 late REVISION result rejected
S54 late POST_REVISION_CRITIC result rejected
S55 terminal COMPLETED state rejects late mutation
S56 terminal FAILED state rejects late mutation
S57 terminal INSUFFICIENT state rejects late mutation
S58 stale result cannot publish
S59 stale result cannot persist assistant Message
S60 stale result cannot create authoritative Experience outcome

S61 stale lease rejected
S62 duplicate active turn rejected
S63 cross-conversation lease use rejected
S64 cross-workspace lease use rejected
S65 project binding mismatch rejected
S66 ContextSnapshot rebinding rejected
S67 post-freeze Context refresh absent
S68 model-triggered Context refresh absent
S69 Critic-triggered Context refresh absent
S70 D136 creates no second concurrency registry

S71 Critic unavailable never becomes PASS
S72 first REVISE permits max one revision
S73 second REVISE creates no third model loop
S74 invalid cognition blocks substantive publication
S75 insufficient evidence cannot be upgraded to PASS
S76 blocked Publication Gate cannot be overridden
S77 model cannot override Publication Gate
S78 Executive cannot synthesize missing D133 artifact
S79 Experience failure cannot rewrite successful terminal state
S80 ExperienceCandidate cannot modify routing/policy/memory

S81 Executive trace contains no raw owner prompt
S82 Executive trace contains no raw model prompt
S83 Executive trace contains no raw provider response
S84 Executive trace contains no hidden chain-of-thought
S85 Executive trace contains no system/provider prompt
S86 Executive trace contains no credential/API key/OAuth token
S87 Executive trace contains no raw Memory content
S88 Executive trace contains no raw Context/Knowledge text

S89 production D136 modules import no provider implementation
S90 production D136 modules hold no raw provider client
S91 no DB/ORM/repository persistence introduced by D136 modules
S92 no scheduler/background worker/thread-pool cognitive loop introduced
S93 no automatic provider/model/profile fallback surface
S94 no Tool/Module/Plugin/connector execution authority surface
S95 no modification of ExecutionPlanner/ExecutionGuard/AIRuntime required
S96 exact nine-path implementation scope enforced
```

---

## 45. Exact Targeted Historical Regression

Exactly **37 historical test files**:

```text
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
backend/tests/test_d131_cognitive_planning_decision_goal.py
backend/tests/test_d131_cognitive_planning_decision_goal_security.py
backend/tests/test_d132_cognitive_metacognition.py
backend/tests/test_d132_cognitive_metacognition_security.py
backend/tests/test_d133_cognitive_verification.py
backend/tests/test_d133_cognitive_verification_security.py
backend/tests/test_d134_cognitive_experience.py
backend/tests/test_d134_cognitive_experience_security.py
backend/tests/test_d135_cognitive_model_intelligence.py
backend/tests/test_d135_cognitive_model_intelligence_security.py

backend/tests/test_execution_planner.py
backend/tests/test_execution_guard.py
backend/tests/test_ai_runtime.py
backend/tests/test_ai_runtime_dependency_wiring.py
backend/tests/test_ai_runtime_e2e.py

backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
backend/tests/test_d105_task_aware_ai_routing_integration.py
backend/tests/test_d105_task_aware_ai_routing_security.py
backend/tests/test_d111_ai_brain_routing_contract.py
backend/tests/test_d111_ai_brain_routing_service.py
backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py

backend/tests/test_pipeline.py
backend/tests/test_knowledge_pipeline_regression.py
```

Historical tests may not be edited to make D136 pass.

---

## 46. Full Regression

After D136 targeted tests and exact historical regression pass:

```text
run full backend regression
```

No pre-existing failing test may be silently excluded.

Any unrelated environmental failure must be separately identified and reproduced before acceptance.

---

## 47. Implementation Validation Protocol

```text
1. verify branch main
2. verify exact D135 baseline / expected frozen-spec parent
3. verify origin/main synchronization
4. verify working tree state
5. verify frozen D136 spec SHA
6. verify exact nine implementation paths
7. run D136 functional F01–F56
8. run D136 security S01–S96
9. run exact 37-file targeted historical regression
10. run full backend regression
11. verify no forbidden production path changed
12. verify final implementation hashes / scope
13. Owner Guided Acceptance
14. separate local implementation commit authorization
15. independent local implementation commit verification
16. separate normal implementation push authorization
17. independent remote implementation verification
18. D136 close
```

No stage implies authorization for the next stage.

---

## 48. Owner Guided Acceptance Intent

At minimum the Owner must be able to confirm:

```text
A. D136 is deterministic orchestration, not an autonomous agent.
B. D136 does not own routing/model/profile authority.
C. Every model call receives fresh Planner + Guard authorization.
D. No hidden provider/model/profile fallback occurs.
E. Maximum model invocations are four.
F. Maximum Draft generations are two.
G. Maximum revision count is one.
H. Turn deadline is server-owned and cannot be extended by cognition.
I. Runtime timeout must fit within remaining budget.
J. Late/stale results cannot mutate or publish.
K. D128 same-conversation turn exclusion remains authoritative.
L. D129 frozen Context cannot be silently refreshed.
M. D133 Verification / Publication Gate remains authoritative.
N. D134 Experience failure cannot retroactively fail a successful turn.
O. D135 knowledge cannot become routing authority.
P. Existing Conversation persistence remains the sole persistence boundary.
Q. D136 trace contains safe metadata, not hidden reasoning/raw secrets.
R. Tools/Modules/Plugins/connectors receive no new authority.
S. Normal Chat is integrated through existing CommandOrchestrator route.
T. ExecutionPlanner, ExecutionGuard, and AIRuntime remain unchanged.
```

---

## 49. Design-Freeze Repository Scope

D136 Repository Design-Freeze Rev 0.1 changes exactly one path:

```text
NEW docs/specs/D136_COGNITIVE_EXECUTIVE_INTEGRATED_BRAIN_RUNTIME_V1.md
```

During Design Freeze artifact creation:

```text
NO implementation code change
NO test change
NO existing spec modification
NO commit unless separately authorized
NO push
NO reset
NO rebase
NO force / force-with-lease
```

Any second changed path:

```text
FAIL / STOP
```

---

## 50. Current Gate State

```text
D135:
COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED

D135 BASELINE:
fc4a5915043397877a9a37692861183ab54126cc

D136 DESIGN RECONCILIATION A–P:
APPROVED

D136 SEMANTIC DESIGN FREEZE:
PASS

D136 INDEPENDENT SEMANTIC REVIEW:
PASS

D136 REPOSITORY BASELINE:
VERIFIED

D136 IMPLEMENTATION PLANNING / EXACT-SCOPE RECONCILIATION:
PASS

D136 REPOSITORY DESIGN-FREEZE ARTIFACT REV 0.1:
CANDIDATE / LOCAL CREATION AUTHORIZED BY OWNER REQUEST

D136 IMPLEMENTATION:
NOT AUTHORIZED / NOT STARTED

IMPLEMENTATION CODE CHANGE:
NONE

DESIGN-FREEZE COMMIT:
NOT AUTHORIZED / NOT CREATED

PUSH:
NOT AUTHORIZED / NOT PUSHED
```

---

## 51. Gate After Local Artifact Creation

After the exact one-path local artifact is created:

```text
Independent local frozen-spec verification
↓
Owner design-freeze commit authorization
↓
independent local design-freeze commit verification
↓
Owner normal design-freeze push authorization
↓
independent remote design-freeze verification
↓
Owner D136 implementation authorization
```

Implementation must not begin before those gates complete.

---

**End of D136 Cognitive Executive / Integrated Brain Runtime V1 — Design Freeze Rev 0.1**
