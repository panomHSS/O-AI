# D134 — Experience / Learning Boundary V1

**Document status:** DESIGN FROZEN — OWNER APPROVED
**Design revision:** Rev 0.2 — FINAL FROZEN BASELINE
**Architecture:** O-AI Cognitive Brain Architecture V1
**Milestone:** D134 — Experience / Learning Boundary V1
**Baseline commit:** `d9a83c8d2a62e91a5c173dcc0cac146c86b5d0df`
**Baseline state:** D133 COMPLETE / PUSHED / INDEPENDENTLY REMOTE VERIFIED
**Owner Design Reconciliation A–P:** PASS
**Owner Exact Contract Proposal Rev 0.1 approval:** YES — SUPERSEDED BY REV 0.2
**Owner Exact Contract Proposal Rev 0.2 approval:** YES
**Final Contract Review Rev 0.2:** PASS
**Design Freeze:** YES — OWNER AUTHORIZED
**Implementation authorization:** NOT RECEIVED
**Implementation mutation:** NONE
**Code change:** DESIGN SPEC ONLY
**Push:** NOT AUTHORIZED / NOT PUSHED

---

## 1. Purpose

D134 introduces the Brain-facing **Experience / Learning Boundary V1**.

D134 gives Newborn Brain V1 the anatomy to observe a terminal cognitive outcome and form one bounded, privacy-minimized `ExperienceCandidate` without granting autonomous learning authority.

The governing boundary is:

```text
ExperienceCandidate ≠ Memory
ExperienceCandidate ≠ Policy
ExperienceCandidate ≠ Prompt
ExperienceCandidate ≠ Routing authority
ExperienceCandidate ≠ Execution authority
ExperienceCandidate ≠ Promoted Experience
Experience observation ≠ General truth
```

D134 is deliberately **ephemeral by default**. It does not create a durable Experience store, autonomous promotion path, model-selection policy, background learner, self-modifying prompt, or self-modifying code.

## 2. Architecture Position

Canonical Brain Formation relationship:

```text
D132 Metacognition
      ↓
Authorized synthesis
      ↓
D133 Verification / Publication Gate
      ↓
Primary response finalization / persistence
      ↓
Terminal Cognitive Turn
      ↓
D134 Experience Eligibility
      ↓
Safe structured observation
      ↓
Hygiene / minimization
      ↓
ExperienceCandidate
      ↓
EPHEMERAL
      ↓
future separately frozen Owner / promotion policy boundary
```

D134 processing is outside primary response criticality.

```text
Experience processing failure
≠ primary-turn failure
```

Actual integrated post-turn hook wiring is reserved for D136 Cognitive Executive.

## 3. Frozen Design Reconciliation A–P

### A — Frozen upstream sovereignty

D126–D133, Context, Memory, routing, execution governance, Publication Gate, and Owner authority remain frozen upstream.

D134 must not change their semantics.

### B — Post-turn only

Experience evaluation occurs only after the primary cognitive path has reached a terminal state.

It may never delay, reopen, downgrade, or rewrite an already-established primary terminal outcome.

### C — All three terminal classes are eligible for evaluation

D134 may evaluate:

```text
COMPLETED
INSUFFICIENT
FAILED
```

A terminal state being eligible for evaluation does not guarantee that a valid candidate can be formed.

### D — No post-terminal Working State mutation

`ExperienceCandidate` is a post-turn artifact.

D134 does not add an `experience_candidate` field to `CognitiveWorkingState` and does not mutate D128–D133 Working State after terminality.

### E — Ephemeral-by-default is literal

D134 V1 forms ephemeral candidates only.

No database table, ORM model, migration, repository, API, queue, scheduler, TTL worker, or automatic archival system is introduced.

### F — Candidate is cognition, never authority

The candidate uses a `CognitiveArtifactEnvelope` with producer `EXPERIENCE_SYSTEM`.

It grants no approval, routing, execution, persistence, promotion, Memory, Policy, Prompt, or code authority.

### G — References over raw copies

D134 prefers bounded metadata, enum/status values, IDs already present in the safe turn manifest, and digests.

It must not copy raw Conversation, Context, Memory, Knowledge, Draft, prompt, or hidden reasoning content into the candidate.

### H — Privacy-minimized situation metadata

D134 may carry canonical task categories.

It does not copy `normalized_request`, user message text, or arbitrary owner-authored free text into the ExperienceCandidate.

### I — Outcome observation is not generalization

A candidate may record what happened in one terminal turn.

It may not turn one observation into a rule such as:

```text
model X is always best
never use model Y
change policy Z
```

### J — Deterministic V1; zero LLM calls

D134 V1 performs no LLM invocation and adds no new `CognitiveInvocationPurpose`.

Lesson representation is deterministic bounded vocabulary, not model-generated prose.

### K — Hygiene by construction

D134 uses allowlisted fields, bounded identifiers, strict types, digests, and omission of raw text.

It does not claim anonymity.

### L — Deterministic safe fingerprint

A canonical SHA-256 fingerprint represents the safe experience shape for future deduplication.

The fingerprint grants no persistence or promotion authority.

### M — Promotion is negative-by-default

D134 may form a candidate only.

No automatic promotion exists.

### N — Memory lifecycle stays separate

D134 may not create, update, approve, reject, or archive Personal Memory.

The historical Owner-controlled Memory lifecycle remains authoritative.

### O — No D135 / D136 leakage

D134 does not score model capability, change routing/profile policy, invoke models, or own runtime orchestration.

D135 owns Model Intelligence.

D136 owns integrated Cognitive Executive / terminal hook wiring.

### P — Fail closed without harming the primary turn

Malformed, cross-turn, cross-workspace, incoherent, over-limit, or mismatched provenance produces no fabricated candidate.

A D134 failure never rewrites the primary terminal result.

## 4. Existing-System Reconciliation

### 4.1 D126 Cognitive Brain core

D126 already provides:

```text
CognitiveOrgan.EXPERIENCE_SYSTEM
CognitiveArtifactEnvelope
CognitiveTurnManifest
CognitiveTurnState
CognitiveFailureCode
COGNITIVE_REFERENCE_DIGEST_MAX_COUNT = 64
COGNITIVE_ARTIFACT_DIGEST_MAX_COUNT = 128
COGNITIVE_REVISION_COUNT_MAX = 1
```

D134 does not modify `backend/app/contracts/cognitive_brain.py`.

### 4.2 D127 task semantics

D134 may observe:

```text
interaction_intent
cognitive_intent
authoritative_ai_task_kind
```

from `CognitiveTaskDescription`.

It does not copy:

```text
normalized_request
required_information
information_gaps
constraints
```

into ExperienceCandidate.

`CognitiveTaskDescription.envelope.context_snapshot_digest` may legitimately be `None` because D127 task interpretation can predate Context freeze.

### 4.3 D132 metacognition

D134 may observe only:

```text
confidence_class
```

from the supplied same-turn D132 artifact.

D134 does not copy unknowns, assumptions, hypotheses, uncertainty text, or evidence-ID lists.

### 4.4 D133 verification / publication

D134 may observe bounded D133 metadata:

```text
verification.result
verification.issue_codes
publication_gate.disposition
publication_gate.critic_exhausted
revision_count
```

D134 does not copy Draft text or validated evidence contents.

### 4.5 Historical Memory

`MemoryService` remains Owner-controlled and explicitly does not learn memories automatically.

D134 does not import or invoke Memory mutation surfaces.

## 5. Exact Contract Constants

```text
D134_EXPERIENCE_ARTIFACT_TYPE
= "cognitive.experience_candidate"

D134_EXPERIENCE_CONTRACT_VERSION
= "o-ai.cognitive-experience-candidate.v1"

D134_EXPERIENCE_FINGERPRINT_VERSION
= "o-ai.cognitive-experience-fingerprint.v1"

D134_RETENTION_DISPOSITION
= "ephemeral"

D134_PROMOTION_DISPOSITION
= "candidate_only"
```

D134 reuses D126 identifier, digest, revision, and envelope bounds instead of introducing parallel authority semantics.

## 6. Exact Vocabulary

### 6.1 ExperienceOutcomeClass

Exactly:

```text
success
insufficient
failure
```

### 6.2 ExperienceLessonCode

Exactly:

```text
verified_success
bounded_insufficiency
critic_exhausted
invalid_cognition
terminal_failure
```

### 6.3 ExperienceRetentionDisposition

Exactly:

```text
ephemeral
```

### 6.4 ExperiencePromotionDisposition

Exactly:

```text
candidate_only
```

D134 V1 does not define:

```text
learned
trusted
confirmed
promoted
preferred_model
best_model
policy
auto_promote
```

as Experience states.

## 7. Exact ExperienceCandidate Artifact

```python
@dataclass(frozen=True, slots=True)
class CognitiveExperienceCandidateArtifact:
    envelope: CognitiveArtifactEnvelope

    terminal_state: CognitiveTurnState

    interaction_intent: CognitiveInteractionIntent | None
    cognitive_intent: CognitiveIntent | None
    authoritative_ai_task_kind: AITaskKind | None

    outcome_class: ExperienceOutcomeClass

    verification_result: VerificationResult | None
    verification_issue_codes: tuple[VerificationIssueCode, ...]

    publication_disposition: PublicationDisposition | None
    critic_exhausted: bool | None

    revision_count: int
    failure_code: CognitiveFailureCode | None

    observed_confidence_class: MetacognitiveConfidenceClass | None

    authorized_adapter_id: str | None
    authorized_model_id: str | None
    authorized_profile_id: str | None

    lesson_code: ExperienceLessonCode

    retention_disposition: ExperienceRetentionDisposition
    promotion_disposition: ExperiencePromotionDisposition

    candidate_fingerprint: str
```

The candidate contains no arbitrary free-text lesson.

## 8. Candidate Envelope

Exact envelope rules:

```text
producer_organ
= CognitiveOrgan.EXPERIENCE_SYSTEM

artifact_type
= "cognitive.experience_candidate"

contract_version
= "o-ai.cognitive-experience-candidate.v1"

status
= CognitiveOrganStatus.READY

model_binding_reference
= None
```

The envelope represents successful candidate formation, not the success/failure of the observed turn.

Exact identity:

```text
envelope.turn_id
== manifest.turn_id

envelope.workspace_id
== manifest.workspace_id

envelope.context_snapshot_digest
== manifest.context_snapshot_digest
```

Therefore an early failed turn may validly produce an Experience envelope with:

```text
context_snapshot_digest = None
```

if the terminal manifest also has `None`.

## 9. Terminal Manifest Requirement

`CognitiveTurnManifest` is required.

Exact rules:

```text
manifest.terminal_state != None
manifest.terminal_state ∈ {COMPLETED, INSUFFICIENT, FAILED}
```

A non-terminal manifest cannot form a candidate.

D134 never fabricates terminality.

## 10. Outcome Mapping

Deterministic mapping:

| terminal state | outcome_class |
|---|---|
| `COMPLETED` | `success` |
| `INSUFFICIENT` | `insufficient` |
| `FAILED` | `failure` |

No other mapping exists.

## 11. Provenance Reference Boundary — Rev 0.2

D126 permits:

```text
CognitiveTurnManifest.artifact_digests
max = 128
```

while `CognitiveArtifactEnvelope.input_reference_digests` permits:

```text
max = 64
```

D134 resolves this cardinality mismatch fail closed.

### 11.1 Eligible reference cardinality

Candidate formation requires:

```text
len(manifest.artifact_digests) <= 64
```

Then:

```text
candidate.envelope.input_reference_digests
==
manifest.artifact_digests
```

with exact membership and exact order.

### 11.2 Over-limit manifest

If:

```text
len(manifest.artifact_digests) > 64
```

candidate formation raises:

```text
CognitiveExperienceContractError
code = "contract_violation"
failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
diagnostic reason = "experience_reference_limit_exceeded"
```

and returns no candidate.

### 11.3 No projection or truncation

Forbidden:

```text
first 64
last 64
priority 64
random 64
silent omission
```

The complete manifest remains authoritative.

An Experience failure caused by this limit does not modify the primary terminal state.

## 12. Task Semantics Binding

`task` is optional only for terminal `FAILED`.

Operational rule:

```text
task is None
→ manifest.terminal_state must be FAILED
→ manifest.authoritative_ai_task_kind must be None
→ candidate.interaction_intent = None
→ candidate.cognitive_intent = None
→ candidate.authoritative_ai_task_kind = None
```

When `task` exists:

```text
task.envelope.turn_id
== manifest.turn_id

task.envelope.workspace_id
== manifest.workspace_id

task.authoritative_ai_task_kind
== manifest.authoritative_ai_task_kind

candidate.interaction_intent
== task.interaction_intent

candidate.cognitive_intent
== task.cognitive_intent

candidate.authoritative_ai_task_kind
== manifest.authoritative_ai_task_kind
```

Context rule for D127 task:

```text
task.envelope.context_snapshot_digest is None
OR
task.envelope.context_snapshot_digest
== manifest.context_snapshot_digest
```

A non-`None` task digest that disagrees with the manifest is a contract violation.

D134 never copies `normalized_request`.

## 13. Metacognition Binding

`metacognition` is required for:

```text
COMPLETED
INSUFFICIENT
```

and optional for `FAILED`.

If metacognition exists:

```text
task must exist

metacognition.envelope.turn_id
== manifest.turn_id

metacognition.envelope.workspace_id
== manifest.workspace_id

metacognition.envelope.context_snapshot_digest
== manifest.context_snapshot_digest

metacognition.intent
== task.cognitive_intent

candidate.observed_confidence_class
== metacognition.confidence_class
```

If metacognition is absent:

```text
candidate.observed_confidence_class = None
```

D134 does not copy metacognitive free-text collections.

## 14. Verification Binding

`verification` is required for `COMPLETED`.

It is optional for `INSUFFICIENT` and `FAILED`.

If verification exists:

```text
task must exist
metacognition must exist

verification.envelope.turn_id
== manifest.turn_id

verification.envelope.workspace_id
== manifest.workspace_id

verification.envelope.context_snapshot_digest
== manifest.context_snapshot_digest

verification.draft_revision_count
== manifest.revision_count

candidate.verification_result
== verification.result

candidate.verification_issue_codes
== verification.issue_codes
```

If verification is absent:

```text
candidate.verification_result = None
candidate.verification_issue_codes = ()
```

No missing result is guessed.

## 15. Publication Gate Binding

`publication_gate` is required for `COMPLETED`.

It is optional for `INSUFFICIENT` and `FAILED`.

If publication gate exists:

```text
verification must exist

publication_gate.envelope.turn_id
== manifest.turn_id

publication_gate.envelope.workspace_id
== manifest.workspace_id

publication_gate.envelope.context_snapshot_digest
== manifest.context_snapshot_digest

publication_gate.verification_result
== verification.result

publication_gate.draft_revision_count
== manifest.revision_count

publication_gate.draft_revision_count
== verification.draft_revision_count

publication_gate.draft_digest
== verification.draft_digest

candidate.publication_disposition
== publication_gate.disposition

candidate.critic_exhausted
== publication_gate.critic_exhausted
```

If publication gate is absent:

```text
candidate.publication_disposition = None
candidate.critic_exhausted = None
```

No missing disposition is inferred.

## 16. Manifest Model / Profile Observation

The following candidate fields are exact copies from the manifest:

```text
authorized_adapter_id
authorized_model_id
authorized_profile_id
```

They are provenance observations only.

D134 may not use them to:

```text
score
rank
prefer
ban
route
select provider
select model
select profile
invoke a provider
```

## 17. Manifest Revision / Failure Observation

Exact copies:

```text
candidate.revision_count
== manifest.revision_count

candidate.failure_code
== manifest.failure_code
```

D134 does not invent a failure code.

For `INSUFFICIENT`, if `manifest.failure_code` is non-`None`, the only coherent value is:

```text
CognitiveFailureCode.INSUFFICIENT_EVIDENCE
```

For `COMPLETED`:

```text
failure_code = None
```

For `FAILED`, D126 already requires:

```text
failure_code != None
```

## 18. COMPLETED Coherence

A `COMPLETED` candidate requires:

```text
manifest.context_snapshot_digest != None
task present
metacognition present
verification present
publication_gate present

verification.result = "pass"
publication_gate.disposition = "eligible"
publication_gate.critic_exhausted = False
manifest.failure_code = None
```

Then:

```text
outcome_class = "success"
lesson_code = "verified_success"
```

D134 does not interpret `PASS` as universal truth.

## 19. INSUFFICIENT Coherence

An `INSUFFICIENT` candidate requires:

```text
manifest.context_snapshot_digest != None
task present
metacognition present
```

Metacognition must already represent bounded insufficiency through its frozen D132 self-consistency.

If verification exists:

```text
verification.result = "insufficient_evidence"
```

If publication gate exists:

```text
publication_gate.disposition = "bounded_insufficiency_only"
publication_gate.critic_exhausted = False
```

If `manifest.failure_code` is non-`None`:

```text
manifest.failure_code
= CognitiveFailureCode.INSUFFICIENT_EVIDENCE
```

Then:

```text
outcome_class = "insufficient"
lesson_code = "bounded_insufficiency"
```

## 20. FAILED Coherence

For `FAILED`:

```text
manifest.failure_code != None
```

Task, metacognition, verification, and publication gate are optional subject to the dependency chain:

```text
publication_gate
→ requires verification

verification
→ requires metacognition

metacognition
→ requires task
```

This permits bounded observation of failures at different cognitive stages.

A failed turn may still have a prior D133 `PASS`/`eligible` observation if the primary terminal failure occurred later. D134 must not rewrite that later failure into success.

## 21. Lesson-Code Precedence

Exact deterministic precedence:

```text
if publication_gate is present
and publication_gate.critic_exhausted is True:
    lesson_code = "critic_exhausted"

elif verification is present
and verification.result == "invalid_cognition":
    lesson_code = "invalid_cognition"

elif manifest.terminal_state == FAILED:
    lesson_code = "terminal_failure"

elif manifest.terminal_state == INSUFFICIENT:
    lesson_code = "bounded_insufficiency"

elif manifest.terminal_state == COMPLETED:
    lesson_code = "verified_success"
```

No model or heuristic chooses the lesson code.

## 22. Candidate Fingerprint

Public helper:

```python
compute_cognitive_experience_fingerprint(
    *,
    workspace_id,
    terminal_state,
    interaction_intent,
    cognitive_intent,
    authoritative_ai_task_kind,
    outcome_class,
    verification_result,
    verification_issue_codes,
    publication_disposition,
    critic_exhausted,
    revision_count,
    failure_code,
    observed_confidence_class,
    authorized_adapter_id,
    authorized_model_id,
    authorized_profile_id,
    lesson_code,
) -> str
```

The canonical payload is:

```json
{
  "fingerprint_version": "o-ai.cognitive-experience-fingerprint.v1",
  "workspace_id": "<workspace value>",
  "terminal_state": "<terminal state value>",
  "interaction_intent": null,
  "cognitive_intent": null,
  "authoritative_ai_task_kind": null,
  "outcome_class": "<outcome>",
  "verification_result": null,
  "verification_issue_codes": [],
  "publication_disposition": null,
  "critic_exhausted": null,
  "revision_count": 0,
  "failure_code": null,
  "observed_confidence_class": null,
  "authorized_adapter_id": null,
  "authorized_model_id": null,
  "authorized_profile_id": null,
  "lesson_code": "<lesson code>"
}
```

Enum-like fields serialize to their canonical string values.

`verification_issue_codes` serializes as a JSON array preserving exact tuple order.

Serialization:

```text
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
UTF-8
SHA-256 lowercase hexadecimal
```

The candidate must satisfy:

```text
candidate.candidate_fingerprint
==
recomputed canonical fingerprint
```

### 22.1 Deliberately excluded from the fingerprint

The fingerprint excludes:

```text
turn_id
conversation_id
project_id
ContextSnapshot digest
artifact digests
created_at
raw text
```

This permits future same-shape deduplication across turns while keeping deduplication isolated by `workspace_id`.

Fingerprint identity is not truth, promotion, persistence, or global identity.

## 23. Retention Boundary

Every D134 V1 candidate has:

```text
retention_disposition = "ephemeral"
```

There is no other valid retention value.

Future durable Experience persistence requires a separately frozen contract defining at least:

```text
retention / TTL
per-workspace quota
per-candidate size limit
deduplication / fingerprint policy
promotion lifecycle
Owner inspection / deletion
archival / expiry
```

D134 V1 activates none of these persistence mechanisms.

## 24. Promotion Boundary

Every D134 V1 candidate has:

```text
promotion_disposition = "candidate_only"
```

D134 V1 provides no:

```text
promote()
approve()
apply()
learn()
write_memory()
update_policy()
rewrite_prompt()
change_route()
modify_code()
```

method or authority.

## 25. Hygiene / Data-Minimization Boundary

ExperienceCandidate must not contain:

```text
normalized_request
raw user message
raw assistant response
Draft text
Context text
Knowledge content
Memory value
system prompt
provider prompt
hidden reasoning
chain-of-thought
credential
API key
OAuth token
arbitrary exception text
arbitrary lesson prose
```

Allowed content is limited to:

```text
bounded enums / statuses
bounded safe manifest identifiers
safe task categories
safe model/profile identifiers
digests
verification issue codes
failure codes
revision count
fingerprint
```

D134 uses minimization and bounded metadata. It does not claim anonymity.

## 26. Exact Coordinator Interface

```python
CognitiveExperienceCoordinator.form_candidate(
    envelope,
    manifest,
    *,
    task=None,
    metacognition=None,
    verification=None,
    publication_gate=None,
) -> CognitiveExperienceCandidateArtifact
```

The coordinator is deterministic and side-effect free.

It performs no:

```text
database write
repository read/write
Context re-read
Memory read/write
Knowledge retrieval
network access
AI invocation
routing
provider selection
profile selection
scheduler registration
background task creation
```

## 27. Contract Error

```python
class CognitiveExperienceContractError(Exception):
    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

Malformed or incoherent input raises this exception and yields no fabricated candidate.

The over-limit provenance case has the exact diagnostic reason:

```text
experience_reference_limit_exceeded
```

Contract failure is local to Experience processing and grants no authority to rewrite the primary turn.

## 28. Idempotence

For exact same inputs, including the exact same supplied envelope:

```text
Candidate A == Candidate B
```

The semantic fingerprint is deterministic independently of envelope timestamp.

Two otherwise equivalent candidates with different turn IDs / timestamps may have different artifact envelopes while retaining the same semantic fingerprint.

## 29. LLM Boundary

D134 V1 performs:

```text
LLM invocation count = 0
```

D134 does not add a new invocation purpose to D126.

The existing:

```text
PRIMARY_SYNTHESIS
CRITIC
REVISION
POST_REVISION_CRITIC
```

purposes remain unchanged.

## 30. Primary-Turn Failure Isolation

D134 is a bounded post-turn hook contract.

Exact invariant:

```text
primary turn = COMPLETED
Experience formation = contract failure
→ primary turn remains COMPLETED

primary turn = INSUFFICIENT
Experience formation = contract failure
→ primary turn remains INSUFFICIENT

primary turn = FAILED
Experience formation = contract failure
→ primary turn remains FAILED
```

D134 has no API to change the manifest terminal state.

Actual runtime isolation/wiring belongs to D136.

## 31. No Working-State Attachment

D134 does not modify:

```text
backend/app/intelligence/context/cognitive.py
```

and does not attach ExperienceCandidate to Cognitive Working State.

This prevents post-terminal mutation of the D128–D133 cognitive chain.

## 32. D135 Boundary

Outside D134:

```text
model capability scoring
model benchmark aggregation
model strength/weakness knowledge
preferred model evaluation
routing policy
profile policy
```

These belong to D135 Model Intelligence & Capability Knowledge V1.

## 33. D136 Boundary

Outside D134:

```text
integrated post-turn hook invocation
Cognitive Executive sequencing
turn deadline enforcement
stage budgets
circuit breakers
late-result enforcement
fresh AI authorization per call
actual Critic / Revision orchestration
scheduler/runtime lifecycle
```

These belong to D136 Cognitive Executive / Integrated Brain Runtime V1.

## 34. Exact Implementation Scope

Exactly four implementation paths:

```text
NEW backend/app/contracts/cognitive_experience.py
NEW backend/app/services/cognitive_experience.py
NEW backend/tests/test_d134_cognitive_experience.py
NEW backend/tests/test_d134_cognitive_experience_security.py
```

Any fifth implementation path:

```text
STOP
→ dependency / contradiction report
→ Owner amendment review
```

## 35. Explicitly Unmodified Areas

D134 implementation must not modify:

```text
backend/app/contracts/cognitive_brain.py
backend/app/intelligence/context/cognitive.py

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

Memory models/repositories/services/APIs
Context models/repositories/services
Conversation models/repositories/services
Knowledge retrieval
Execution audit
D104/D105 routing
D125 model/profile routing
AIRuntime
AIAdapter
database
Alembic
API
frontend
```

Historical tests may not be edited to make D134 pass.

## 36. Functional Test Contract

Exact file:

```text
backend/tests/test_d134_cognitive_experience.py
```

Exact count:

```text
F01–F44
44 functional tests
```

Frozen functional matrix:

```text
F01 exact constants
F02 exact outcome vocabulary
F03 exact lesson vocabulary
F04 exact retention / promotion vocabulary
F05 valid COMPLETED revision 0
F06 valid COMPLETED revision 1
F07 COMPLETED task metadata projection
F08 manifest adapter/model/profile projection
F09 metacognitive confidence projection
F10 PASS verification issue projection
F11 valid INSUFFICIENT with D133 artifacts
F12 valid INSUFFICIENT from D132 without D133 artifacts
F13 valid early FAILED with no Context / task
F14 valid FAILED with task but no metacognition
F15 valid FAILED with metacognition but no verification
F16 valid FAILED invalid-cognition verification
F17 valid FAILED critic exhaustion
F18 valid FAILED after prior PASS / eligible
F19 COMPLETED outcome mapping
F20 INSUFFICIENT outcome mapping
F21 FAILED outcome mapping
F22 critic-exhausted lesson precedence
F23 invalid-cognition lesson precedence
F24 terminal-failure lesson mapping
F25 bounded-insufficiency lesson mapping
F26 verified-success lesson mapping
F27 fingerprint determinism
F28 fingerprint independent of created_at / turn identity
F29 fingerprint independent of conversation / project identity
F30 fingerprint changes across workspace
F31 fingerprint changes with task semantics
F32 fingerprint changes with outcome
F33 fingerprint changes with verification issues
F34 fingerprint changes with model/profile observation
F35 fingerprint preserves verification-issue order
F36 empty provenance reference sequence
F37 exact <=64 provenance reference copying
F38 failed no-task projection produces None task fields
F39 absent verification produces None / empty projections
F40 absent publication gate produces None projections
F41 candidate is frozen / slots-based
F42 bounded sequence values are immutable tuples
F43 exact repeated invocation is idempotent
F44 source artifacts / manifest remain unchanged
```

## 37. Security Test Contract

Exact file:

```text
backend/tests/test_d134_cognitive_experience_security.py
```

Exact count:

```text
S01–S80
80 security tests
```

Frozen security matrix:

```text
S01 wrong Experience envelope producer rejected
S02 wrong Experience artifact type rejected
S03 wrong Experience contract version rejected
S04 non-READY Experience envelope rejected
S05 Experience model binding rejected
S06 wrong manifest type rejected
S07 non-terminal manifest rejected
S08 envelope turn mismatch rejected
S09 envelope workspace mismatch rejected
S10 envelope Context digest mismatch rejected

S11 manifest artifact refs >64 fail closed
S12 >64 exact reason is experience_reference_limit_exceeded
S13 envelope refs missing manifest ref rejected
S14 envelope refs adding ref rejected
S15 envelope refs reordering rejected
S16 no silent first-64 projection
S17 no silent last-64 projection
S18 no source-manifest mutation on ref failure
S19 malformed fingerprint rejected
S20 mismatched recomputed fingerprint rejected

S21 invalid outcome literal rejected
S22 invalid lesson literal rejected
S23 invalid retention literal rejected
S24 invalid promotion literal rejected
S25 non-terminal candidate state rejected
S26 revision overflow rejected
S27 non-boolean critic exhaustion rejected
S28 invalid verification issue sequence rejected
S29 duplicate verification issues rejected
S30 invalid task type rejected

S31 task turn mismatch rejected
S32 task workspace mismatch rejected
S33 non-None task Context mismatch rejected
S34 task kind mismatch with manifest rejected
S35 task absent on COMPLETED rejected
S36 task absent on INSUFFICIENT rejected
S37 task absent with manifest task kind present rejected
S38 metacognition wrong type rejected
S39 metacognition without task rejected
S40 metacognition turn mismatch rejected

S41 metacognition workspace mismatch rejected
S42 metacognition Context mismatch rejected
S43 metacognition intent mismatch rejected
S44 COMPLETED missing metacognition rejected
S45 INSUFFICIENT missing metacognition rejected
S46 verification wrong type rejected
S47 verification without metacognition rejected
S48 verification turn mismatch rejected
S49 verification workspace mismatch rejected
S50 verification Context mismatch rejected

S51 verification revision mismatch rejected
S52 COMPLETED missing verification rejected
S53 COMPLETED non-PASS verification rejected
S54 INSUFFICIENT supplied non-insufficient verification rejected
S55 publication gate wrong type rejected
S56 publication gate without verification rejected
S57 publication gate turn mismatch rejected
S58 publication gate workspace mismatch rejected
S59 publication gate Context mismatch rejected
S60 publication / verification result mismatch rejected

S61 publication / verification draft digest mismatch rejected
S62 publication revision mismatch rejected
S63 COMPLETED missing publication gate rejected
S64 COMPLETED non-eligible disposition rejected
S65 COMPLETED critic exhaustion rejected
S66 INSUFFICIENT non-bounded disposition rejected
S67 INSUFFICIENT critic exhaustion rejected
S68 INSUFFICIENT unrelated manifest failure code rejected
S69 candidate adapter id must equal manifest
S70 candidate model id must equal manifest

S71 candidate profile id must equal manifest
S72 raw normalized request absent from candidate fields
S73 raw Draft / response text absent from candidate fields
S74 raw Context / Memory / Knowledge fields absent
S75 hidden reasoning / prompt / credential fields absent
S76 no Memory mutation / promotion surface
S77 no persistence / DB / repository / migration surface
S78 no provider / network / model invocation or routing surface
S79 no scheduler / background-loop / D136 runtime surface
S80 no model-scoring / preferred-model / D135 authority surface
```

## 38. Exact Targeted Historical Regression

Exactly 27 files:

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
backend/tests/test_personal_memory.py
backend/tests/test_memory_aware_chat.py
backend/tests/test_conversation_memory.py
backend/tests/test_context_provenance_contract.py
backend/tests/test_context_snapshot.py
backend/tests/test_context_snapshot_persistence.py
backend/tests/test_conversation_dependency_wiring.py
backend/tests/test_execution_audit.py
backend/tests/test_execution_audit_contract.py
backend/tests/test_durable_execution_audit.py
backend/tests/test_message_citations.py
```

Historical tests may not be edited to make D134 pass.

## 39. Validation Protocol

```text
1. branch / baseline / origin / remote verification
2. frozen D134 spec SHA verification
3. exact four-path implementation scope verification
4. D134 functional F01–F44
5. D134 security S01–S80
6. exact 27-file historical targeted regression
7. full backend regression
8. final exact implementation scope / hashes / spec verification
9. Owner Guided Acceptance
10. separate local implementation commit authorization
11. verify local implementation commit
12. separate normal implementation push authorization
13. independent remote implementation verification
14. milestone close
```

## 40. Owner Guided Acceptance Intent

At least:

```text
A. Experience runs only after terminality.
B. COMPLETED / INSUFFICIENT / FAILED may be evaluated.
C. Experience failure never rewrites the primary terminal result.
D. Experience does not attach back into Working State.
E. Candidate is ephemeral in D134 V1.
F. Candidate contains no raw request/response/Context/Memory/Knowledge text.
G. ExperienceCandidate cannot become Memory automatically.
H. ExperienceCandidate cannot mutate Policy, Prompt, Routing, or Code.
I. D134 performs zero LLM/provider invocations.
J. Model/profile IDs are provenance observations only.
K. Fingerprint is deterministic but grants no authority.
L. Manifest artifact references are never silently truncated.
M. >64 manifest refs fail Experience formation only.
N. D134 creates no DB/API/repository/scheduler/background learner.
O. D134 does not leak into D135 model intelligence or D136 runtime ownership.
P. D126–D133, Memory, routing, execution, and historical behavior remain unchanged.
```

## 41. Design Freeze Scope

D134 Design Freeze changes exactly one path:

```text
docs/specs/D134_EXPERIENCE_LEARNING_BOUNDARY_V1.md
```

Design Freeze commit subject:

```text
docs: freeze D134 experience learning boundary design
```

This Design Freeze authorization permits the local spec commit only.

It does not authorize:

```text
push
implementation
implementation commit
implementation push
reset
rebase
force
```

## 42. Current Gate State

```text
D134 BASELINE:
d9a83c8d2a62e91a5c173dcc0cac146c86b5d0df

D133 STATUS:
COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED

D134 OWNER DESIGN RECONCILIATION A–P:
PASS / OWNER APPROVED

D134 EXACT CONTRACT PROPOSAL REV 0.1:
OWNER APPROVED / SUPERSEDED BY REV 0.2

D134 EXACT CONTRACT PROPOSAL REV 0.2:
OWNER APPROVED

D134 FINAL CONTRACT REVIEW REV 0.2:
PASS

D134 DESIGN FREEZE:
YES — OWNER AUTHORIZED

D134 IMPLEMENTATION:
NOT AUTHORIZED / NOT STARTED

IMPLEMENTATION CODE CHANGE:
NONE

GIT PUSH:
NOT AUTHORIZED / NOT PUSHED
```

**End of D134 Experience / Learning Boundary V1 — Rev 0.2 Frozen Design Baseline**
