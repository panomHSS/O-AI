# D129 — Context Intelligence / Brain-facing Context & Memory V1

**Roadmap name:** Cognitive Context & Memory Integration V1
**Status:** DESIGN FROZEN - OWNER A-N APPROVED / REPOSITORY FREEZE PENDING
**Design revision:** Rev 1.0 - FROZEN DESIGN CONTENT
**Architecture baseline:** O-AI Cognitive Brain Architecture V1 — DESIGN FROZEN / PUSHED / REMOTE FROZEN
**D128 baseline:** COMPLETE / PUSHED / REMOTE FROZEN
**D128 implementation commit:** `274f5e51795a5ce1b68acaa74ed712ea527a8953`
**D128 Design Freeze parent:** `0854ca768095e290041b3d3d0f74de8233a902fc`
**Owner Design Review:** PASS - Decisions A-N APPROVED
**Implementation:** NOT STARTED
**Code change:** NONE
**Git commit:** NOT CREATED
**Git push:** NOT PUSHED
**Codex:** NOT USED

---

## 1. Purpose

D129 forms the Brain V1 **Context Intelligence / Brain-facing Context & Memory** boundary by reconciling the existing D94-D97 Context architecture, confirmed Memory retrieval, D126 provenance/failure contracts, D127 Perception/Attention/Task semantics, and D128 `CognitiveWorkingState`.

The governing rules are:

> **D94-D97 remain the canonical Context substrate. D129 creates Brain-facing projections over verified Context; it does not create a second Context system.**

> **One Cognitive Turn may perform at most one explicit full pre-freeze Context reacquisition, and only for the exact verified D96 source-change conflict. After freeze, Context is immutable for the remainder of the turn.**

> **Memory Retrieval is a read-only selection of confirmed Memory already admitted into the final frozen ContextSnapshot. Retrieval is not Memory mutation, learning, confirmation, or authority.**

D129 adds exactly two Brain-facing organ outputs:

```text
Context Intelligence
    -> CognitiveContextArtifact

Memory Retrieval
    -> CognitiveMemoryRetrievalArtifact
```

and one bounded pre-freeze stabilization primitive:

```text
resolve
-> snapshot capture
-> exact source-change conflict?
       no  -> freeze
       yes -> discard whole first candidate set
              -> re-resolve exact same request once
              -> capture again
              -> freeze OR CONTEXT_UNSTABLE
```

D129 does not wire the live Cognitive Executive. D136 remains the integrated runtime milestone.

---

## 2. Owner Design Reconciliation A-N — APPROVED

### A — Canonical Context substrate

APPROVED:

D94-D97 remain the only canonical Context selection, budget, provenance, freeze, rendering, and compatibility substrate.

D129 does not create a second:

```text
Context resolver
Context budget system
Context layer taxonomy
Context snapshot type
Context provenance model
Context renderer
```

### B — Brain-facing Context organ output

APPROVED:

D129 introduces one immutable `CognitiveContextArtifact` carrying the existing verified `ContextSnapshot`.

The artifact does not copy Context text into a second representation.

### C — Brain-facing Memory Retrieval organ output

APPROVED:

D129 introduces one immutable `CognitiveMemoryRetrievalArtifact` carrying only the exact Memory-layer `ContextSourceRef` identities selected into the final frozen snapshot.

No Memory content is duplicated into the cognitive artifact.

### D — No second Memory read after freeze

APPROVED:

Brain-facing Memory Retrieval is derived from the final frozen `ContextSnapshot` only.

D129 performs no post-freeze `MemoryResolver.resolve`, repository Memory read, or `confirmed_versions_for_context()` call.

### E — Exact stabilization trigger

APPROVED:

Automatic stabilization is permitted only for:

```text
ContextSnapshotError.code == "context_snapshot_source_changed"
```

No other D94-D97 error is retryable by D129.

### F — Exact stabilization budget

APPROVED:

Maximum automatic Context reacquisitions:

```text
1
```

The implementation is explicit and bounded. No general retry loop exists.

### G — Same-input invariant across reacquisition

APPROVED:

The second resolution reuses the exact same immutable `ContextResolveRequest` object and therefore preserves:

```text
query
workspace
conversation binding
project binding
task input represented by the query
ContextResolver instance
Context policy
source dependency set
```

### H — No stale/fresh merge

APPROVED:

After the recognized first source-change conflict, the complete first `ContextBundle` is discarded.

No selected item, score, source identity, text projection, provenance observation, or partial subset from attempt 1 may be merged into attempt 2.

### I — Working State integration

APPROVED:

`CognitiveWorkingState` gains optional D129 slots:

```text
context: CognitiveContextArtifact | None
memory_retrieval: CognitiveMemoryRetrievalArtifact | None
```

D129 validates exact turn/workspace/digest/source consistency.

### J — Freeze means no silent replacement

APPROVED:

Once D129 Context is attached to one `CognitiveWorkingState`, a different Context artifact or snapshot may not replace it.

Once Memory Retrieval is attached for that frozen snapshot, it may not silently rebind to another snapshot.

### K — D127 compatibility under stabilization

APPROVED:

D129 does not silently recompute or rewrite D127 Perception, Attention, or Task artifacts.

Conflicting already-attached D127 metadata fails closed.

D136 owns final orchestration order.

### L — Persistence boundary

APPROVED:

D129 itself performs no persistence and introduces no repository write.

Existing D96/D97 persistence remains historical infrastructure for later runtime integration.

### M — Authority and runtime boundary

APPROVED:

D129 adds no provider/model/profile selection, AI invocation, credential access, tool permission, Owner approval, execution authority, action execution, Memory mutation, Project mutation, Conversation mutation, routing authority, frontend/API behavior, or DB schema/migration.

### N — Failure semantics

APPROVED:

D129 adds no new Architecture-level failure vocabulary.

A second exact pre-freeze source-change conflict maps to existing:

```text
CognitiveFailureCode.CONTEXT_UNSTABLE
```

Other D94-D97 bounded failures retain their existing safe error codes for later runtime normalization.

---

## 3. Reconciled Existing Ownership

### 3.1 D94 Context contracts

Canonical existing values remain:

```text
ContextLayer
    CONVERSATION
    PROJECT
    MEMORY
    KNOWLEDGE

ContextSourceRef
ContextItem
ContextBundle
WorkspaceScope
```

Context remains provider-neutral untrusted background data and grants no authority.

### 3.2 D95 Context selection and budget

`ContextResolver` remains the sole D129 Context selection/budget/dedupe authority.

Exact layer order remains:

```text
CONVERSATION
PROJECT
MEMORY
KNOWLEDGE
```

D129 does not re-rank, re-budget, truncate, deduplicate, or reorder the resolved bundle.

### 3.3 Existing confirmed Memory retrieval

`MemoryContextSource` remains the canonical Memory candidate source for D95.

It already reuses confirmed Memory scoring helpers and emits D94 candidates.

Therefore D129 does not create a second Memory ranking path.

### 3.4 D96 verify-before-freeze Context

`ContextSnapshotService` remains the final source-truth verification boundary before freeze.

It re-observes selected sources and raises exact:

```text
context_snapshot_source_changed
```

when current authoritative projection differs from the D95-selected projection.

### 3.5 D97 frozen-snapshot compatibility principle

D97 already derives Project, Memory usage, and Reasoning evidence views from the frozen `ContextSnapshot` without re-resolving Memory or Project state.

D129 generalizes this principle to Brain-facing Context and Memory artifacts.

### 3.6 D126 Brain provenance and failure vocabulary

D129 reuses:

```text
CognitiveArtifactEnvelope
CognitiveOrgan.CONTEXT_INTELLIGENCE
CognitiveOrgan.MEMORY_RETRIEVAL
CognitiveOrganStatus.READY
CognitiveFailureCode.CONTEXT_UNSTABLE
CognitiveFailureCode.CONTRACT_VIOLATION
```

No second Brain-wide envelope or failure enum is introduced.

### 3.7 D127 Perception / Attention / Task semantics

D129 stores no duplicate D127 artifacts and does not recompute them.

D129 only validates final frozen Context consistency where D127 artifacts are already attached.

### 3.8 D128 Working State

`CognitiveWorkingState` remains the canonical Brain mutable per-turn state.

D129 extends it narrowly with the two new optional organ slots and freeze-consistency rules.

D128 turn concurrency semantics remain unchanged.

---

## 4. Exact D129 Implementation Scope

D129 implementation is frozen to exactly five code/test paths:

```text
NEW    backend/app/contracts/cognitive_context_memory.py
NEW    backend/app/services/cognitive_context_memory.py
MODIFY backend/app/intelligence/context/cognitive.py
NEW    backend/tests/test_d129_cognitive_context_memory.py
NEW    backend/tests/test_d129_cognitive_context_memory_security.py
```

No other production or test path is authorized without Owner amendment review.

Historical tests may not be modified under the initial D129 authorization.

Any required sixth implementation path means:

```text
STOP
-> dependency report
-> Owner amendment review
```

The Design Freeze specification itself is the sixth total milestone file:

```text
docs/specs/D129_COGNITIVE_CONTEXT_MEMORY_INTEGRATION_V1.md
```

Thus the complete D129 milestone is expected to contain exactly six changed/added repository paths after implementation:

```text
1 frozen spec
5 code/test paths
```

---

## 5. Exact D129 Constants

`backend/app/contracts/cognitive_context_memory.py` defines:

```text
D129_CONTEXT_ARTIFACT_TYPE
    = "cognitive.context"

D129_CONTEXT_CONTRACT_VERSION
    = "o-ai.cognitive-context.v1"

D129_MEMORY_RETRIEVAL_ARTIFACT_TYPE
    = "cognitive.memory_retrieval"

D129_MEMORY_RETRIEVAL_CONTRACT_VERSION
    = "o-ai.cognitive-memory-retrieval.v1"

D129_STABILIZATION_POLICY
    = "single_full_reacquisition_on_source_change.v1"

D129_MAX_STABILIZATION_REACQUISITIONS
    = 1
```

No dynamic policy extension exists in V1.

No provider/model/retry/fallback vocabulary is introduced.

---

## 6. `CognitiveContextFreezeResult`

Exact immutable contract:

```text
CognitiveContextFreezeResult
├── bundle: ContextBundle
├── snapshot: ContextSnapshot
├── stabilization_reacquisitions: int
└── stabilization_policy: str
```

### 6.1 Validation

```text
bundle
    exact existing ContextBundle

snapshot
    exact existing ContextSnapshot

stabilization_reacquisitions
    exact int
    bool rejected
    value in {0, 1}

stabilization_policy
    exactly "single_full_reacquisition_on_source_change.v1"
```

### 6.2 Final-bundle / snapshot coherence

The result retains the **successful final `ContextBundle`** alongside the final snapshot.

This is a Design Freeze refinement required so D136 can later project D127 Attention from the exact successful selection without re-resolving Context.

It does not alter Owner decisions A-N.

Required coherence:

```text
bundle.workspace_scope == snapshot.workspace_scope

tuple(snapshot_item.item for snapshot_item in snapshot.items)
    == bundle.items
```

The successful final bundle is not a second truth source.

It is only the exact pre-freeze selection that the D96 snapshot verified.

The failed first bundle, if any, is never present in the result.

---

## 7. `CognitiveContextArtifact`

Exact immutable contract:

```text
CognitiveContextArtifact
├── envelope: CognitiveArtifactEnvelope
├── snapshot: ContextSnapshot
├── stabilization_reacquisitions: int
└── stabilization_policy: str
```

### 7.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.CONTEXT_INTELLIGENCE

artifact_type
    == "cognitive.context"

contract_version
    == "o-ai.cognitive-context.v1"

status
    == CognitiveOrganStatus.READY

workspace_id
    == snapshot.workspace_scope.workspace_id

context_snapshot_digest
    non-null
    == snapshot.snapshot_digest

model_binding_reference
    == None
```

Context Intelligence is deterministic in D129 and cannot claim model production.

### 7.2 Stabilization metadata

```text
stabilization_reacquisitions
    exact int
    bool rejected
    0 or 1

stabilization_policy
    exact D129_STABILIZATION_POLICY
```

The artifact carries the existing D96 `ContextSnapshot` object.

It does not copy raw Context into a new list, prompt, or text blob.

---

## 8. `CognitiveMemoryRetrievalArtifact`

Exact immutable contract:

```text
CognitiveMemoryRetrievalArtifact
├── envelope: CognitiveArtifactEnvelope
└── selected_sources: tuple[ContextSourceRef, ...]
```

### 8.1 Envelope requirements

```text
producer_organ
    == CognitiveOrgan.MEMORY_RETRIEVAL

artifact_type
    == "cognitive.memory_retrieval"

contract_version
    == "o-ai.cognitive-memory-retrieval.v1"

status
    == CognitiveOrganStatus.READY

context_snapshot_digest
    non-null

model_binding_reference
    == None
```

### 8.2 Selected Memory source rules

Input may be a finite non-string `Sequence`, copied immediately to tuple.

Every selected source must be:

```text
exact ContextSourceRef
source.workspace_id == envelope.workspace_id
source.layer == ContextLayer.MEMORY
```

Duplicate exact source identities are rejected.

Source order is preserved.

No Memory content, raw value, prompt text, instruction field, repository handle, mutation request, or confirmation state is stored.

Empty selection is valid and means:

```text
no relevant confirmed Memory was admitted into final frozen Context
```

It is not a failure.

---

## 9. `CognitiveContextStabilizer`

Location:

```text
backend/app/services/cognitive_context_memory.py
```

The stabilizer is deterministic orchestration over exactly:

```text
existing ContextResolver
existing ContextSnapshotService
```

Conceptual constructor:

```text
CognitiveContextStabilizer(
    resolver,
    snapshot_service,
)
```

Conceptual operation:

```text
resolve_and_freeze(
    request: ContextResolveRequest,
) -> CognitiveContextFreezeResult
```

D129 performs no persistence inside this service.

---

## 10. Exact zero-reacquisition path

Normal path:

```text
bundle_1 = resolver.resolve(request)
snapshot_1 = snapshot_service.capture(bundle_1)

return CognitiveContextFreezeResult(
    bundle=bundle_1,
    snapshot=snapshot_1,
    stabilization_reacquisitions=0,
)
```

No second Context resolution is allowed after success.

No post-freeze refresh is allowed.

---

## 11. Exact one-reacquisition stabilization path

The only automatic stabilization trigger is:

```text
ContextSnapshotError.code
    == "context_snapshot_source_changed"
```

Exact behavior:

```text
bundle_1 = resolver.resolve(request)

capture(bundle_1)
    -> context_snapshot_source_changed

discard bundle_1 completely

bundle_2 = resolver.resolve(request)
snapshot_2 = snapshot_service.capture(bundle_2)

return CognitiveContextFreezeResult(
    bundle=bundle_2,
    snapshot=snapshot_2,
    stabilization_reacquisitions=1,
)
```

The same exact `request` object is passed to both calls.

No request copy, mutation, widening, or alternate policy is permitted.

The same resolver and snapshot-service instances are used.

---

## 12. Exact unstable path

If attempt 2 also raises exact:

```text
context_snapshot_source_changed
```

D129 raises:

```text
CognitiveContextUnstableError
    failure_code = CognitiveFailureCode.CONTEXT_UNSTABLE
    code = "context_unstable"
```

No third resolve.

No third capture.

No loop.

No sleep.

No wait.

No backoff.

No queue.

No provider retry.

No fallback.

No degraded stale Context continuation.

---

## 13. Non-retryable failure preservation

The following are examples of errors that must not trigger the D129 stabilization path:

```text
ContextResolutionError(...)
ContextSourceReadError(...)
context_snapshot_source_unavailable
context_snapshot_source_mismatch
context_snapshot_timestamp_invalid
context_snapshot_invalid
```

D129 does not remap them into `CONTEXT_UNSTABLE`.

They retain their existing bounded safe failure identity for D136 to normalize later.

Only the second exact source-change conflict becomes `CONTEXT_UNSTABLE`.

---

## 14. Dependency contract verification

D129 validates the outputs of its existing dependencies even when tests use fakes.

After every resolution:

```text
result is exact ContextBundle
bundle.workspace_scope == request.workspace_scope
```

After every successful capture:

```text
result is exact ContextSnapshot
snapshot.workspace_scope == request.workspace_scope
tuple(snapshot_item.item for snapshot_item in snapshot.items)
    == bundle.items
```

Violation fails closed with D129 contract error:

```text
CognitiveContextContractError
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
    code = "contract_violation"
```

A contract violation is not retryable.

---

## 15. No stale/fresh merge rule

When the first capture reports the exact source-change conflict:

```text
bundle_1
snapshot partials
first observations
first selected-source list
first projection text
```

are all unusable for final cognition.

Attempt 2 begins from:

```text
resolver.resolve(the_same_request)
```

and produces a completely new full candidate selection.

The final result contains only attempt 2's bundle and snapshot.

---

## 16. `CognitiveContextMemoryProjector`

Location:

```text
backend/app/services/cognitive_context_memory.py
```

This projector performs no I/O and no source read.

### 16.1 `project_context`

Conceptual signature:

```text
project_context(
    envelope,
    freeze_result,
) -> CognitiveContextArtifact
```

Requirements:

1. exact Context Intelligence envelope;
2. exact `CognitiveContextFreezeResult`;
3. envelope workspace matches final snapshot;
4. envelope Context digest equals final `snapshot_digest`;
5. copy exact stabilization count/policy;
6. reuse exact existing snapshot;
7. perform no resolution, provenance observation, repository read/write, AI call, or persistence.

### 16.2 `project_memory`

Conceptual signature:

```text
project_memory(
    envelope,
    snapshot,
) -> CognitiveMemoryRetrievalArtifact
```

Requirements:

1. exact Memory Retrieval envelope;
2. exact `ContextSnapshot`;
3. envelope workspace matches snapshot;
4. envelope Context digest equals snapshot digest;
5. select only `ContextLayer.MEMORY` source refs;
6. preserve their exact snapshot order;
7. copy no Memory content;
8. perform no MemoryResolver/repository call.

---

## 17. D129 extension to `CognitiveWorkingState`

Location:

```text
backend/app/intelligence/context/cognitive.py
```

Exact additional fields:

```text
context: CognitiveContextArtifact | None = None
memory_retrieval: CognitiveMemoryRetrievalArtifact | None = None
```

Existing D128 fields remain unchanged:

```text
binding
working_memory_envelope
perception
attention
task
request
conversation
knowledge
intelligence
response
runtime
```

D129 does not create future-organ fields.

---

## 18. Working State Context attachment invariants

For non-null `context`:

```text
context.envelope.turn_id
    == binding.turn_id

context.envelope.workspace_id
    == binding.workspace_id

context.snapshot.workspace_scope.workspace_id
    == binding.workspace_id

context.envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest
```

If D128 Working Memory envelope has non-null Context digest:

```text
working_memory_envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest
```

A D128 Working Memory envelope with null Context digest remains valid for compatibility.

D129 does not replace that frozen envelope.

---

## 19. D127 digest compatibility after Context freeze

Once D129 Context is attached, for every non-null D127 artifact:

```text
perception
attention
task
```

if its envelope has a non-null `context_snapshot_digest`, it must equal:

```text
context.snapshot.snapshot_digest
```

Null D127 digest remains valid because D127 artifacts may have been created before final freeze.

D129 never edits a D127 envelope.

---

## 20. D127 Attention / final frozen selection consistency

If `attention` is non-null when D129 Context is attached, its exact selected sources must equal:

```text
tuple(
    snapshot_item.item.source
    for snapshot_item in context.snapshot.items
)
```

in exact order.

If D129 Context already exists and Attention is assigned later, the same rule applies.

Mismatch fails closed.

D129 does not silently rebuild Attention.

D136 may later project Attention from `CognitiveContextFreezeResult.bundle`, which is why D129 retains the successful final bundle in the freeze result.

---

## 21. Working State Memory Retrieval invariants

`memory_retrieval` may be non-null only when `context` is already non-null in the resulting state.

Required:

```text
memory_retrieval.envelope.turn_id
    == binding.turn_id

memory_retrieval.envelope.workspace_id
    == binding.workspace_id

memory_retrieval.envelope.context_snapshot_digest
    == context.snapshot.snapshot_digest
```

Exact selected sources must equal:

```text
tuple(
    snapshot_item.item.source
    for snapshot_item in context.snapshot.items
    if snapshot_item.item.source.layer is ContextLayer.MEMORY
)
```

No subset, superset, reorder, or additional Memory identity is valid.

---

## 22. Freeze / replacement semantics

### 22.1 Context

State transition:

```text
context = None
    -> may attach one valid CognitiveContextArtifact

context = valid artifact
    -> idempotent assignment of equal artifact allowed
    -> assignment of different artifact rejected
    -> assignment back to None rejected
```

### 22.2 Memory Retrieval

State transition:

```text
memory_retrieval = None
    -> may attach one valid artifact after Context exists

memory_retrieval = valid artifact
    -> idempotent assignment of equal artifact allowed
    -> assignment of different artifact rejected
    -> assignment back to None rejected
```

This is per-turn freeze identity, not durable persistence.

---

## 23. Post-freeze read semantics

After D129 successful freeze:

```text
ContextResolver calls for this primitive: 0 additional
ContextSnapshotService captures for this primitive: 0 additional
MemoryResolver calls: 0
MemoryRepository reads: 0
Project re-resolution: 0
Knowledge re-search: 0
```

D129 provides no `refresh`, `reload`, `replace`, `retry`, or `fallback` API.

A later database/source change is not silently incorporated into the current turn.

---

## 24. Memory safety semantics

Brain-facing Memory means:

```text
confirmed Memory selected through D95
and verified through D96
and represented by source identity in the final frozen snapshot
```

It does not mean:

```text
instruction
system prompt
developer prompt
Owner approval
execution command
routing directive
provider selection
tool permission
Memory write request
learning event
```

D129 never promotes, confirms, edits, deletes, supersedes, or creates Memory.

---

## 25. Context truth semantics

A successful D129 Context artifact proves:

```text
these exact selected source projections
were re-observed and verified at freeze time
under this exact workspace
and are represented by this ContextSnapshot digest
```

It does not prove:

```text
every source statement is objectively true
future source state is unchanged
execution is authorized
Owner approved an action
a model/provider must be selected
```

---

## 26. Exact import / dependency boundaries

`backend/app/contracts/cognitive_context_memory.py` may import only contract/value dependencies needed for:

```text
CognitiveArtifactEnvelope
CognitiveOrgan
CognitiveOrganStatus
ContextLayer
ContextSourceRef
ContextBundle
ContextSnapshot
```

It must not import:

```text
repositories
SQLAlchemy Session
providers
AIRuntime
ExecutionGuard
ConversationService
API routes
```

`backend/app/services/cognitive_context_memory.py` may import existing:

```text
ContextResolveRequest
ContextBundle
ContextSnapshot
ContextResolver
ContextResolutionError
ContextSnapshotService
ContextSnapshotError
D129 contracts
CognitiveFailureCode
```

and standard-library typing/sequence utilities only as needed.

No provider/model/repository/execution import is authorized.

---

## 27. Persistence boundary

D129 production code must not write through:

```text
ContextSnapshotRepository
MemoryRepository
ConversationRepository
ProjectRepository
KnowledgeRepository
```

D129 creates no DB model or migration.

D129 does not change historical D96 snapshot persistence behavior.

Persistence decisions remain outside the D129 primitive and are integrated later by D136 or existing historical flows.

---

## 28. Authority boundary

The following equivalences are forbidden:

```text
Context Artifact       != authorization
Memory Retrieval       != Memory write permission
Snapshot Digest        != Owner approval
Selected source        != trusted instruction
Stabilization retry    != general retry authority
Attention              != routing authority
Context Intelligence   != provider/model selection
```

D129 grants zero Sovereign authority.

---

## 29. Runtime integration boundary

D129 does not modify or wire:

```text
ConversationService
CommandOrchestrator
ChatService
API routes
AIRuntime
ExecutionGuard
provider adapters
D104 task routing
D125 runtime profiles
frontend
automation runtime
```

D136 remains the owner of:

```text
Cognitive Executive sequencing
turn lifecycle integration
when D127 artifacts are projected
when D129 freeze runs
fresh model authorization
turn/stage deadlines
late-result enforcement
Critic revision coordination
durable final-response integration
```

---

## 30. Exact D129 functional test matrix

The focused functional module must contain tests covering exactly these frozen cases:

```text
F01 exact D129 constants
F02 valid freeze result with zero reacquisition
F03 valid freeze result with one reacquisition
F04 freeze result preserves exact successful bundle
F05 freeze result preserves exact successful snapshot
F06 valid Context artifact with zero reacquisition
F07 valid Context artifact with one reacquisition
F08 Context artifact retains exact D96 snapshot
F09 valid empty Memory Retrieval artifact
F10 valid Memory Retrieval artifact with one source
F11 Memory selected_sources normalize to tuple
F12 Memory selected-source order preserved

F13 first-attempt stable resolution succeeds
F14 stable path calls resolver exactly once
F15 stable path calls snapshot service exactly once
F16 stable path reports zero reacquisition
F17 stable path returns exact first bundle/snapshot
F18 first source-change conflict triggers second resolve
F19 stabilization reuses exact same request object
F20 stabilization uses exact same resolver instance
F21 stabilization uses exact same snapshot service instance
F22 successful second attempt reports one reacquisition
F23 failed first bundle is not returned
F24 successful second bundle is returned exactly
F25 successful second snapshot is returned exactly
F26 no third resolution occurs after second-attempt success
F27 second source-change conflict raises CognitiveContextUnstableError
F28 unstable error exposes CONTEXT_UNSTABLE
F29 first resolver error propagates without stabilization
F30 first non-source-change snapshot error propagates without stabilization
F31 second resolver error after first conflict propagates
F32 second non-source-change snapshot error after first conflict propagates

F33 Context projector uses final snapshot digest exactly
F34 Context projector preserves stabilization metadata
F35 Context projector performs pure projection
F36 Memory projector selects only MEMORY layer
F37 Memory projector preserves frozen snapshot Memory order
F38 Memory projector returns empty selection when snapshot has no Memory
F39 Memory projector does not copy Memory content

F40 CognitiveWorkingState remains constructible with both D129 slots None
F41 CognitiveWorkingState constructs with valid Context
F42 Context may attach once after state construction
F43 Memory Retrieval may attach after Context
F44 state constructs with valid Context + Memory Retrieval
F45 null D128 Working Memory Context digest remains compatible
F46 matching non-null D128 Working Memory Context digest remains compatible
F47 null D127 Perception digest remains compatible after freeze
F48 null D127 Task digest remains compatible after freeze
F49 matching D127 Context digest remains compatible
F50 matching D127 Attention selected-source order is accepted
F51 idempotent equal Context assignment is accepted
F52 idempotent equal Memory Retrieval assignment is accepted

F53 historical D128 Working State behavior remains compatible
F54 historical D128 turn-guard behavior remains compatible
```

No additional production behavior is justified merely by adding extra focused tests.

---

## 31. Exact D129 security test matrix

The focused security module must contain tests covering exactly these frozen cases:

```text
S01 wrong Context envelope object rejected
S02 wrong Context producer organ rejected
S03 wrong Context artifact type rejected
S04 wrong Context contract version rejected
S05 non-READY Context status rejected
S06 Context model binding reference rejected
S07 null Context snapshot digest rejected
S08 Context snapshot digest mismatch rejected
S09 Context cross-workspace snapshot rejected
S10 bool stabilization count rejected
S11 negative stabilization count rejected
S12 stabilization count above one rejected
S13 wrong stabilization policy rejected

S14 wrong freeze-result bundle type rejected
S15 wrong freeze-result snapshot type rejected
S16 freeze-result bundle/snapshot workspace mismatch rejected
S17 freeze-result bundle/snapshot item mismatch rejected

S18 wrong Memory envelope object rejected
S19 wrong Memory producer organ rejected
S20 wrong Memory artifact type rejected
S21 wrong Memory contract version rejected
S22 non-READY Memory status rejected
S23 Memory model binding reference rejected
S24 null Memory Context digest rejected
S25 non-ContextSourceRef Memory source rejected
S26 non-MEMORY layer source rejected
S27 cross-workspace Memory source rejected
S28 duplicate Memory source rejected
S29 invalid Memory selected-source collection rejected

S30 Context projector rejects wrong envelope
S31 Context projector rejects wrong freeze result
S32 Context projector rejects digest mismatch
S33 Memory projector rejects wrong envelope
S34 Memory projector rejects wrong snapshot
S35 Memory projector rejects digest mismatch
S36 Memory projector rejects cross-workspace snapshot

S37 stabilizer rejects wrong request type
S38 resolver returning non-ContextBundle fails contract
S39 resolver returning wrong-workspace bundle fails contract
S40 snapshot service returning non-ContextSnapshot fails contract
S41 snapshot wrong workspace fails contract
S42 snapshot not freezing exact resolved bundle fails contract
S43 dependency contract failure is not retried

S44 resolver failure is not retried
S45 context_snapshot_source_unavailable is not retried
S46 context_snapshot_source_mismatch is not retried
S47 context_snapshot_timestamp_invalid is not retried
S48 context_snapshot_invalid is not retried
S49 only exact context_snapshot_source_changed triggers stabilization
S50 first exact source-change yields at most two resolver calls
S51 second exact source-change yields no third resolver call
S52 second exact source-change yields no third capture call
S53 stabilizer contains no sleep/wait/backoff/queue
S54 stabilizer contains no general retry/fallback loop
S55 stabilization reuses exact request object
S56 stabilization does not mutate request
S57 failed first bundle cannot contribute items to final bundle
S58 failed first bundle cannot contribute provenance to final snapshot

S59 Working State Context turn mismatch rejected
S60 Working State Context workspace mismatch rejected
S61 Context digest conflicting with non-null Working Memory digest rejected
S62 Context digest conflicting with Perception digest rejected
S63 Context digest conflicting with Attention digest rejected
S64 Context digest conflicting with Task digest rejected
S65 Attention selected-source mismatch against final snapshot rejected
S66 Memory Retrieval without Context rejected
S67 Memory Retrieval turn mismatch rejected
S68 Memory Retrieval workspace mismatch rejected
S69 Memory Retrieval digest mismatch rejected
S70 Memory Retrieval selected-source mismatch rejected
S71 different Context replacement after freeze rejected
S72 Context removal after freeze rejected
S73 different Memory Retrieval replacement rejected
S74 Memory Retrieval removal after freeze rejected

S75 no Owner approval/execution authorization fields
S76 no provider/model/profile/credential/tool authority fields
S77 no raw prompt/system prompt/hidden reasoning/CoT fields
S78 no Memory/Project/Conversation/repository write behavior
S79 no provider/AIRuntime/ExecutionGuard call
S80 D126 CONTEXT_UNSTABLE and CONTRACT_VIOLATION vocabulary unchanged
```

---

## 32. Exact targeted historical regression

At minimum, D129 implementation validation must run these exact current historical test files:

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

backend/tests/test_task_aware_ai_routing_contract.py
backend/tests/test_task_aware_ai_routing_service.py
backend/tests/test_d104_task_aware_ai_routing_security.py
backend/tests/test_d105_task_aware_ai_routing_integration.py
backend/tests/test_d105_task_aware_ai_routing_security.py
backend/tests/test_d125_local_ai_task_runtime_profiles.py
backend/tests/test_d125_local_ai_task_runtime_profiles_integration.py
backend/tests/test_d125_local_ai_task_runtime_profiles_security.py

backend/tests/test_execution_guard.py
backend/tests/test_ai_runtime.py
```

Exact filenames must be revalidated before implementation mutation.

Historical test modification is not pre-authorized.

Any historical-test edit requires STOP and Owner review.

---

## 33. Validation sequence

After separate implementation authorization, the mandatory validation sequence is:

```text
1. Pre-Mutation Gate
2. Exact five-path implementation mutation
3. D129 focused functional tests F01-F54
4. D129 focused security tests S01-S80
5. Exact targeted historical regression
6. Full backend regression
7. Exact scope/hash/security acceptance
8. Owner guided acceptance
9. Separate local implementation commit authorization
10. Separate normal push authorization
11. Independent remote verification
```

A failed gate is diagnosed from current state.

No blind patch reapplication.

No blind push retry.

No reset/rebase/force.

---

## 34. Acceptance criteria

D129 is complete only when all applicable gates pass:

```text
Owner Design Reconciliation A-N                    PASS
D129 Design Freeze                                PASS
Design Freeze exact one-doc scope                 PASS

Implementation exact five code/test paths         PASS
Frozen D129 spec unchanged during implementation  PASS

D129 functional matrix F01-F54                    PASS
D129 security matrix S01-S80                      PASS

D94-D97 canonical substrate preserved             PASS
Context stabilization exact trigger preserved     PASS
Maximum reacquisition exactly one                 PASS
Same exact request reused                         PASS
No stale/fresh merge                              PASS
Second source-change -> CONTEXT_UNSTABLE          PASS
No post-freeze Context refresh                    PASS

Memory derived only from final frozen snapshot    PASS
No post-freeze Memory reread                      PASS
Empty Memory selection remains successful         PASS

D127 digest/Attention compatibility               PASS
D128 Working State compatibility                  PASS
D128 concurrency behavior unchanged               PASS
D104/D125 authority unchanged                     PASS

No persistence introduced                         PASS
No DB/migration change                            PASS
No API/frontend change                            PASS
No ConversationService change                     PASS
No AIRuntime/ExecutionGuard change                PASS
No provider/model/profile authority change        PASS
No Memory/Project/Conversation mutation           PASS

Targeted historical regression                    PASS
Full backend regression                           PASS
git diff --check                                  PASS
Exact local commit scope                          PASS
Working tree clean                                PASS
Owner guided acceptance                           PASS
Final push / remote freeze                        PASS
```

---

## 35. Guided Owner Acceptance shape

Final implementation acceptance will ask the Owner to confirm:

```text
A. D94-D97 remain the canonical Context substrate
B. D129 freezes one verified existing ContextSnapshot, not a parallel Context representation
C. Brain-facing Memory is derived only from Memory items in that frozen snapshot
D. no Memory reread occurs after freeze
E. stabilization triggers only on exact context_snapshot_source_changed
F. stabilization performs at most one full reacquisition
G. the failed first bundle is fully discarded and the same request is reused
H. a second source-change conflict becomes CONTEXT_UNSTABLE
I. no silent Context refresh or replacement is possible after freeze
J. D127 Attention/digest consistency fails closed rather than being silently rewritten
K. D129 adds no persistence/provider/model/execution authority
L. live Cognitive Executive wiring remains deferred to D136
```

---

## 36. Codex budget

Default:

```text
CODEX = NO
```

Expected implementation is bounded:

```text
1 new contract module
1 new deterministic service module
1 narrow CognitiveWorkingState extension
2 focused test modules
```

Codex becomes justified only if pre-mutation reconciliation discovers unexpected broad coupling in:

```text
ContextSnapshot lifecycle
Pydantic assignment/freeze behavior
hidden runtime dependencies
```

If that occurs:

```text
STOP
-> report exact dependency
-> Owner review
```

---

## 37. Explicit non-goals

D129 does not build:

```text
Reasoning V2
Prediction
Cognitive Planning integration
Decision integration
Metacognition
Critic
Experience/Learning
Model Intelligence
Cognitive Executive
Browser/tools/workflows
autonomous refresh
distributed Context locking
new Memory ranking
Memory mutation
new persistence
frontend behavior
```

These remain owned by later milestones or historical subsystems.

---

## 38. Frozen status

```text
D129 — CONTEXT INTELLIGENCE / BRAIN-FACING CONTEXT & MEMORY V1

OWNER DESIGN RECONCILIATION A-N: APPROVED
EXACT CONTRACTS:                 DEFINED
STABILIZATION CONTRACT:          DEFINED
WORKING STATE INTEGRATION:       DEFINED
FUNCTIONAL MATRIX:               F01-F54 DEFINED
SECURITY MATRIX:                 S01-S80 DEFINED
IMPLEMENTATION SCOPE:            EXACTLY 5 CODE/TEST PATHS

DESIGN CONTENT:                  FROZEN - OWNER APPROVED
REPOSITORY DESIGN FREEZE:        PENDING OWNER GIT AUTHORIZATION

IMPLEMENTATION:                  NOT STARTED
CODE CHANGE:                     NONE
COMMIT:                          NOT CREATED
PUSH:                            NOT PUSHED
CODEX USED:                      NO
RESET/REBASE/FORCE:              NO
```

---

**End of D129 — Context Intelligence / Brain-facing Context & Memory V1 Design Freeze Content**
