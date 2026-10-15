# D137 — Newborn Brain Integration & Security Review V1

**Status:** DESIGN FROZEN — Rev 0.1
**Architecture phase:** Brain Formation / Birth Review
**Canonical implementation baseline:** `e32df6de5cdff2a7777f9aa64103259da28e97bb`
**Design Reconciliation:** A–P APPROVED
**Implementation authority:** NOT GRANTED BY THIS DOCUMENT
**Production mutation default:** ZERO
**Autonomous learning:** DISABLED
**Hands / Legs:** NOT STARTED

---

## 1. Purpose

D137 is the final Brain Formation milestone for O-AI Cognitive Brain V1.

D126–D136 created and integrated the bounded cognitive anatomy. D137 does not add a new cognitive organ, model authority, execution authority, persistence system, routing system, learning loop, or autonomous agent. D137 determines whether the already-built Brain V1 satisfies the frozen Birth Criteria through integration, adversarial security, concurrency, late-result, latency/resilience, privacy-hygiene, regression, Owner Guided Acceptance, and a final Birth decision.

The architectural question is:

```text
Are the D126–D136 cognitive organs and cross-cutting controls
coherent, bounded, secure, non-autonomous, and ready to be
declared O-AI Cognitive Brain V1 — BORN?
```

D137 may answer only:

```text
BIRTH DECISION: PASS
```

or:

```text
BIRTH DECISION: FAIL
```

There is no partial-BORN state.

---

## 2. Authoritative Baseline and Source Hierarchy

D137 begins only from exact commit:

```text
e32df6de5cdff2a7777f9aa64103259da28e97bb
```

The repository branch must be:

```text
main
```

At Design Freeze creation and at implementation start, `HEAD` and `origin/main` must equal the baseline above unless a separately approved D137 Design-Freeze commit has become the new expected spec parent.

Source hierarchy:

1. `docs/architecture/O-AI_COGNITIVE_BRAIN_ARCHITECTURE_V1.md`
2. D126–D136 frozen Design/Implementation Specs
3. Existing authority/security/context/memory/runtime contracts
4. Current committed production implementation at the exact baseline
5. D137 frozen tests and validation protocol

A D137 test may not redefine an earlier frozen contract merely to obtain a pass.

---

## 3. D137 Constitutional Boundary

D137 is verification-first and review-only by default.

D137 must not:

```text
add an eighteenth CognitiveOrgan
change CognitiveOrgan serialized values
change D104 AITaskKind authority
change D111 routing authority
change D125 model/profile authority
change Workspace AI policy
change ExecutionPlanner authority
change ExecutionGuard authority
change AIRuntime authority
add provider/model/profile fallback
add hidden retry loops
add Tool / Module / Plugin / connector execution authority
add browser / shell / Git-write authority
add autonomous workflow behavior
add autonomous Memory mutation
add autonomous Experience promotion
add policy learning
add prompt self-rewriting
add self-modifying code
add background cognitive loops
add durable Experience persistence
add a new Context substrate
add a second Working State
add a second Conversation store
persist hidden chain-of-thought
```

A model remains an intelligence engine used by the O-AI brain. It is not sovereign brain authority.

---

## 4. Exact 17-Organ Brain Inventory

D137 freezes the D126 `CognitiveOrgan` closed set as exactly:

```text
SELF_IDENTITY
PERCEPTION
ATTENTION
TASK_UNDERSTANDING
WORKING_MEMORY
MEMORY_RETRIEVAL
CONTEXT_INTELLIGENCE
REASONING
PREDICTION
COGNITIVE_PLANNING
DECISION_GOAL
VERIFICATION_CRITIC
METACOGNITION
MODEL_INTELLIGENCE
EXPERIENCE_SYSTEM
COMMUNICATION_RESPONSE
COGNITIVE_EXECUTIVE
```

No alias, prompt-defined extension, Plugin-defined extension, or eighteenth organ is permitted.

D137 does not require every logical organ to make a model call. Deterministic organs remain deterministic.

---

## 5. Canonical Brain Integration Invariants

The following integrated invariants are mandatory:

```text
One Cognitive Turn
→ one exact Workspace binding
→ one exact Conversation binding
→ one optional exact Project binding
→ one authoritative Task Domain
→ one verified frozen ContextSnapshot
→ one coherent Working State
→ bounded cognition
→ bounded authorized model invocation
→ deterministic/advisory verification
→ Publication Gate
→ transactional response/provenance persistence
→ terminal state
→ best-effort ephemeral Experience eligibility
```

Additional rules:

1. D94–D97 remains the canonical Context substrate.
2. Pre-freeze Context stabilization permits at most one full reacquisition on the exact approved source-change condition.
3. No stale/fresh partial merge is permitted.
4. After freeze, Context is immutable for the turn.
5. `ExecutionContext` or its reconciled successor remains canonical Working State.
6. Normal Chat and Grounded Knowledge must not create incompatible cognitive state models.
7. Interaction Intent, Cognitive Intent, and Task Domain remain separate concepts.
8. Prediction is not Fact.
9. Cognitive Planning is not Execution Planning.
10. Decision support is advisory and is not Owner approval.
11. Metacognition may state `insufficient`, `limited`, or `unknown`.
12. Deterministic verification vetoes outrank advisory Critic output.
13. Automatic revision is bounded to one.
14. Critic exhaustion is terminal/bounded.
15. Invocation purpose is server-owned.
16. Every model invocation receives fresh Planner + Guard authorization.
17. No provider/model/profile fallback is inferred from cognition.
18. One active Cognitive Turn per conversation is enforced.
19. Terminal turns reject late model/Critic results.
20. ExperienceCandidate remains non-authoritative and ephemeral by default.

---

## 6. Exact Model-Invocation and Runtime Bounds

D137 preserves D136 exact limits:

```text
maximum total model invocations = 4
maximum Draft generations       = 2
maximum automatic revisions     = 1
```

Invocation purposes remain server-owned closed-set values.

Each invocation must follow:

```text
CognitiveInvocationCoordinator
        ↓
ExecutionPlanner
        ↓
ExecutionGuard
        ↓
AIRuntime
```

No prior authorization may be reused as fresh authorization for a later model call.

Turn deadline is server-owned. An organ/model/Critic cannot extend it.

A model timeout must fit within the remaining turn budget.

Circuit breaker or runtime failure may improve fail-fast behavior but may not silently change:

```text
provider
adapter
model
profile
Workspace
Task Domain
authority path
```

---

## 7. Context / Working State / Concurrency Boundary

D137 must demonstrate:

```text
source-change before freeze
→ at most one whole Context reacquisition
→ exact request reuse
→ verified frozen ContextSnapshot
→ immutable Context for the remainder of the turn
```

Same-conversation concurrency:

```text
one active Cognitive Turn per workspace + conversation
```

A conflicting turn receives `TURN_IN_PROGRESS` or the frozen equivalent safe conflict outcome.

No queue, sleep, wait-loop, backoff, or autonomous retry is introduced.

Different conversations may proceed independently.

A stale lease cannot release a newer active turn.

---

## 8. Verification / Publication Boundary

D133 remains authoritative for verification and publication quality.

D137 freezes these integrated rules:

```text
deterministic veto > advisory Critic
PASS != execution authority
PASS != Owner approval
Publication Gate != Tool/Module authority
INVALID_COGNITION != uncertainty-only publication
required evidence missing != fabricated confidence
```

One automatic revision is the maximum.

A second unresolved `REVISE` or Critic exhaustion may not create a third Draft generation or an unbounded loop.

---

## 9. Experience / Learning Boundary

D134 remains the Experience boundary.

During Brain Formation:

```text
ExperienceCandidate → Memory             NO
ExperienceCandidate → Policy             NO
ExperienceCandidate → Prompt rewrite     NO
ExperienceCandidate → Model routing      NO
ExperienceCandidate → Code modification  NO
Automatic Experience promotion           NO
Background Experience loop               NO
```

Experience processing occurs outside response criticality.

Experience failure must not retroactively fail a successfully completed primary response.

Any future durable Experience store must first satisfy the already-frozen minimization, secret/PII hygiene, workspace isolation, size, retention, quota, and deduplication requirements.

D137 does not create that store.

---

## 10. Provenance and Birth Criterion #29

D126 defines `CognitiveArtifactEnvelope` and `CognitiveTurnManifest`.

The current Brain V1 implementation may satisfy Birth Criterion #29 through a **minimal Cognitive Turn Manifest or equivalent safe provenance record**.

D137 must not assume that one object contains every conceptual field.

The evidence must demonstrate a coherent safe binding across existing bounded records for:

```text
turn identity
Workspace / Conversation / Project identity
Context snapshot digest
authorized adapter/model/profile binding
verification/publication outcome
terminal state / safe failure code
artifact/reference digests
```

Equivalent-record evidence is acceptable only when all parts are cryptographically/reference-bound or exact turn/binding-bound and cannot be silently mixed across turns.

Raw request text, raw response text, raw Context/Memory/Knowledge text, credentials, provider secrets, system prompts, or hidden chain-of-thought are forbidden from the safe provenance projection.

Failure to demonstrate this equivalence is a **Birth blocker**.

---

## 11. Transactional Response Completion and Birth Criterion #34

D137 preserves the existing response transaction principle:

```text
Final Response
+
Assistant Message persistence
+
required ContextSnapshot / provenance persistence
+
commit
```

Failure requires rollback.

A provider/model answer alone does not define a completed Cognitive Turn.

D137 must test that persistence failure prevents a `COMPLETED` terminal outcome.

D137 does not introduce a second persistence system.

---

## 12. Benchmark Readiness — Birth Criterion #41

D137 does not create an intelligence score, calibrated confidence score, model ranking, preferred model, or Learning policy.

D137 demonstrates only that a future Brain Benchmark baseline **can be established** from existing safe measurement surfaces.

A D137 test-only benchmark-readiness projection may contain bounded fields such as:

```text
authoritative task kind
terminal state
safe failure class
Context snapshot digest/reference
authorized model binding reference
invocation count
Draft generation count
revision count
verification result
publication disposition
```

It must not contain:

```text
raw Owner prompt
raw model prompt
raw provider response
raw final response text
raw Context / Memory / Knowledge text
hidden reasoning / chain-of-thought
model score
model ranking
preferred-model authority
```

The production benchmark contract belongs to the future Learning & Development phase.

---

## 13. D137 Exact Design-Freeze Repository Scope

Design Freeze Rev 0.1 changes exactly one new path:

```text
docs/specs/D137_NEWBORN_BRAIN_INTEGRATION_SECURITY_REVIEW_V1.md
```

No other path is authorized by Design Freeze.

Design Freeze does not authorize implementation, commit, or push.

---

## 14. D137 Exact Implementation Scope

After the Design Freeze is separately committed/pushed and after separate Owner implementation authorization, D137 implementation scope is exactly three **new test files**:

```text
backend/tests/test_d137_newborn_brain_integration.py
backend/tests/test_d137_newborn_brain_security.py
backend/tests/test_d137_newborn_brain_resilience.py
```

Default production modifications:

```text
ZERO
```

Historical test modifications:

```text
ZERO
```

Fourth implementation path:

```text
STOP
→ defect / contradiction report
→ Owner amendment review
```

Any required production edit:

```text
STOP
→ identify exact Birth blocker
→ identify exact frozen rule/test proving the blocker
→ propose exact additional path(s)
→ separate Owner amendment approval
→ only then may production mutation occur
```

D137 tests may not be weakened to hide a production defect.

---

## 15. Functional Integration Test Contract

Exact file:

```text
backend/tests/test_d137_newborn_brain_integration.py
```

Exact count:

```text
F01–F64
64 integration tests
```

Frozen matrix:

```text
F01 exact CognitiveOrgan closed set contains 17 values
F02 no eighteenth CognitiveOrgan exists
F03 each organ value maps to an existing bounded D126–D136 contract or canonical response boundary
F04 D126 constitutional invariants remain source-compatible
F05 CognitiveArtifactEnvelope version/provenance fields remain bounded
F06 cross-organ artifact digests are stable metadata rather than authority
F07 cognitive turn binding preserves exact Workspace
F08 cognitive turn binding preserves exact Conversation
F09 optional Project binding is exact and immutable for the turn
F10 cross-binding state cannot be merged into one turn
F11 D94–D97 Context remains the substrate used by D129/D136
F12 D136 performs one Context stabilization/freeze entry per turn
F13 final Working State Context digest equals the frozen snapshot digest
F14 post-freeze stages consume the same snapshot identity
F15 source-change stabilization performs at most one whole reacquisition
F16 canonical Working State remains ExecutionContext-compatible
F17 D127–D133 cognitive artifacts attach coherently to one Working State
F18 Normal Chat uses the D136 Cognitive Executive on the canonical server path
F19 compatibility/override path does not create a second cognitive state model
F20 Grounded Knowledge historical pipeline remains compatible with shared state foundations
F21 Interaction Intent remains separate from Cognitive Intent
F22 Cognitive Intent remains separate from authoritative AITaskKind
F23 authoritative Task Domain remains D104 AITaskKind
F24 Prediction artifact remains explicitly typed as prediction rather than fact
F25 Reasoning and Prediction provenance remain distinguishable
F26 Cognitive Planning artifact remains distinct from ExecutionPlan
F27 Cognitive Planning never becomes execution authorization
F28 Decision/Goal output remains advisory
F29 Decision/Goal output cannot grant Owner approval
F30 Metacognition can represent insufficient
F31 Metacognition can represent limited
F32 Metacognition can represent unknown
F33 deterministic verification veto has priority over advisory Critic
F34 valid verification PASS is represented separately from publication disposition
F35 Publication Gate remains the final response-quality gate
F36 deterministic invalid cognition cannot become ordinary eligible publication
F37 automatic revision count is bounded to one
F38 Critic exhaustion has explicit terminal behavior
F39 Critic exhaustion cannot create a third draft/revision loop
F40 invocation purpose is server-owned closed-set metadata
F41 every model invocation passes through CognitiveInvocationCoordinator
F42 every invocation obtains fresh ExecutionPlanner + ExecutionGuard authorization
F43 maximum total model invocations is four
F44 maximum draft generations is two
F45 safe provenance can bind turn + workspace + conversation + project + Context digest
F46 safe provenance can bind authorized adapter/model/profile metadata
F47 safe provenance can bind verification/publication result through equivalent bounded records
F48 safe provenance can bind terminal state/failure code
F49 provenance equivalence uses references/digests without raw hidden reasoning
F50 D134 Experience formation consumes coherent terminal provenance
F51 ExperienceCandidate remains ephemeral by default
F52 Experience hygiene/retention policy exists before any durable Experience store
F53 assistant Message and required ContextSnapshot complete through one transaction boundary
F54 persistence failure rolls back required response provenance
F55 provider/model success alone does not mark the turn completed before persistence
F56 D136 final outcome follows successful publication persistence
F57 brain/runtime failures normalize to bounded safe failure behavior
F58 benchmark-readiness projection can record authoritative task kind without raw prompt
F59 benchmark-readiness projection can record terminal state/failure class
F60 benchmark-readiness projection can record Context snapshot digest/reference
F61 benchmark-readiness projection can record authorized model binding references
F62 benchmark-readiness projection can record invocation/draft/revision counts
F63 benchmark-readiness projection can record verification/publication disposition
F64 benchmark-readiness projection contains no score, ranking, raw response, raw Context, or hidden reasoning
```

---

## 16. Security Test Contract

Exact file:

```text
backend/tests/test_d137_newborn_brain_security.py
```

Exact count:

```text
S01–S96
96 security tests
```

Frozen matrix:

```text
S01 cross-workspace Cognitive Self binding rejected
S02 cross-conversation Cognitive Self binding rejected
S03 cross-project Cognitive Self binding rejected
S04 malformed turn id rejected
S05 malformed workspace binding rejected
S06 malformed conversation binding rejected
S07 malformed project binding rejected
S08 state from another turn cannot attach
S09 artifact from another workspace cannot attach
S10 artifact Context digest mismatch fails closed
S11 D129 Context uses canonical D94–D97 types rather than a second resolver substrate
S12 post-freeze Context replacement rejected
S13 post-freeze Context removal rejected
S14 post-freeze Memory retrieval replacement rejected
S15 stale/fresh Context partial merge absent
S16 model-triggered Context refresh absent
S17 Critic-triggered Context refresh absent
S18 Context stabilization general retry loop absent
S19 Context stabilization sleep/backoff absent
S20 Context instability fails boundedly
S21 Prediction cannot be represented as authoritative fact
S22 Cognitive Planning cannot become ExecutionPlan
S23 Decision/Goal cannot grant owner approval
S24 Decision/Goal cannot grant execution authorization
S25 metacognition cannot grant publication authority
S26 verification advisory result cannot override deterministic veto
S27 publication result cannot grant tool/module execution authority
S28 cognitive metadata cannot mutate Project
S29 cognitive metadata cannot mutate Memory
S30 cognitive metadata cannot mutate policy/prompt/code
S31 cognitive task metadata cannot override D104 routing authority
S32 D135 cannot rank/select provider
S33 D135 cannot rank/select adapter
S34 D135 cannot rank/select model
S35 D135 cannot rank/select profile
S36 D136 cannot accept model/user-selected invocation purpose
S37 fifth model invocation rejected
S38 third draft generation rejected
S39 second automatic revision rejected
S40 prior authorization cannot be reused as fresh invocation authority
S41 unknown citation/reference cannot silently pass verification
S42 known deterministic conflict cannot silently pass verification
S43 invalid cognition blocks substantive publication
S44 insufficient evidence cannot be upgraded to ordinary PASS
S45 deterministic veto cannot be downgraded to uncertainty-only publication
S46 Critic unavailable/exhausted cannot become PASS
S47 model output cannot override Publication Gate
S48 Executive cannot synthesize missing D133 authority artifact
S49 ExperienceCandidate cannot become Memory automatically
S50 ExperienceCandidate cannot mutate Policy automatically
S51 ExperienceCandidate cannot mutate Prompt automatically
S52 ExperienceCandidate cannot mutate Routing automatically
S53 ExperienceCandidate cannot mutate Code automatically
S54 ExperienceCandidate contains no raw owner request
S55 ExperienceCandidate contains no raw response Draft
S56 ExperienceCandidate contains no raw Context/Memory/Knowledge text
S57 Experience path introduces no durable candidate persistence in Brain V1
S58 Experience durable-design hygiene contract covers secret handling
S59 Experience durable-design hygiene contract covers PII/workspace/size/retention/quota/deduplication
S60 Experience failure cannot rewrite successful primary turn
S61 Executive trace contains no raw owner prompt
S62 Executive trace contains no raw model/system/provider prompt
S63 Executive trace contains no raw provider response
S64 Executive trace contains no hidden chain-of-thought
S65 safe provenance contains no credential/API key/OAuth token
S66 safe provenance contains no raw Memory text
S67 safe provenance contains no raw Context/Knowledge text
S68 equivalent provenance binding uses bounded IDs/digests/reason codes only
S69 Cognitive Organ receives no raw provider client
S70 cognitive production modules import no provider implementation as direct authority
S71 no hidden provider fallback surface
S72 no hidden model fallback surface
S73 no hidden profile fallback surface
S74 no hidden model retry loop
S75 no scheduler/background cognitive learning loop
S76 no autonomous Experience promotion loop
S77 no Tool authority added by Cognitive Executive
S78 no Module/Plugin/connector authority added by Cognitive Executive
S79 no browser/shell/Git-write authority added by Brain V1
S80 ordinary cognition cannot approve an execution action
S81 provider/internal exception text is not exposed as brain failure reason
S82 authorization failure remains bounded/safe
S83 model failure remains bounded/safe
S84 persistence failure remains bounded/safe
S85 workspace isolation historical invariants remain unchanged
S86 Context security historical invariants remain unchanged
S87 Memory governance historical invariants remain unchanged
S88 execution governance historical invariants remain unchanged
S89 D104/D105/D111/D125 routing authority historical invariants remain unchanged
S90 audit/provenance historical invariants remain unchanged
S91 CognitiveOrgan remains exactly 17 values
S92 D137 adds no production runtime/contract/service path
S93 D137 adds no database/migration/repository path
S94 D137 adds no API/frontend/deployment path
S95 D137 focused implementation is exactly three new test files
S96 frozen D137 spec remains unchanged during implementation
```

---

## 17. Resilience / Concurrency / Late-Result Test Contract

Exact file:

```text
backend/tests/test_d137_newborn_brain_resilience.py
```

Exact count:

```text
R01–R48
48 resilience tests
```

Frozen matrix:

```text
R01 expired turn deadline prevents primary synthesis invocation
R02 insufficient remaining budget prevents model invocation
R03 model timeout cannot exceed remaining turn budget
R04 cognition cannot extend the server-owned deadline
R05 Critic cannot extend the server-owned deadline
R06 revision cannot extend the server-owned deadline
R07 budget exhaustion returns bounded terminal failure
R08 deadline path performs no unbounded wait
R09 open/failed runtime breaker fails fast
R10 breaker outcome does not switch provider
R11 breaker outcome does not switch adapter
R12 breaker outcome does not switch model
R13 breaker outcome does not switch profile
R14 breaker outcome does not switch workspace/task domain
R15 model failure performs no hidden retry
R16 model failure cannot create fallback authority
R17 exact context_snapshot_source_changed permits one full reacquisition
R18 non-source-change Context failure is not retried
R19 second source-change failure performs no third resolve
R20 second source-change failure performs no third capture
R21 failed first Context bundle cannot contribute items to final snapshot
R22 failed first Context provenance cannot leak into final snapshot
R23 unresolved stabilization returns CONTEXT_UNSTABLE boundedly
R24 Context instability path cannot hang
R25 first active turn acquires same-conversation lease
R26 concurrent same-conversation turn fails with safe in-progress outcome
R27 concurrent acquire never grants two same-key leases
R28 different conversations may hold independent leases
R29 same conversation UUID in different workspaces does not collide
R30 stale lease release cannot clear newer turn
R31 concurrency guard contains no queue/sleep/backoff
R32 rejected concurrent turn cannot persist assistant output
R33 late PRIMARY_SYNTHESIS result rejected
R34 late CRITIC result rejected
R35 late REVISION result rejected
R36 late POST_REVISION_CRITIC result rejected
R37 terminal COMPLETED turn rejects late mutation
R38 terminal INSUFFICIENT turn rejects late mutation
R39 terminal FAILED turn rejects late mutation
R40 stale result cannot persist/publish/create authoritative Experience
R41 Critic unavailable never becomes PASS
R42 first REVISE may request at most one revision
R43 revision count remains maximum one
R44 second REVISE cannot create third draft loop
R45 Critic exhaustion reaches explicit terminal state
R46 Critic exhaustion path has bounded invocation count and no hang
R47 assistant Message + ContextSnapshot persistence rollback is atomic on failure
R48 persistence failure prevents COMPLETED terminal result
```

### 17.1 Non-flaky timing rule

D137 must not define a hardware-performance SLA.

Deadline/latency tests must prefer:

```text
fake monotonic clocks
deterministic fake runtimes
bounded call-count assertions
explicit terminal-state assertions
bounded thread synchronization only where true contention must be exercised
```

No external provider/network availability may be required for the focused D137 suite.

No arbitrary `sleep()` is permitted as correctness evidence.

---

## 18. Brain V1 Birth Criteria — Exact Evidence Matrix

All 41 criteria are mandatory.

| # | Frozen Birth Criterion | D137 evidence owner |
|---:|---|---|
| 1 | All 17 brain organs have explicit bounded contracts. | D126 + D137 F01–F04 / S91 |
| 2 | Cross-cutting Cognitive Artifact provenance/versioning contracts exist without adding an unnecessary eighteenth organ. | D126 + D137 F05–F06 / S61–S68 |
| 3 | Cognitive Self is bound to exact workspace / conversation / project context. | D127–D129 + D137 F07–F10 / S01–S10 |
| 4 | D94–D97 remains the canonical Context substrate. | D94–D97 + D129 + F11 / S11 |
| 5 | One Cognitive Turn uses one verified frozen ContextSnapshot after any permitted pre-freeze stabilization attempt. | D129 + D136 + F12–F14 / R17–R20 |
| 6 | Context source-change handling is bounded to at most one full reacquisition and never performs partial stale/fresh merges. | D129 + F15 / R21–R24 |
| 7 | `ExecutionContext` or its reconciled successor serves as canonical Working State. | D128 + F16–F17 |
| 8 | Normal Chat and Grounded Knowledge use a coherent shared cognitive-state architecture. | D128/D136 + F18–F20 |
| 9 | Intent/Task semantics are separated into Interaction Intent, Cognitive Intent, and Task Domain. | D127 + F21–F23 |
| 10 | Brain task semantics preserve D104/D125 routing authority unless a separately frozen milestone explicitly changes it. | D104/D125/D127/D135/D136 + S31–S40 |
| 11 | Reasoning artifacts remain safe structured metadata and do not persist hidden chain-of-thought. | D126/D130 + S61–S64 |
| 12 | Prediction is explicitly distinguishable from Fact. | D130 + F24–F25 / S21 |
| 13 | Cognitive Planning remains distinct from Execution Planning. | D131 + F26–F27 / S22 |
| 14 | Decision support remains advisory and cannot grant Owner authority. | D131 + F28–F29 / S23–S24 |
| 15 | Metacognition can return `insufficient`, `limited`, or `unknown`. | D132 + F30–F32 |
| 16 | Cognitive Critic combines deterministic and advisory verification with deterministic veto priority. | D133 + F33–F36 / S41–S44 |
| 17 | Critic revision is bounded to at most one automatic revision. | D133/D136 + F37 / R43 |
| 18 | Critic exhaustion has explicit terminal behavior and cannot create an unbounded loop. | D133/D136 + F38–F39 / R44–R46 |
| 19 | `INVALID_COGNITION` and deterministic vetoes cannot be downgraded into uncertainty-only publication. | D133/D136 + S45–S48 |
| 20 | Model invocation purposes are server-owned, bounded, and mediated through the central authorized invocation boundary. | D126/D136 + F40–F42 / S31–S36 |
| 21 | Maximum draft generations and maximum total model invocations are separately defined and enforced. | D136 + F43–F44 / S37–S40 |
| 22 | No hidden model retry, provider fallback, or model fallback exists. | D126/D136 + S71–S74 / R09–R16 |
| 23 | Cognitive Turn deadlines and expensive-stage budgets are enforced with bounded timeout outcomes. | D136 + R01–R08 |
| 24 | Circuit breakers fail fast without silently changing provider, model, workspace, task domain, or authority path. | D136 + R09–R16 |
| 25 | One active Cognitive Turn per conversation is enforced or an equivalent mechanism proves ordered commits. | D128/D136 + R25–R32 |
| 26 | Late model/Critic results after terminality cannot mutate cognitive or durable response state. | D136 + R33–R40 |
| 27 | D125 model/profile bindings remain server-owned and fail-closed. | D125/D136 + S31–S40 |
| 28 | No Cognitive Organ receives raw provider authority. | D126/D136 + S69–S70 |
| 29 | A minimal Cognitive Turn Manifest or equivalent safe provenance record can bind turn, Context, model authorization, verification outcome, and terminal status without raw hidden reasoning. | D126/D133/D134/D136 + F45–F50 / S61–S68 |
| 30 | ExperienceCandidate cannot auto-promote into Memory, Policy, Prompt, Routing, or Code. | D134 + S51–S56 |
| 31 | ExperienceCandidate is ephemeral by default until a separately frozen persistence contract exists. | D134 + F51 / S57 |
| 32 | Any durable Experience design includes data minimization, secret handling, PII minimization, workspace isolation, size limits, retention, quotas, and deduplication before activation. | D134 hygiene/retention contract + F52 / S58–S60 |
| 33 | Experience processing cannot create an autonomous background learning loop during Brain Formation. | D134 + S75–S78 |
| 34 | Response completion preserves required provenance transactionally. | ConversationService + D136 + F53–F56 / R47–R48 |
| 35 | Brain failures normalize safely without leaking provider internals. | D136 + F57 / S81–S84 |
| 36 | Existing O-AI authority, workspace isolation, execution governance, Memory governance, and Context security invariants remain intact. | Historical authority/isolation regressions + S85–S90 |
| 37 | Brain integration regression tests pass. | D137 F01–F64 + exact 67-file historical + full backend |
| 38 | Brain-specific security tests pass. | D137 S01–S96 |
| 39 | Latency/resilience tests cover timeouts, open breakers, Context instability, same-conversation concurrency, late results, model failure, and Critic exhaustion without hangs. | D137 R01–R48 |
| 40 | Owner Guided Acceptance demonstrates multi-stage cognition without autonomous action. | D137 Owner Guided Acceptance A–L |
| 41 | Brain benchmark baseline can be established for the next Learning & Development phase. | D137 F58–F64 benchmark-readiness projection |

A criterion may use historical evidence only when D137 revalidates the relevant current test/contract against the exact frozen baseline.

No criterion may be marked `PASS` solely because a prior milestone once passed on an older commit.

---

## 19. Exact Historical Regression Set

D137 targeted historical regression is exactly **67 current test files**:

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
backend/tests/test_d136_cognitive_executive.py
backend/tests/test_d136_cognitive_executive_security.py
backend/tests/test_d91_workspace_isolation.py
backend/tests/test_d93_workspace_scope_enforcement.py
backend/tests/test_d93_workspace_derived_scope.py
backend/tests/test_d93_workspace_knowledge_isolation.py
backend/tests/test_d94_context_security.py
backend/tests/test_d95_context_resolution_security.py
backend/tests/test_d96_context_snapshot_security.py
backend/tests/test_d97_context_chat_security.py
backend/tests/test_context_resolver.py
backend/tests/test_context_snapshot.py
backend/tests/test_context_snapshot_persistence.py
backend/tests/test_conversation_memory.py
backend/tests/test_memory_aware_chat.py
backend/tests/test_project_context.py
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
backend/tests/test_d111_ai_brain_runtime_integration.py
backend/tests/test_d111_ai_brain_runtime_security.py
backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py
backend/tests/test_pipeline.py
backend/tests/test_knowledge_pipeline_regression.py
backend/tests/test_command_orchestrator.py
backend/tests/test_api_standardization.py
backend/tests/test_execution_audit.py
backend/tests/test_execution_audit_contract.py
backend/tests/test_durable_execution_audit.py
backend/tests/test_execution_approval_service.py
backend/tests/test_workspace_contract.py
backend/tests/test_context_contract.py
backend/tests/test_context_resolution_contract.py
backend/tests/test_context_provenance_contract.py
backend/tests/test_context_chat.py
backend/tests/test_context_aware_chat_integration.py
```

All 67 paths were revalidated as present on the D137 canonical baseline before this freeze.

Historical tests may not be edited to make D137 pass.

A historical failure must be classified as:

```text
D137 production/Birth defect
or
environment/test-harness issue demonstrated independently
```

It may not be silently excluded.

---

## 20. Full Regression

After all focused D137 tests and the exact 67-file historical regression pass:

```text
run full backend regression
```

Requirements:

```text
0 failed
0 errors
no silently excluded pre-existing failure
```

Normal documented skips may remain skips.

An environmental failure must be reproduced and separated from product correctness before D137 acceptance.

---

## 21. Privacy / Hygiene Review

D137 must demonstrate that cognitive review surfaces do not persist or expose:

```text
hidden chain-of-thought
raw system prompts
raw provider prompts
raw provider responses
API keys
OAuth tokens
credentials
raw Memory bodies
raw Context bodies
raw Knowledge bodies
unnecessary Owner request copies
unnecessary Draft/response copies
```

Safe bounded metadata may include identifiers, enumerations, digests, counts, versions, dispositions, and normalized reason codes.

A privacy/hygiene failure is a Birth blocker.

---

## 22. No-Autonomy Review

D137 must demonstrate that Brain V1 cannot obtain or infer autonomous authority from cognition.

The following implications are forbidden:

```text
Reasoning result      → execution authority
Planning result       → execution authority
Decision result       → Owner approval
Metacognition result  → Publication override
Model Intelligence    → model selection
ExperienceCandidate   → Memory/Policy/Prompt/Routing/Code mutation
Publication PASS      → Tool/Module/Plugin/connector execution
```

Existing explicit Owner approval and execution governance remain separate authorities.

---

## 23. Defect and Amendment Protocol

D137 is a review milestone. Finding a defect is a valid review result.

If a focused, historical, full-regression, or guided-acceptance gate exposes a genuine production defect:

```text
1. STOP the D137 pass sequence.
2. Preserve the failing evidence.
3. Identify affected Birth Criterion numbers.
4. Identify exact production path(s) required for repair.
5. State whether any earlier frozen milestone assumption is contradicted.
6. Produce a D137 Validation/Implementation Amendment proposal.
7. Obtain explicit Owner approval.
8. Only then modify production.
9. Re-run all affected focused + historical + full regression gates.
```

No blind patching.

No test weakening.

No force push.

No reset/rebase used to erase evidence.

---

## 24. Validation Protocol

After separate D137 implementation authorization:

```text
1. verify branch main
2. verify exact D137 frozen-spec parent
3. verify origin/main synchronization
4. verify working tree/index state
5. verify frozen D137 spec SHA256
6. verify exact three-new-test implementation scope
7. compile/import focused D137 tests
8. run D137 integration F01–F64
9. run D137 security S01–S96
10. run D137 resilience R01–R48
11. run exact 67-file historical regression
12. run full backend regression
13. verify zero production/historical-test mutation
14. verify final exact implementation hashes/scope
15. produce Birth Criteria 1–41 evidence ledger
16. Owner Guided Acceptance
17. final Birth Decision
18. separate local implementation commit authorization
19. independent local implementation commit verification
20. separate normal implementation push authorization
21. independent remote implementation verification
22. D137 close / Brain Formation exit
```

No stage implies authorization for the next stage.

---

## 25. Owner Guided Acceptance

Owner Guided Acceptance occurs only after automated validation passes.

At minimum the Owner confirms:

```text
A. Normal Chat uses the integrated cognitive runtime and still behaves as Chat, not as an autonomous agent.
B. A multi-step reasoning/planning response does not create or execute an action merely because cognition recommends one.
C. An insufficient/unknown case can say that information is insufficient rather than fabricate confidence.
D. Workspace/Conversation/Project context remains correctly isolated.
E. Context used for a turn is stable; the response does not silently mix a later Context state.
F. Model/provider selection remains controlled by existing server routing/profile policy.
G. Verification/publication can block or limit unsafe/unsupported cognition.
H. Experience processing causes no visible Memory/Policy/Prompt/Routing/Code mutation.
I. No Tool/Module/Plugin/connector action occurs without the existing explicit action/approval path.
J. Failure behavior exposes bounded safe information rather than provider internals.
K. Multi-stage cognition completes without an observable retry/fallback loop.
L. Brain V1 remains non-autonomous: Autonomous Learning DISABLED; Hands / Legs NOT STARTED.
```

Manual acceptance is not used to prove concurrency/late-result mechanics; those remain automated D137 resilience requirements.

---

## 26. Birth Decision Ledger

D137 final review must emit a ledger with exactly 41 rows:

```text
Criterion
Evidence
Result: PASS | FAIL
Blocker reference when FAIL
```

Final decision:

```text
if every criterion == PASS:
    BIRTH DECISION = PASS
else:
    BIRTH DECISION = FAIL
```

No waived criterion.

No majority vote.

No risk acceptance converts a failing frozen Birth Criterion into PASS without an Architecture amendment.

---

## 27. Birth PASS Exit State

Only if all automated gates, all 41 criteria, and Owner Guided Acceptance pass:

```text
O-AI BRAIN FORMATION
STATUS: COMPLETE

O-AI COGNITIVE BRAIN V1
STATUS: BORN

Autonomous Learning: DISABLED
Hands / Legs:        NOT STARTED
```

This does not mean:

```text
STATUS: MATURE
STATUS: AUTONOMOUS
STATUS: SELF-LEARNING
```

The next architecture phase may then be designed separately:

```text
O-AI LEARNING & DEVELOPMENT
```

---

## 28. Birth FAIL Exit State

If any mandatory criterion fails:

```text
O-AI BRAIN FORMATION
STATUS: INCOMPLETE

O-AI COGNITIVE BRAIN V1
STATUS: NOT BORN
```

D137 must preserve explicit blocker evidence.

The next action is repair/amendment of the exact blocker, not progression into Learning & Development.

---

## 29. Acceptance Criteria

D137 is complete only when all applicable gates pass:

```text
Owner Design Reconciliation A–P                         PASS
D137 Design Freeze                                      PASS
Design Freeze exact one-doc scope                       PASS

Implementation exact three-new-test scope               PASS
Production implementation paths                         ZERO
Historical test modifications                           ZERO
Frozen D137 spec unchanged during implementation        PASS

D137 integration F01–F64                                PASS
D137 security S01–S96                                   PASS
D137 resilience R01–R48                                 PASS

Exact 17-organ inventory                                PASS
D94–D97 canonical Context substrate                     PASS
One frozen ContextSnapshot per turn                     PASS
Maximum Context reacquisition one                       PASS
No stale/fresh merge                                    PASS
Canonical Working State                                 PASS
D104/D111/D125 authority preserved                      PASS
Planner/Guard/AIRuntime authority preserved             PASS
Maximum model invocations four                          PASS
Maximum Draft generations two                           PASS
Maximum automatic revision one                          PASS
No hidden retry/fallback                                PASS
Turn deadlines/budgets bounded                          PASS
Same-conversation exclusion                             PASS
Late-result terminality                                 PASS
Critic exhaustion bounded                               PASS
Experience non-authoritative / ephemeral                PASS
Privacy/hygiene                                         PASS
Transactional response provenance                       PASS
Equivalent safe provenance record                       PASS
Benchmark readiness                                     PASS
No autonomous side-effect authority                     PASS

Exact 67-file historical regression                     PASS
Full backend regression                                 PASS

Birth Criteria 1–41                                     ALL PASS
Owner Guided Acceptance A–L                             PASS
Birth Decision                                          PASS

git diff --check                                        PASS
Exact local implementation commit scope                 PASS
Working tree clean                                      PASS
Separate normal push authorization                      PASS
Independent remote verification                         PASS
```

---

## 30. Explicit Non-Goals

D137 does not build:

```text
Brain Benchmark scoring
calibrated confidence scoring
model ranking
preferred-model selection
Experience accumulation store
Experience promotion engine
Learning policy
Context optimization policy
reasoning-quality self-tuning
longitudinal improvement loop
browser autonomy
workflow autonomy
background autonomous work
Hands
Legs
```

Those belong to separately designed later phases.

---

## 31. Design Freeze Status

```text
D137 NEWBORN BRAIN INTEGRATION & SECURITY REVIEW V1

Design Reconciliation A–P:       PASS
Canonical baseline:              e32df6de5cdff2a7777f9aa64103259da28e97bb
Birth Criteria:                  41 / FROZEN
Functional matrix:               F01–F64 / FROZEN
Security matrix:                 S01–S96 / FROZEN
Resilience matrix:               R01–R48 / FROZEN
Historical regression:           EXACT 67 FILES / FROZEN
Owner Guided Acceptance:         A–L / FROZEN
Birth decision semantics:        FROZEN

Design Freeze repository scope:  EXACTLY 1 NEW SPEC PATH
Implementation default scope:    EXACTLY 3 NEW TEST PATHS
Production changes:              ZERO BY DEFAULT
Historical test changes:         ZERO

IMPLEMENTATION:                  NOT AUTHORIZED
COMMIT:                          NOT AUTHORIZED
PUSH:                            NOT AUTHORIZED
```

---

**End of D137 Newborn Brain Integration & Security Review V1 — Design Freeze Rev 0.1**
