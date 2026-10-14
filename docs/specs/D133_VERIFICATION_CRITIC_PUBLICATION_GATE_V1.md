# D133 — Verification / Critic & Publication Gate V1

**Document status:** DESIGN AMENDED — OWNER APPROVED
**Design revision:** Rev 0.2 — OWNER-APPROVED AMENDMENT TO REV 0.1
**Architecture:** O-AI Cognitive Brain Architecture V1
**Milestone:** D133 — Verification / Critic & Publication Gate V1
**Baseline commit:** `265e02ca3c1882ea07bd1642943eea1909e1112d`
**Baseline state:** D132 COMPLETE / PUSHED / INDEPENDENTLY REMOTE VERIFIED
**Owner Design Reconciliation A–N:** PASS
**Owner Exact Contract Proposal Rev 0.1 approval:** YES
**Owner Design Amendment Rev 0.2 approval:** YES
**Final Contract Review:** PASS
**Design Freeze:** YES — OWNER AUTHORIZED
**Implementation authorization:** RECEIVED — PAUSED PENDING AMENDMENT REMOTE VERIFICATION
**Implementation mutation:** NONE
**Code change:** DESIGN SPEC ONLY
**Commit:** DESIGN AMENDMENT COMMIT
**Push:** NOT PUSHED

---

## 1. Purpose

D133 introduces the Brain-facing **Verification / Critic & Publication Gate V1** boundary.

D133 answers bounded questions about a candidate draft after D132 Metacognition and after an authorized primary synthesis has produced a Draft Response / Draft Cognition:

- Is the draft structurally coherent with the same cognitive turn?
- Is it bound to the same workspace and frozen ContextSnapshot?
- Does its response mode respect D132 metacognitive state?
- Are draft citation IDs valid against the supplied frozen grounding evidence?
- Are supplied evidence and conflict records consistent with the frozen ContextSnapshot?
- Is the draft repairable by one bounded revision?
- Is there valid insufficient evidence that requires a bounded insufficiency path?
- Is the cognition invalid and therefore non-publishable?
- Is the draft eligible to proceed to downstream finalization?

D133 does **not** prove unrestricted semantic truth, retrieve new evidence, invoke a model, execute revision, select a provider/model/profile, persist a response, learn, or execute an action.

The governing boundary is:

```text
Verification result     ≠ Truth oracle
Critic opinion          ≠ Authority
PASS                    ≠ Final publication
REVISE                  ≠ Revision execution
Publication eligibility ≠ Message persistence
Model advisory          ≠ Deterministic override
```

## 2. Architecture Position

Canonical flow:

```text
D130 Reasoning
      ↓
D130 Prediction
      ↓
D131 Planning
      ↓
D131 Decision / Goal
      ↓
D132 Metacognition
      ↓
Authorized PRIMARY_SYNTHESIS
      ↓
Draft Response / Draft Cognition
      ↓
D133 Verification / Critic
      ↓
D133 Publication Gate
      ↓
Downstream Finalization
      ↓
Final Response
```

D133 sits after draft production and before final response publication.

Actual `CRITIC`, `REVISION`, and `POST_REVISION_CRITIC` model invocations remain outside D133 runtime ownership and are reserved for D136 Cognitive Executive integration.

## 3. Frozen Design Reconciliation A–N

### A — Frozen upstream

D126–D132 remain frozen historical upstream. D133 must not alter Reasoning, Prediction, Planning, Decision/Goal, Metacognition, routing, runtime, or provider authority.

### B — Exact sequence

D133 evaluates a candidate draft only after D132 Metacognition and draft synthesis. It does not move ahead of Metacognition or replace draft synthesis.

### C — Reuse first

D133 reuses existing foundations where their real semantics fit:

```text
CitationEngine
ConflictDetector
ContextSnapshot integrity
existing schema / contract validation
D132 metacognitive state
D126 revision-count limit
```

D133 must not create a parallel replacement for these historical components.

### D — No re-retrieval

D133 consumes only already-frozen same-turn cognitive state plus explicitly supplied frozen grounding. It does not re-read or re-retrieve Context, Memory, Knowledge, repositories, network resources, or external sources.

### E — Ordered verification

Verification order:

```text
1. deterministic contract / binding / provenance invariants
2. frozen evidence / citation / conflict checks
3. structured draft / schema coherence
4. optional advisory critic result merge
```

### F — Deterministic veto dominance

An advisory critic can never downgrade a deterministic result.

### G — Canonical result vocabulary

Exactly:

```text
pass
revise
insufficient_evidence
invalid_cognition
```

No probability, score, percentage, rank, or confidence number is introduced.

### H — Publication Gate is separate

Verification result does not itself publish a response. Publication Gate produces a non-authoritative disposition only.

### I — Bounded revision semantics

Automatic revision eligibility is bounded by the existing D126 maximum:

```text
COGNITIVE_REVISION_COUNT_MAX = 1
```

D133 defines revision eligibility but does not execute revision.

### J — Critic exhaustion

If a revision-count-1 draft still results in `revise`, publication is blocked and Critic exhaustion is explicit.

### K — No model authority

D133 does not select provider, model, profile, adapter, routing, fallback, retry, or authorization.

### L — Ephemeral cognition

Draft verification artifacts, Critic results, and publication dispositions are ephemeral in D133 V1.

### M — Working State coherence

Draft, Verification, and Publication Gate artifacts are same-turn immutable attachments bound to the same turn, workspace, ContextSnapshot digest, draft digest, and revision count.

### N — No D134 / D136 leakage

D133 does not implement Experience learning, Cognitive Executive model-call orchestration, deadlines, circuit breakers, late-result enforcement, or revision execution.

## 4. Existing-System Reconciliation

### 4.1 D126 Cognitive Brain

D126 already provides:

```text
CognitiveOrgan.COMMUNICATION_RESPONSE
CognitiveOrgan.VERIFICATION_CRITIC

CognitiveInvocationPurpose.PRIMARY_SYNTHESIS
CognitiveInvocationPurpose.CRITIC
CognitiveInvocationPurpose.REVISION
CognitiveInvocationPurpose.POST_REVISION_CRITIC

CognitiveFailureCode.INVALID_COGNITION
CognitiveFailureCode.INSUFFICIENT_EVIDENCE
CognitiveFailureCode.CRITIC_UNAVAILABLE
CognitiveFailureCode.CONTRACT_VIOLATION

COGNITIVE_REVISION_COUNT_MAX = 1
```

Therefore D133 does not modify:

```text
backend/app/contracts/cognitive_brain.py
```

### 4.2 D129 ContextSnapshot

D133 relies on the already-frozen D129 `CognitiveContextArtifact` and its D96 `ContextSnapshot`.

For Knowledge items, D96 provenance already binds:

```text
Context source_id          = Knowledge chunk id
provenance.parent_source_id = document id
provenance.source_locator   = source locator
provenance.content_sha256   = exact frozen Context text digest
```

D133 validates supplied grounding against this frozen snapshot and performs no source re-observation.

### 4.3 Historical CitationEngine

Historical behavior:

```python
CitationEngine.validate(
    answer,
    evidence,
) -> (sanitized_answer, valid_evidence)
```

It recognizes `S<number>` citation IDs and removes unknown citation IDs from the returned sanitized text.

D133 reuses this validator but does **not** silently replace the Draft with the sanitized text.

Exact D133 rule:

```text
sanitized text == original draft text
→ citation syntax/provenance check may continue

sanitized text != original draft text
→ REVISE
→ original Draft remains unchanged
```

`CitationEngine` is not a semantic entailment engine and D133 must not describe it as one.

### 4.4 Historical ConflictDetector

Historical `ConflictDetector` detects a bounded subset of source conflicts.

D133 consumes the already-produced frozen conflict records supplied with grounding.

Exact meaning:

```text
known conflict citation missing from the Draft
→ REVISE

conflict references citation/evidence outside supplied frozen grounding
→ CONTRACT_VIOLATION

no detected conflict
≠ proof that no semantic conflict exists
```

D133 does not claim complete contradiction detection.

### 4.5 D132 Metacognition

D133 consumes:

```text
knowledge_status
evidence_sufficiency
confidence_class
recommended_cognitive_action
```

D133 does not recalculate D132 epistemic state.

## 5. Exact Contract Constants

```text
D133_DRAFT_ARTIFACT_TYPE = "cognitive.draft_response"
D133_DRAFT_CONTRACT_VERSION = "o-ai.cognitive-draft-response.v1"

D133_VERIFICATION_ARTIFACT_TYPE = "cognitive.verification"
D133_VERIFICATION_CONTRACT_VERSION = "o-ai.cognitive-verification.v1"

D133_PUBLICATION_GATE_ARTIFACT_TYPE = "cognitive.publication_gate"
D133_PUBLICATION_GATE_CONTRACT_VERSION = "o-ai.cognitive-publication-gate.v1"

D133_DRAFT_TEXT_MAX_BYTES = 65536
D133_ISSUE_MAX_COUNT = 64
D133_CITATION_MAX_COUNT = 12
```

No input truncation is permitted. Draft text, grounding evidence, grounding conflicts, and verification inputs must be validated in full. Rev 0.2 adds one explicit exception for the **diagnostic projection** `validated_citation_ids`: when more than 12 distinct valid citation IDs appear, the full set is inspected to produce `citation_limit_exceeded`, while the artifact stores only the first 12 distinct valid IDs in first-appearance order. This projection cap never mutates the Draft, never removes grounding, and never hides the overflow issue.

## 6. Exact Vocabulary

### 6.1 Verification Result

```text
pass
revise
insufficient_evidence
invalid_cognition
```

### 6.2 Draft Response Mode

```text
response
uncertainty
insufficiency
owner_question
```

### 6.3 Publication Disposition

```text
eligible
bounded_insufficiency_only
revision_required
blocked
```

### 6.4 Verification Issue Codes

Exact bounded issue vocabulary:

```text
response_mode_mismatch
citation_required
citation_unknown
citation_limit_exceeded
conflict_citation_missing
evidence_insufficient
metacognition_revision_required
advisory_revise
advisory_insufficient_evidence
advisory_invalid_cognition
critic_exhausted
```

Issue codes are diagnostic metadata only and grant no authority.

Rev 0.2 clarification:

```text
critic_exhausted
→ reserved vocabulary only in D133 V1
→ CognitiveVerificationArtifact does not emit this issue code
→ canonical exhaustion signal is
   CognitivePublicationGateArtifact.critic_exhausted
```

## 7. Draft Artifact

```python
@dataclass(frozen=True, slots=True)
class CognitiveDraftResponseArtifact:
    envelope: CognitiveArtifactEnvelope
    response_mode: DraftResponseMode
    text: str
    revision_count: int
```

### 7.1 Draft Envelope

```text
producer_organ = CognitiveOrgan.COMMUNICATION_RESPONSE
artifact_type = "cognitive.draft_response"
contract_version = "o-ai.cognitive-draft-response.v1"
status = READY
context_snapshot_digest != None
```

`model_binding_reference` may be `None` or a valid opaque digest identifying the already-authorized synthesis binding.

It is provenance only and is never authorization.

### 7.2 Draft text

Draft text must:

```text
be str
be non-empty
be exact / not silently normalized
encode as UTF-8
be <= 65536 UTF-8 bytes
contain no NUL
contain no disallowed control characters
```

LF and TAB are permitted. CR and other control characters are rejected.

### 7.3 Revision count

```text
0 or 1 only
```

The limit reuses D126 `COGNITIVE_REVISION_COUNT_MAX`.

## 8. Exact Draft Digest

D133 binds Verification and Publication Gate to one exact draft.

Canonical digest payload:

```json
{
  "context_snapshot_digest": "<digest>",
  "response_mode": "<mode>",
  "revision_count": 0,
  "text": "<exact draft text>",
  "turn_id": "<turn>",
  "workspace_id": "<workspace value>"
}
```

Serialization:

```text
UTF-8 JSON
sort_keys = True
separators = (",", ":")
ensure_ascii = False
```

Digest:

```text
sha256(canonical_json_bytes).hexdigest()
```

The helper is:

```python
compute_cognitive_draft_digest(
    draft: CognitiveDraftResponseArtifact,
) -> str
```

## 9. Frozen Verification Grounding Input

D133 service uses an ephemeral service-level value:

```python
@dataclass(frozen=True, slots=True)
class CognitiveVerificationGrounding:
    context_snapshot_digest: str
    evidence: tuple[Evidence, ...]
    conflicts: tuple[Conflict, ...]
```

`Evidence` and `Conflict` are the existing historical structures from:

```text
backend/app/services/knowledge_intelligence.py
```

This is reuse, not a new evidence system.

The grounding object is not persisted and is not attached as a durable artifact.

## 10. Grounding Integrity Contract

Grounding must match the same frozen `CognitiveContextArtifact`.

### 10.1 Context digest

```text
grounding.context_snapshot_digest
==
context.snapshot.snapshot_digest
```

Mismatch:

```text
CONTRACT_VIOLATION
```

### 10.2 Evidence identity

Each supplied `Evidence` must match one Knowledge item in the frozen ContextSnapshot:

```text
evidence.chunk_id
==
snapshot_item.item.source.source_id

evidence.document_id
==
snapshot_item.provenance.parent_source_id

evidence.source_locator
==
snapshot_item.provenance.source_locator

evidence.content
==
snapshot_item.item.text
```

The snapshot item must be:

```text
ContextLayer.KNOWLEDGE
```

Duplicate chunk IDs or duplicate citation IDs are rejected.

Every non-empty citation ID must match:

```text
S[1-9][0-9]*
```

Grounding may not invent evidence outside the frozen ContextSnapshot.

### 10.3 Grounding completeness

The supplied grounding evidence set must correspond exactly to the Knowledge items supplied for verification from the frozen same-turn Context.

No silent addition, omission, source substitution, workspace substitution, or content replacement is permitted.

### 10.4 Conflicts

Every `Conflict.citation_ids` entry must refer to a supplied grounding evidence citation ID.

Unknown or malformed conflict references:

```text
CONTRACT_VIOLATION
```

Grounding conflict count is bounded by `D133_ISSUE_MAX_COUNT`.

## 11. D132 → Draft Mode Coherence

Exact mapping:

| D132 recommended action | Allowed Draft mode |
|---|---|
| `respond` | `response` |
| `respond_with_uncertainty` | `uncertainty` |
| `ask_owner` | `owner_question` |
| `insufficient_information` | `insufficiency` |
| `revise_reasoning` | no publishable Draft is valid |

Rules:

```text
revise_reasoning + Draft present
→ INVALID_COGNITION

other action/mode mismatch
→ REVISE
→ issue: response_mode_mismatch
```

D133 does not change the D132 recommended action.

## 12. Verification Artifact

```python
@dataclass(frozen=True, slots=True)
class CognitiveVerificationArtifact:
    envelope: CognitiveArtifactEnvelope

    result: VerificationResult
    response_mode: DraftResponseMode
    draft_revision_count: int
    draft_digest: str

    issue_codes: tuple[VerificationIssueCode, ...]
    validated_citation_ids: tuple[str, ...]

    advisory_result: VerificationResult | None
    advisory_binding_reference: str | None

    failure_code: CognitiveFailureCode | None
```

### 12.1 Verification Envelope

```text
producer_organ = CognitiveOrgan.VERIFICATION_CRITIC
artifact_type = "cognitive.verification"
contract_version = "o-ai.cognitive-verification.v1"
context_snapshot_digest != None
model_binding_reference = None
```

The coordinator is deterministic even when it merges a separately supplied advisory result.

### 12.2 Advisory pair consistency

```text
advisory_result is None
↔ advisory_binding_reference is None
```

If advisory result exists, advisory binding reference must be a valid opaque digest.

The advisory binding never becomes provider/model selection authority.

## 13. Verification Self-Consistency Matrix

| result | envelope status | failure_code |
|---|---|---|
| `pass` | READY | `None` |
| `revise` | READY | `None` |
| `insufficient_evidence` | INSUFFICIENT | `INSUFFICIENT_EVIDENCE` |
| `invalid_cognition` | FAILED | `INVALID_COGNITION` |

Additional exact rules:

```text
PASS
→ issue_codes empty

non-PASS
→ issue_codes non-empty

validated_citation_ids
→ unique
→ ordered by first appearance in Draft
→ max 12 stored diagnostic IDs
→ if the Draft contains >12 distinct valid IDs, the full set is still inspected,
  result is REVISE with citation_limit_exceeded, and only the first 12 are stored

draft_revision_count
→ 0 or 1
```

## 14. Exact Verification Coordinator Interfaces

```python
CognitiveVerificationCoordinator.verify(
    envelope,
    draft,
    context,
    metacognition,
    grounding,
    *,
    advisory_result=None,
    advisory_binding_reference=None,
) -> CognitiveVerificationArtifact
```

Publication Gate is a separate deterministic step:

```python
CognitiveVerificationCoordinator.evaluate_publication_gate(
    envelope,
    draft,
    verification,
) -> CognitivePublicationGateArtifact
```

D133 does not call AI in either method.

## 15. Contract / Binding / Provenance Failures

Malformed or incoherent inputs fail closed as:

```python
class CognitiveVerificationContractError(Exception):
    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

Contract violation examples include:

```text
wrong artifact type/version/producer
wrong turn
wrong workspace
wrong ContextSnapshot digest
malformed draft
invalid revision count
invalid grounding type
grounding digest mismatch
grounding evidence outside frozen Context
grounding content mismatch
duplicate evidence identity
duplicate citation identity
unknown conflict citation
malformed advisory pair
invalid digest
```

A contract violation produces no fabricated Verification result.

## 16. Deterministic Verification Checks

After contract/binding/provenance validity is established:

### 16.1 Invalid cognition

```text
D132 recommended action == revise_reasoning
AND a Draft is supplied
→ INVALID_COGNITION
→ issue: metacognition_revision_required
```

### 16.2 Response-mode mismatch

Any non-`revise_reasoning` mismatch against Section 11:

```text
→ REVISE
→ issue: response_mode_mismatch
```

### 16.3 CitationEngine reuse

D133 calls historical:

```python
sanitized, valid = CitationEngine().validate(
    draft.text,
    grounding.evidence,
)
```

If:

```text
sanitized != draft.text
```

then:

```text
→ REVISE
→ issue: citation_unknown
```

The original Draft is never replaced by `sanitized`.

### 16.4 Citation count — Rev 0.2 amended

All distinct valid citation IDs in the Draft are inspected before any diagnostic projection cap is applied.

Exact rule:

```text
if distinct valid citation count <= 12:
    validated_citation_ids
    = all distinct valid IDs
      in first-appearance order

if distinct valid citation count > 12:
    result = REVISE
    issue = citation_limit_exceeded

    validated_citation_ids
    = first 12 distinct valid IDs
      in first-appearance order
```

The `> 12` case is an explicit bounded diagnostic projection only.

It must **not**:

```text
truncate or rewrite draft.text
remove citations from the Draft
truncate grounding evidence
truncate grounding conflicts
skip validation of citation IDs after the first 12
make the Draft publishable
suppress citation_limit_exceeded
```

Therefore:

```text
input validation = full
artifact diagnostic projection = bounded to 12
```

### 16.5 Required citation

If:

```text
metacognition.evidence_sufficiency == sufficient
```

and no valid citation is present:

```text
→ REVISE
→ issue: citation_required
```

If evidence is `not_required`, no citation is required.

### 16.6 Known conflict citations

For every supplied historical Conflict, all of its citation IDs must appear among validated Draft citations.

If any are absent:

```text
→ REVISE
→ issue: conflict_citation_missing
```

This proves citation presence only; it does not claim semantic disclosure quality.

### 16.7 Insufficient evidence

If no stronger `INVALID_COGNITION` or `REVISE` condition exists and D132 indicates valid insufficiency / unknown state:

```text
metacognition.evidence_sufficiency == insufficient
OR metacognition.confidence_class in {insufficient, unknown}
OR metacognition.recommended_cognitive_action == insufficient_information
```

result:

```text
INSUFFICIENT_EVIDENCE
→ issue: evidence_insufficient
```

### 16.8 Pass

If none of the above blocking or insufficiency conditions applies:

```text
PASS
```

`PASS` means only that D133 found no blocking condition under its frozen checks.

It does not mean universal factual truth has been proven.

## 16.9 Rev 0.2 Amendment Boundary

Rev 0.2 resolves the citation-overflow representation contradiction in Rev 0.1 without changing the result vocabulary, publication matrix, authority boundary, model boundary, or exact five-path implementation scope.

The contradiction was:

```text
validated_citation_ids max 12
+
more than 12 valid citations → REVISE
+
No truncation is permitted
```

The final enforcement split is:

```text
verification input
→ inspected in full
→ never silently truncated

CognitiveVerificationArtifact.validated_citation_ids
→ bounded diagnostic projection
→ at most first 12 distinct valid IDs in first-appearance order

citation overflow
→ always REVISE
→ always includes citation_limit_exceeded
→ never hidden by the projection cap
```

The reserved `critic_exhausted` issue code remains non-emitted in D133 V1; exhaustion is represented canonically by `CognitivePublicationGateArtifact.critic_exhausted`.

No new artifact field is added. No security or publication restriction is weakened. D136 boundaries remain unchanged.

## 17. Exact Deterministic Precedence

```text
1. CONTRACT_VIOLATION
   → exception / no artifact

2. INVALID_COGNITION

3. REVISE

4. INSUFFICIENT_EVIDENCE

5. PASS
```

Higher precedence may never be downgraded by lower precedence.

## 18. Advisory Critic Merge

D133 may consume an already-authorized bounded advisory result:

```text
pass
revise
insufficient_evidence
invalid_cognition
```

D133 itself performs no Critic model invocation.

Severity:

```text
invalid_cognition
    >
revise
    >
insufficient_evidence
    >
pass
```

Merge rule:

```text
final result = stricter(deterministic result, advisory result)
```

Therefore:

```text
deterministic INVALID_COGNITION
→ advisory cannot downgrade

deterministic REVISE
→ advisory PASS/INSUFFICIENT cannot downgrade

deterministic INSUFFICIENT_EVIDENCE
→ advisory PASS cannot downgrade

deterministic PASS
→ advisory may tighten to
   REVISE / INSUFFICIENT_EVIDENCE / INVALID_COGNITION
```

When advisory tightens the result, add exactly one matching issue:

```text
advisory_revise
advisory_insufficient_evidence
advisory_invalid_cognition
```

No hidden retry or model fallback occurs.

## 19. Publication Gate Artifact

```python
@dataclass(frozen=True, slots=True)
class CognitivePublicationGateArtifact:
    envelope: CognitiveArtifactEnvelope

    verification_result: VerificationResult
    disposition: PublicationDisposition
    draft_revision_count: int
    draft_digest: str
    critic_exhausted: bool
```

### 19.1 Publication Gate Envelope

```text
producer_organ = CognitiveOrgan.VERIFICATION_CRITIC
artifact_type = "cognitive.publication_gate"
contract_version = "o-ai.cognitive-publication-gate.v1"
context_snapshot_digest != None
model_binding_reference = None
```

No new Brain organ is introduced.

## 20. Exact Publication Matrix

| Verification result | revision_count | disposition | critic_exhausted | envelope status |
|---|---:|---|---|---|
| `pass` | 0 or 1 | `eligible` | False | READY |
| `insufficient_evidence` | 0 or 1 | `bounded_insufficiency_only` | False | INSUFFICIENT |
| `revise` | 0 | `revision_required` | False | READY |
| `revise` | 1 | `blocked` | True | FAILED |
| `invalid_cognition` | 0 or 1 | `blocked` | False | FAILED |

No other combination is valid.

## 21. Bounded Insufficiency Meaning

`bounded_insufficiency_only` does **not** authorize the current ordinary Draft text for publication.

It means:

```text
current ordinary answer is not publishable as a supported answer

downstream finalization may continue only through
a bounded insufficiency / "I do not know" response path
```

D133 does not synthesize that final bounded response.

## 22. Critic Exhaustion

Exact rule:

```text
Draft revision_count = 0
+ Verification REVISE
→ revision_required

Draft revision_count = 1
+ Verification REVISE
→ blocked
→ critic_exhausted = True
→ no second automatic revision
```

No unbounded Critic / Revision loop is permitted.

## 23. Working State Integration

Add:

```python
draft_response: CognitiveDraftResponseArtifact | None = None
verification: CognitiveVerificationArtifact | None = None
publication_gate: CognitivePublicationGateArtifact | None = None
```

Canonical order:

```text
context
reasoning
prediction
planning
decision_goal
metacognition
draft_response
verification
publication_gate
```

### 23.1 Draft attachment

Requires:

```text
context
metacognition
```

and all historical prerequisites already required by those upstream attachments.

It must share:

```text
turn_id
workspace_id
context_snapshot_digest
```

with Working State.

### 23.2 Verification attachment

Requires:

```text
draft_response
metacognition
context
```

It must share:

```text
turn_id
workspace_id
context_snapshot_digest
draft_revision_count
draft_digest
response_mode
```

with the attached Draft and upstream state.

Working State validates artifact-local consistency and same-turn binding. The service-level grounding checks are performed by `CognitiveVerificationCoordinator.verify()` and are not re-run through repositories or retrieval from Working State.

### 23.3 Publication Gate attachment

Requires:

```text
draft_response
verification
```

and must exactly match the deterministic Section 20 matrix for:

```text
verification_result
draft_revision_count
draft_digest
disposition
critic_exhausted
envelope status
```

## 24. Working State Freeze Semantics

For each D133 attachment:

```text
None → valid artifact
ALLOWED

same valid artifact → same artifact
ALLOWED / idempotent

existing artifact → different artifact
REJECT

existing artifact → None
REJECT
```

Once downstream D133 state exists, incompatible upstream replacement/removal must fail closed through existing Working State revalidation.

## 25. No Hidden Draft Rewrite

D133 must not silently mutate:

```text
draft.text
draft.response_mode
draft.revision_count
```

Citation sanitization is validation evidence only.

A required correction yields:

```text
REVISE
```

not a hidden text rewrite.

## 26. No Model / Provider Invocation

D133 must not invoke:

```text
AIRuntime
AIAdapter
Local AI
Cloud AI
provider client
model client
chat completion
generation
retry
fallback
routing
```

Actual invocation purposes:

```text
CRITIC
REVISION
POST_REVISION_CRITIC
```

remain D136 orchestration responsibilities.

## 27. Persistence Boundary

D133 artifacts are ephemeral in V1.

No new:

```text
DB table
ORM model
migration
repository
Message persistence
Memory mutation
Project mutation
Conversation mutation
audit persistence
```

is introduced.

Historical citation persistence remains unchanged.

## 28. Authority Boundary

D133 grants no:

```text
authentication
authorization
Owner approval
routing authority
provider selection
model selection
profile selection
tool permission
execution permission
calendar permission
Project mutation
Memory mutation
policy mutation
prompt mutation
code mutation
message persistence authority
```

`eligible` means eligible to continue downstream, not "send now".

## 29. D134 Boundary

Outside D133:

```text
ExperienceCandidate
experience validation
experience promotion
learning
Memory promotion
policy promotion
```

## 30. D136 Boundary

Outside D133:

```text
actual PRIMARY_SYNTHESIS orchestration
actual CRITIC invocation
actual REVISION invocation
actual POST_REVISION_CRITIC invocation
fresh authorization per invocation
provider/model/profile binding
remaining-budget checks
turn deadlines
stage budgets
circuit breakers
late-result enforcement
runtime retry policy
response finalization orchestration
```

## 31. Exact Implementation Scope

Exactly five paths:

```text
NEW backend/app/contracts/cognitive_verification.py
NEW backend/app/services/cognitive_verification.py
MODIFY backend/app/intelligence/context/cognitive.py
NEW backend/tests/test_d133_cognitive_verification.py
NEW backend/tests/test_d133_cognitive_verification_security.py
```

Any sixth implementation path:

```text
STOP
→ dependency / contradiction report
→ Owner amendment review
```

## 32. Explicitly Unmodified Production Areas

D133 may not modify:

```text
backend/app/contracts/cognitive_brain.py

backend/app/contracts/cognitive_reasoning_prediction.py
backend/app/services/cognitive_reasoning_prediction.py

backend/app/contracts/cognitive_planning_decision_goal.py
backend/app/services/cognitive_planning_decision_goal.py

backend/app/contracts/cognitive_metacognition.py
backend/app/services/cognitive_metacognition.py

backend/app/services/knowledge_intelligence.py
backend/app/services/knowledge_answer.py

backend/app/contracts/context_provenance.py
backend/app/services/context_snapshot.py
backend/app/services/context_sources.py
backend/app/services/context_provenance_sources.py

ReasoningService
PlanningService
DecisionService
GoalService

D104/D105 routing
D125 Local AI runtime profiles
ExecutionPlanner
ExecutionGuard
AIRuntime
AIAdapter
ConversationService

API
frontend
database
ORM
migrations
repositories
```

Historical tests may not be edited to make D133 pass.

## 33. Functional Test Contract

```text
backend/tests/test_d133_cognitive_verification.py
F01–F50
exactly 50 functional tests
```

Coverage includes:

```text
Draft contract
Draft digest determinism
Draft mode / D132 mapping
grounding integrity
CitationEngine reuse without mutation
citation ordering
citation limits
required citation behavior
conflict citation presence
insufficiency result
invalid cognition result
deterministic precedence
advisory severity merge
Publication Gate matrix
Critic exhaustion
Working State attachment / idempotence / freeze
historical component preservation
```

## 34. Security Test Contract

```text
backend/tests/test_d133_cognitive_verification_security.py
S01–S88
exactly 88 security tests
```

Coverage includes:

```text
malformed envelopes
wrong turn/workspace/digest
grounding invention
grounding source substitution
grounding content substitution
duplicate citation/evidence identities
unknown conflict citations
citation injection / unknown citation tokens
hidden draft mutation prevention
deterministic veto dominance
advisory downgrade attempts
revision-count overflow
Critic exhaustion bypass attempts
Publication Gate bypass attempts
provider/model/routing authority fields absent
no Context / Memory / Knowledge re-retrieval
no network/provider/model invocation
no persistence
no D134/D136 leakage
Working State freeze
historical production source preservation
```

## 35. Exact Targeted Historical Regression

Exact proposed set: **48 files**.

The first 43 are the D132 historical targeted set:

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
backend/tests/test_knowledge_intelligence.py
```

Add the two frozen D132 implementation tests:

```text
backend/tests/test_d132_cognitive_metacognition.py
backend/tests/test_d132_cognitive_metacognition_security.py
```

Add three D133-critical historical regressions:

```text
backend/tests/test_message_citations.py
backend/tests/test_knowledge_answer_ai_execution.py
backend/tests/test_knowledge_answer_request_correlation.py
```

Total:

```text
43 + 2 + 3 = 48 exact targeted historical files
```

Historical tests may not be edited to make D133 pass.

## 36. Validation Protocol

```text
1. branch / baseline / origin / remote verification
2. frozen spec SHA verification
3. exact implementation scope verification
4. D133 functional F01–F50
5. D133 security S01–S88
6. exact 48-file historical targeted regression
7. full backend regression
8. final exact implementation scope / hashes / spec verification
9. Owner Guided Acceptance
10. separate local implementation commit authorization
11. separate normal implementation push authorization
12. independent remote verification
```

## 37. Owner Guided Acceptance Intent

At least:

```text
A. D133 occurs after D132 and Draft production.
B. D133 does not re-read Context/Memory/Knowledge.
C. Grounding cannot escape the frozen ContextSnapshot.
D. Citation validation never silently rewrites the Draft.
E. Unknown citation IDs require REVISE.
F. Known conflict citation omissions require REVISE.
G. No-conflict result is not represented as proof of semantic truth.
H. D132 revise_reasoning cannot produce a publishable Draft.
I. Valid insufficiency remains insufficiency, not fabricated confidence.
J. Deterministic vetoes cannot be downgraded by advisory Critic.
K. PASS is not publication authority.
L. bounded_insufficiency_only is not ordinary-answer publication.
M. Automatic revision is bounded to one.
N. Critic exhaustion blocks further automatic revision.
O. D133 does not select or invoke provider/model/profile.
P. D133 does not persist cognition or leak into D134/D136.
Q. Working State freezes Draft/Verification/Publication Gate coherently.
R. Historical CitationEngine, ConflictDetector, D132, routing, and runtime behavior remain unchanged.
```

## 38. Design Freeze Scope

The original D133 Design Freeze commit and this Rev 0.2 Design Amendment commit each change exactly one path:

```text
docs/specs/D133_VERIFICATION_CRITIC_PUBLICATION_GATE_V1.md
```

Original Rev 0.1 freeze subject:

```text
docs: freeze D133 verification critic publication gate design
```

Rev 0.2 amendment subject:

```text
docs: amend D133 citation projection boundary
```

The amendment authorization does not authorize push.
Implementation remains paused until the amendment is independently remote verified.

## 39. Current Gate State

```text
D133 BASELINE:
265e02ca3c1882ea07bd1642943eea1909e1112d

D132 STATUS:
COMPLETE / CLOSED / PUSHED / INDEPENDENTLY REMOTE VERIFIED

D133 OWNER DESIGN RECONCILIATION A–N:
PASS

D133 EXACT CONTRACT PROPOSAL REV 0.1:
OWNER APPROVED

D133 FINAL CONTRACT REVIEW:
PASS

D133 DESIGN FREEZE REV 0.1:
PUSHED / INDEPENDENTLY REMOTE VERIFIED

D133 DESIGN AMENDMENT REV 0.2:
YES — OWNER AUTHORIZED

D133 DESIGN SPEC:
REV 0.2 AMENDED FROZEN BASELINE

D133 IMPLEMENTATION AUTHORIZATION:
RECEIVED

D133 IMPLEMENTATION:
PAUSED / NOT STARTED PENDING AMENDMENT REMOTE VERIFICATION

IMPLEMENTATION CODE CHANGE:
NONE

GIT COMMIT:
REV 0.2 DESIGN AMENDMENT COMMIT

GIT PUSH:
NOT AUTHORIZED / NOT PUSHED
```

**End of D133 Verification / Critic & Publication Gate V1 — Rev 0.2 Owner-Approved Amended Design Baseline**
