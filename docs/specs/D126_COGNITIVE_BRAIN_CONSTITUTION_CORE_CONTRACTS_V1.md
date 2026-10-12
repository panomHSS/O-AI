# D126 — Cognitive Brain Constitution & Core Contracts V1

**Status:** DESIGN FROZEN - OWNER APPROVED<br>
**Design revision:** Rev 0.2 - FROZEN DESIGN BASELINE<br>
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN<br>
**Architecture freeze commit:** `d16e29d0c239f31e89961e59078c299d7c81ec31`<br>
**Frozen architecture file:** `docs/architecture/O-AI_COGNITIVE_BRAIN_ARCHITECTURE_V1.md`<br>
**D125 baseline parent:** `74b26ef725ef576e24062e6de5f096265ced3301`<br>
**Owner Design Review:** PASS<br>
**Owner approval:** YES<br>
**Implementation:** NOT STARTED<br>
**Code change:** NONE<br>
**Commit:** DESIGN FREEZE COMMIT<br>
**Push:** NOT PUSHED<br>
**Codex:** NOT USED<br>

---

## 1. Purpose

D126 establishes the shared constitutional vocabulary and immutable core data contracts for O-AI Cognitive Brain V1.

D126 does **not** implement cognition. It does not run Perception, Attention, Reasoning, Prediction, Planning, Decision, Metacognition, Critic, Experience, or the Cognitive Executive.

D126 exists so that D127–D137 do not invent incompatible definitions for:

- cognitive organ identity;
- organ status;
- cognitive turn lifecycle;
- server-owned model invocation purpose;
- normalized Architecture-level failure reasons;
- cross-organ artifact provenance;
- minimal cognitive turn metadata;
- workspace binding;
- D104/D125 task-authority compatibility;
- deadline/resource semantics;
- authority separation.

The governing rule is:

> **Cognition may inform authority, but cognition is never authority.**

---

## 2. Reconciliation With Existing O-AI

D126 is evolutionary. Existing authoritative components remain authoritative.

| Existing foundation | D126 treatment |
|---|---|
| `WorkspaceId`, `WorkspaceScope` | Reuse directly. No parallel workspace identity. |
| D94–D97 Context contracts | Preserve unchanged. No parallel Context model/store. |
| `ExecutionContext` | Recognized as the Working State prototype. Convergence belongs to D128. |
| `AITaskKind` | Reuse exactly. No new authoritative task kinds. |
| `ExecutionPlanner` | Remains outside cognition. |
| `ExecutionGuard` | Remains execution authorization boundary. |
| `AIRuntime` | Remains authorization-gated AI execution boundary. |
| `ReasoningService` / `ReasoningPlan` | Preserve as reasoning foundation. |
| `PlanningService` / `PlanningPlan` | Preserve as non-executable planning foundation. |
| `DecisionService` / `DecisionAnalysis` | Preserve as advisory decision foundation. |
| ContextSnapshot persistence | Preserve as existing Context provenance substrate. |

D126 must not introduce:

```text
new Workspace authority
new execution authorization
new Context store
new Memory store
new provider router
new model/profile selector
new AI runtime
new approval mechanism
new autonomous agent
```

---

## 3. D126 Constitutional Invariants

The following rules become directly represented by D126 contracts or D126 tests.

1. Cognitive metadata grants zero execution authority.
2. Model output grants zero routing, policy, Memory, approval, or execution authority.
3. One Cognitive Turn belongs to exactly one `WorkspaceId`.
4. Cross-organ artifacts carry bounded provenance/version identity.
5. Hidden chain-of-thought is neither a contract field nor a persistence target.
6. Deterministic security/integrity vetoes cannot be overridden by model output.
7. D104/D125 `AITaskKind` remains the authoritative task-domain type during Brain Formation.
8. Richer cognitive task descriptions are non-authoritative metadata.
9. Model invocation purpose is server-owned and closed-set.
10. D126 introduces no retry, provider fallback, model fallback, or profile fallback.
11. Turn deadlines are server-owned; cognition cannot extend them.
12. D126 adds no side-effect capability.
13. Experience/learning authority remains outside D126.
14. Browser, workflow, tool, connector, shell, Git-write, and autonomous action remain outside D126.

---

## 4. Exact Production Scope

D126 production implementation scope is frozen to exactly one module:

```text
backend/app/contracts/cognitive_brain.py
```

The module may contain only:

```text
constants / validators

CognitiveOrgan
CognitiveOrganStatus
CognitiveTurnState
CognitiveInvocationPurpose
CognitiveFailureCode

CognitiveArtifactEnvelope
CognitiveTurnManifest

is_terminal_cognitive_turn_state()
```

No service, repository, database model, route, runtime, adapter, provider client, scheduler, or background worker is authorized.

---

## 5. Shared Validation Constants

D126 freezes the following exact limits.

```text
COGNITIVE_ID_MAX_BYTES                  = 512
COGNITIVE_ARTIFACT_TYPE_MAX_BYTES       = 128
COGNITIVE_CONTRACT_VERSION_MAX_BYTES    = 128
COGNITIVE_REFERENCE_DIGEST_MAX_COUNT    = 64
COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT     = 128
COGNITIVE_REVISION_COUNT_MAX            = 1
SHA256_HEX_LENGTH                       = 64
```

Identifiers must:

- be exact `str`;
- be non-empty;
- equal `value.strip()`;
- contain no Unicode control character with category `Cc`;
- fit the relevant UTF-8 byte limit.

Digests must:

- be exact `str`;
- contain exactly 64 characters;
- use lowercase hexadecimal `[0-9a-f]`;
- not be silently lowercased or normalized.

Unknown values fail closed.

---

## 6. `CognitiveOrgan`

Exact closed-set values:

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

Frozen serialized values:

```text
self_identity
perception
attention
task_understanding
working_memory
memory_retrieval
context_intelligence
reasoning
prediction
cognitive_planning
decision_goal
verification_critic
metacognition
model_intelligence
experience_system
communication_response
cognitive_executive
```

Rules:

- no aliases;
- no case folding;
- no prompt-derived values;
- no plugin/tool-defined extension;
- adding an eighteenth organ requires a separately reviewed Architecture amendment.

`CognitiveOrgan` is descriptive only and grants no capability.

---

## 7. `CognitiveOrganStatus`

Exact values:

```text
READY
NOT_APPLICABLE
INSUFFICIENT
FAILED
```

Serialized values:

```text
ready
not_applicable
insufficient
failed
```

This status describes one organ's result for one turn.

It is not:

```text
permission
authorization
approval
retry instruction
provider routing
```

---

## 8. `CognitiveTurnState`

Exact lifecycle vocabulary:

```text
RECEIVED
ACCEPTED
COGNITIVE_LANE
BOUND
CONTEXT_RESOLVING
CONTEXT_FROZEN
THINKING
MODEL_READY
GENERATING
VERIFYING
REVISING
FINALIZING
PERSISTING
COMPLETED
FAILED
INSUFFICIENT
```

Serialized values use lowercase snake case.

Exact terminal states:

```text
COMPLETED
FAILED
INSUFFICIENT
```

D126 provides:

```text
is_terminal_cognitive_turn_state(state) -> bool
```

The helper must:

- require an exact `CognitiveTurnState`;
- return `True` only for the three terminal states;
- perform no mutation or I/O.

D126 defines lifecycle vocabulary only.

Transition enforcement belongs to later runtime integration.

---

## 9. `CognitiveInvocationPurpose`

Exact values:

```text
PRIMARY_SYNTHESIS
CRITIC
REVISION
POST_REVISION_CRITIC
```

Serialized values:

```text
primary_synthesis
critic
revision
post_revision_critic
```

Rules:

- purpose is server-owned;
- prompt, Context, Memory, frontend, model output, plugin, and tool input cannot create a purpose;
- the enum does not itself invoke a model;
- the enum does not select a provider/model/profile;
- no dynamic arbitrary purpose exists.

Architecture-level model limits remain:

```text
maximum draft generations = 2
maximum bounded model invocations = 4
```

Enforcement belongs to later runtime milestones.

---

## 10. `CognitiveFailureCode`

D126 owns only a small Architecture-level closed set:

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

Serialized values:

```text
turn_in_progress
turn_deadline_exceeded
context_unstable
invalid_cognition
insufficient_evidence
critic_unavailable
stale_late_result
contract_violation
```

Rules:

- no provider-specific exception text;
- no credentials or endpoint details;
- no retry/fallback semantics are implied;
- codes are descriptive and non-authoritative;
- subsystem-specific failure vocabularies remain owned by their existing subsystem.

---

## 11. `CognitiveArtifactEnvelope`

Frozen immutable contract:

```text
CognitiveArtifactEnvelope
├── turn_id: str
├── artifact_type: str
├── contract_version: str
├── producer_organ: CognitiveOrgan
├── workspace_id: WorkspaceId
├── context_snapshot_digest: str | None
├── created_at: datetime
├── status: CognitiveOrganStatus
├── input_reference_digests: tuple[str, ...]
└── model_binding_reference: str | None
```

### 11.1 Exact rules

`turn_id`

- validated as bounded identifier;
- server ownership is a runtime invariant; D126 validates shape only.

`artifact_type`

- bounded identifier;
- metadata only;
- never used as an executable dispatch key in D126.

`contract_version`

- bounded identifier;
- exact version label;
- no silent coercion.

`producer_organ`

- exact `CognitiveOrgan`.

`workspace_id`

- exact existing `WorkspaceId`;
- D126 does not accept raw arbitrary workspace strings.

`context_snapshot_digest`

- `None` is permitted for legitimate pre-Context-freeze artifacts;
- when present, must be exact lowercase SHA-256 hex;
- later runtime milestones must require it where the turn has reached `CONTEXT_FROZEN`.

`created_at`

- exact `datetime`;
- must be timezone-aware;
- normalized to UTC inside the immutable contract;
- naive datetimes fail closed.

`status`

- exact `CognitiveOrganStatus`.

`input_reference_digests`

- accepts a tuple or finite sequence of digest strings;
- converted once to immutable tuple;
- maximum 64 entries;
- each entry exact SHA-256 lowercase hex;
- duplicates rejected;
- source order preserved;
- raw Context/Memory text is not accepted through this field.

`model_binding_reference`

- optional;
- when present, exact SHA-256 lowercase hex;
- it references authorized model-binding metadata but grants no runtime authority.

### 11.2 Explicitly forbidden fields

The envelope must not have fields for:

```text
owner_approval
execution_authorization
execution_plan
api_key
credential
provider_secret
raw_prompt
system_prompt
hidden_reasoning
raw_context
memory_value
tool_permission
```

---

## 12. `CognitiveTurnManifest`

D126 includes a **data contract only**.

No repository or persistence path is added.

Frozen minimal immutable contract:

```text
CognitiveTurnManifest
├── turn_id: str
├── workspace_id: WorkspaceId
├── conversation_id: str
├── project_id: str | None
├── terminal_state: CognitiveTurnState | None
├── context_snapshot_digest: str | None
├── task_semantics_version: str
├── authoritative_ai_task_kind: AITaskKind | None
├── authorized_adapter_id: str | None
├── authorized_model_id: str | None
├── authorized_profile_id: str | None
├── revision_count: int
├── failure_code: CognitiveFailureCode | None
└── artifact_digests: tuple[str, ...]
```

### 12.1 Exact rules

`turn_id`, `conversation_id`, optional `project_id`

- bounded identifiers;
- no normalization beyond validation.

`terminal_state`

- `None` while the turn is non-terminal;
- when present, must be one of `COMPLETED`, `FAILED`, `INSUFFICIENT`;
- a non-terminal value in this field fails closed.

`context_snapshot_digest`

- optional;
- exact lowercase SHA-256 when present.

`task_semantics_version`

D126 freezes the initial value:

```text
o-ai.cognitive-task-semantics.v1
```

D126 does not define richer authoritative routing kinds.

`authoritative_ai_task_kind`

- optional exact existing `AITaskKind`;
- current valid values remain exactly:
  - `GENERAL_CHAT`
  - `SOFTWARE_ENGINEERING`
- no string alias or cognitive-task-description substitution.

`authorized_adapter_id`, `authorized_model_id`, `authorized_profile_id`

- optional bounded metadata copied from an already-authorized runtime path;
- the manifest does not perform or grant authorization;
- the manifest cannot be supplied to `AIRuntime` as authorization evidence.

`revision_count`

- exact `int`;
- `bool` rejected;
- valid range `0..1`;
- reflects the Architecture maximum of one automatic revision;
- it does not trigger revision.

`failure_code`

- optional exact `CognitiveFailureCode`.

`artifact_digests`

- immutable tuple;
- maximum 128;
- exact SHA-256 lowercase hex;
- duplicates rejected;
- order preserved.

### 12.2 Cross-field consistency

D126 proposes these deterministic validations:

```text
terminal_state is None
    => failure_code may be None or descriptive only in intermediate construction;
       D126 does not infer lifecycle transition.

terminal_state == COMPLETED
    => failure_code must be None.

terminal_state == FAILED
    => failure_code must be present.

terminal_state == INSUFFICIENT
    => failure_code must be INSUFFICIENT_EVIDENCE
       or CONTEXT_UNSTABLE where the later runtime treats instability
       as an insufficient owner-facing outcome.
```

D126 intentionally defers the exact `INSUFFICIENT` failure mapping because
`CONTEXT_UNSTABLE` may instead be represented as `FAILED` by D129/D136.
D126 should avoid freezing a cross-field rule that later runtime semantics
have not yet implemented.

**Frozen rule:**

```text
COMPLETED => failure_code is None
FAILED    => failure_code is not None
```

and defer exact `INSUFFICIENT` failure mapping to D129/D132/D136.

---

## 13. Immutability Rules

Both dataclass-style contracts must be:

```text
frozen
slots
provider-neutral
side-effect free
```

Collection inputs that are accepted must be copied into immutable tuples.

Caller mutation after construction must not alter the contract.

The contracts must contain no mutable default list/dict/set.

---

## 14. D104 / D125 Compatibility Contract

D126 imports and reuses:

```text
app.contracts.task_aware_ai_routing.AITaskKind
```

D126 must not redefine it.

Frozen authority remains:

```text
AITaskKind.GENERAL_CHAT
AITaskKind.SOFTWARE_ENGINEERING
```

The following is explicitly invalid:

```text
cognitive intent
    -> arbitrary new AITaskKind
    -> provider/profile selection
```

The invariant is:

```text
CognitiveTaskDescription != AITaskKind authority
```

Future expansion of authoritative task routing requires a separately frozen milestone.

---

## 15. Deadline / Resource Constitution

D126 freezes semantics only.

A Cognitive Turn owns one server-generated monotonic deadline.

Rules:

1. deadline is not supplied by model output;
2. deadline is not extended by an organ;
3. remaining budget monotonically decreases;
4. an expensive/model stage must use no more than remaining turn budget;
5. deadline expiry does not create provider/model fallback;
6. late results after terminality are stale;
7. no background continuation is authorized.

D126 does not freeze numeric timeout values.

D126 does not add a deadline runtime class unless implementation review proves a pure data contract is required.

---

## 16. LLM / Provider Boundary

D126 performs zero AI calls.

`backend/app/contracts/cognitive_brain.py` must not import:

```text
OpenAI SDK
Ollama runtime
AIAdapter implementations
AIRuntime
ExecutionGuard
ExecutionPlanner
provider clients
provider endpoints
API keys
```

`CognitiveInvocationPurpose` is descriptive metadata only.

Actual future model execution remains behind existing authorization and runtime boundaries.

---

## 17. Persistence Boundary

D126 adds **no new persistence**.

Forbidden D126 production additions:

```text
database table
ORM model
migration
repository
artifact store
turn-manifest store
Experience store
automatic Memory write
```

The data contracts are persistence-capable shapes only in the architectural sense.

Any durable use requires separately authorized milestone scope.

---

## 18. Exact Test Scope

D126 proposes exactly two new test modules.

```text
backend/tests/test_d126_cognitive_brain_core_contracts.py
backend/tests/test_d126_cognitive_brain_core_contracts_security.py
```

No historical test migration is pre-authorized.

If a historical test conflict appears during regression, implementation stops and reports the exact conflict before editing it.

---

## 19. Functional Test Matrix

Frozen functional tests:

| ID | Test |
|---|---|
| F01 | `CognitiveOrgan` exposes exactly 17 frozen values |
| F02 | `CognitiveOrganStatus` exposes exactly 4 values |
| F03 | `CognitiveTurnState` exposes exact lifecycle values |
| F04 | terminal helper returns true only for COMPLETED / FAILED / INSUFFICIENT |
| F05 | `CognitiveInvocationPurpose` exposes exactly 4 values |
| F06 | `CognitiveFailureCode` exposes the exact frozen D126 set |
| F07 | envelope accepts exact `WorkspaceId.PERSONAL` |
| F08 | envelope accepts exact `WorkspaceId.COMPANY` |
| F09 | envelope permits absent pre-freeze Context digest |
| F10 | envelope accepts valid Context SHA-256 digest |
| F11 | envelope normalizes aware datetime to UTC |
| F12 | envelope copies reference sequence into immutable tuple |
| F13 | envelope preserves reference digest order |
| F14 | envelope accepts optional model-binding digest |
| F15 | manifest constructs a valid General Chat record |
| F16 | manifest constructs a valid Software Engineering record |
| F17 | manifest terminal COMPLETED with no failure is valid |
| F18 | manifest terminal FAILED with safe failure code is valid |
| F19 | manifest revision count accepts 0 and 1 |
| F20 | manifest artifact digests become immutable tuple |
| F21 | manifest uses the exact existing `AITaskKind` class |
| F22 | manifest task semantics version is exact frozen V1 identifier |
| F23 | contracts compare deterministically by immutable values where dataclass equality applies |

---

## 20. Security Test Matrix

Frozen security tests:

| ID | Test |
|---|---|
| S01 | arbitrary organ string rejected |
| S02 | wrong-case organ alias rejected |
| S03 | arbitrary organ status rejected |
| S04 | arbitrary turn state rejected |
| S05 | arbitrary invocation purpose rejected |
| S06 | arbitrary failure code rejected |
| S07 | raw arbitrary workspace string rejected |
| S08 | invalid/empty/whitespace turn ID rejected |
| S09 | control-character identifier rejected |
| S10 | oversized identifier rejected |
| S11 | uppercase SHA-256 digest rejected |
| S12 | short/long/non-hex digest rejected |
| S13 | duplicate reference digests rejected |
| S14 | too many reference digests rejected |
| S15 | caller list mutation cannot mutate envelope tuple |
| S16 | naive datetime rejected |
| S17 | non-terminal state rejected in `terminal_state` field |
| S18 | COMPLETED manifest with failure code rejected |
| S19 | FAILED manifest without failure code rejected |
| S20 | revision count bool rejected |
| S21 | revision count below 0 rejected |
| S22 | revision count above 1 rejected |
| S23 | arbitrary string cannot replace `AITaskKind` |
| S24 | richer cognitive task label cannot become authoritative task kind |
| S25 | model binding reference does not expose runtime authorization object |
| S26 | contracts have no Owner approval field |
| S27 | contracts have no execution authorization field |
| S28 | contracts have no credential/secret field |
| S29 | construction triggers no provider/network call |
| S30 | construction triggers no DB/repository call |
| S31 | contract module imports no provider/runtime implementation |
| S32 | contract module cannot create retry/fallback behavior |

---

## 21. Relevant Historical Regression Set

Before full backend regression, D126 should run a targeted historical set covering preserved boundaries.

At minimum:

```text
D91 workspace contract/security tests
D94-D97 Context contract/security tests
D104 task-aware routing tests
D111 AI brain runtime integration tests
D125 task runtime profile/security tests
ExecutionGuard / AIRuntime focused tests
Reasoning / Planning / Decision focused tests
```

Exact test filenames will be enumerated in the implementation gate from the repository state at that time.

D126 must not modify those historical tests unless an explicit amendment is separately reviewed and frozen.

---

## 22. Exact Frozen D126 Repository Scope

The initial D126 milestone scope is frozen as:

```text
NEW backend/app/contracts/cognitive_brain.py

NEW backend/tests/test_d126_cognitive_brain_core_contracts.py
NEW backend/tests/test_d126_cognitive_brain_core_contracts_security.py

NEW docs/specs/D126_COGNITIVE_BRAIN_CONSTITUTION_CORE_CONTRACTS_V1.md
```

Exactly four files.

No frontend file.

No DB model.

No migration.

No API route.

No existing production file modification.

No runtime integration.

No historical test modification.

---

## 23. Scope Expansion Rule

If implementation requires any fifth file:

```text
STOP
    ↓
identify exact dependency/conflict
    ↓
Owner review
    ↓
D126 Amendment if justified
    ↓
freeze amendment
    ↓
resume
```

No implicit scope expansion is authorized.

---

## 24. Codex Budget Policy for D126

Default:

```text
CODEX = NO
```

Reason:

- one isolated production contract module;
- two new focused test files;
- no multi-file caller migration;
- no runtime wiring;
- no broad refactor.

Codex becomes justified only if the pre-implementation compatibility scan finds an unexpected cross-cutting conflict that is expensive to inspect manually.

---

## 25. D126 Acceptance Criteria

D126 is complete only when all applicable gates pass:

```text
Owner Design Review                           PASS
D126 Design Freeze                           PASS
Exact 4-file initial implementation scope    PASS
Functional D126 tests                        PASS
Security D126 tests                          PASS
Targeted historical regression               PASS
Full backend regression                      PASS
No frontend production change                PASS
No DB/migration change                       PASS
No routing/profile authority change          PASS
No provider call introduced                  PASS
No persistence introduced                    PASS
git diff --check                             PASS
Exact commit scope                           PASS
Working tree clean                           PASS
Owner contract/guided acceptance             PASS
Remote freeze                                PASS
```

For D126, Guided Acceptance is contract inspection and adversarial construction testing rather than a UI workflow.

---

## 26. Explicit Non-Goals / Future Ownership

```text
Perception / Attention / richer Task Understanding  -> D127
Working State convergence / turn concurrency        -> D128
Context stabilization                               -> D129
Reasoning expansion / Prediction                    -> D130
Planning / Decision integration                     -> D131
Metacognition / uncertainty                         -> D132
Critic / Publication Gate                           -> D133
Experience / Learning boundary                      -> D134
Model capability knowledge                          -> D135
Cognitive Executive / integrated runtime            -> D136
Newborn Brain integration / security / Birth        -> D137
```

D126 also excludes Browser, external workflow engines, autonomous action, shell execution, Git mutation, connector writes, and self-modification.

---

## 27. D126 Owner Review Decisions

D126 freezes the Owner-approved decisions:

```text
CognitiveTurnManifest:
IN D126 AS DATA CONTRACT ONLY

CognitiveFailureCode:
SMALL CLOSED ARCHITECTURE-LEVEL SET

context_snapshot_digest:
OPTIONAL BEFORE CONTEXT_FROZEN

CognitiveOrgan:
ALL 17 FROZEN ARCHITECTURE ORGANS

exact timeout durations:
NOT IN D126
```

One remaining semantic point should be frozen carefully:

### `INSUFFICIENT` + `failure_code`

Frozen rule:

```text
COMPLETED -> failure_code MUST be None
FAILED    -> failure_code MUST be present
INSUFFICIENT -> no additional cross-field restriction in D126
```

Reason:

D129/D132/D136 should own the exact distinction between an insufficient owner-facing result and a system failure such as persistent Context instability.

This avoids D126 prematurely deciding later runtime behavior.

---

## 28. Current Status

```text
D126 — COGNITIVE BRAIN CONSTITUTION & CORE CONTRACTS V1

READ-ONLY RECONCILIATION:  COMPLETE
DESIGN REVISION:           0.2 - FROZEN
DRAFT 0.1 OWNER DIRECTION: APPROVED
DRAFT 0.2 OWNER REVIEW:    PASS
DESIGN FREEZE:             YES

IMPLEMENTATION:            NOT STARTED
CODE CHANGE:               NONE
CODEX USED:                NO
COMMIT:                    DESIGN FREEZE COMMIT
PUSH:                      NO
```
