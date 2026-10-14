# D132 — Metacognition & Uncertainty V1

**Document status:** DESIGN AMENDED — OWNER APPROVED
**Design revision:** Rev 0.2 — OWNER-APPROVED AMENDMENT TO REV 0.1a
**Architecture:** O-AI Cognitive Brain Architecture V1
**Milestone:** D132 — Metacognition & Uncertainty V1
**Baseline commit:** `de9503bb770e34d76a19a7eede5c7b129954d072`
**Baseline state:** D131 COMPLETE / PUSHED / INDEPENDENTLY REMOTE VERIFIED
**Owner Design Reconciliation A–N:** PASS
**Owner Exact Contract Proposal Rev 0.1 approval:** YES
**Owner Design Amendment Rev 0.2 approval:** YES
**Design Freeze:** YES — OWNER AUTHORIZED
**Implementation:** NOT AUTHORIZED / NOT STARTED
**Code change:** NONE
**Commit:** DESIGN FREEZE COMMIT
**Push:** NOT PUSHED

---

## 1. Purpose

D132 introduces the Brain-facing **Metacognition & Uncertainty V1** organ.

D132 answers bounded questions about the quality and limits of the current cognitive state:

- What is known?
- What remains unknown?
- Is required information missing?
- Is evidence sufficient for the current cognitive intent?
- Are assumptions, hypotheses, or prediction uncertainties still present?
- Should O-AI respond, respond with uncertainty, recommend revision, ask the Owner, or report insufficient information?

D132 does **not** decide truth, grant authority, publish a response, invoke a model, revise reasoning, select a provider, execute an action, mutate durable state, or learn.

The governing boundary is:

```text
Metacognition ≠ Authority
Confidence    ≠ Truth
Uncertainty   ≠ Permission
ask_owner     ≠ Owner approval
revise_reasoning ≠ autonomous revision
respond       ≠ publication authorization
```

## 2. Architecture Position

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
D133 Verification / Critic & Publication Gate
```

D132 exists before D133 intentionally. Verification/Critic may later consume D132 metacognitive state, but D132 does not implement Critic or Publication Gate behavior.

## 3. Frozen Design Principles

1. D132 consumes only already-produced bounded cognitive artifacts.
2. D132 performs no Context, Memory, Knowledge, repository, provider, model, routing, network, persistence, API, frontend, or execution I/O.
3. D132 does not re-read raw Context.
4. D132 does not create new evidence.
5. D132 does not invent numeric confidence, probability, percentage, score, or rank.
6. Explicit insufficiency dominates apparent confidence.
7. Explicit unknowns cannot be promoted to sufficient confidence.
8. Assumptions, hypotheses, and prediction uncertainty may reduce confidence to limited.
9. Owner-decision requirements remain Owner authority.
10. `ask_owner` is recommendation metadata only.
11. `revise_reasoning` is recommendation metadata only.
12. A valid insufficient result is not a contract failure.
13. Malformed or incoherent upstream cognition fails closed as `CONTRACT_VIOLATION`.
14. D132 does not alter D104/D105/D125 model-routing/runtime authority.
15. D132 does not implement any D133 publication or Critic behavior.

## 4. Existing-System Reconciliation

### 4.1 D126 Cognitive Brain

`CognitiveOrgan.METACOGNITION` already exists. D132 does not modify `backend/app/contracts/cognitive_brain.py`.

### 4.2 D130 Reasoning

D132 consumes:

```text
CognitiveReasoningArtifact
├── intent
├── required_information
├── information_gaps
├── evidence[].evidence_id
└── statements[]
    ├── UNKNOWN
    ├── ASSUMPTION
    └── HYPOTHESIS
```

D132 does not alter D130 contracts or service behavior.

### 4.3 D130 Prediction

D132 consumes:

```text
CognitivePredictionArtifact
├── envelope.status
├── missing_support
└── scenarios[]
    ├── assumptions
    └── uncertainty_reasons
```

D132 does not alter Prediction.

### 4.4 D131 Planning / Decision / Goal

D132 consumes:

```text
CognitivePlanningArtifact
└── missing_information

CognitiveDecisionGoalArtifact
├── envelope.status
├── intent
├── supporting_evidence_ids
├── recommendation_status
└── missing_information
```

D132 does not modify D131 production contracts or projectors.

### 4.5 Historical ConfidenceEvaluator

Historical:

```text
ConfidenceEvaluator.evaluate(
    evidence,
    citations,
    conflicts,
)
→ high | medium | low | insufficient
```

This evaluator measures grounded answer evidence quality after answer/citation production. D132 occurs before answer synthesis and citation validation.

Therefore:

```text
D132 confidence_class
≠ historical EvidenceQuality
```

D132 must not fabricate post-answer citations or misuse `ConfidenceEvaluator` as a pre-answer classifier. Historical `ConfidenceEvaluator` remains unchanged and protected by regression tests.

## 5. Exact Contract Constants

```text
D132_METACOGNITION_ARTIFACT_TYPE = "cognitive.metacognition"
D132_METACOGNITION_CONTRACT_VERSION = "o-ai.cognitive-metacognition.v1"

D132_TEXT_MAX_BYTES = 2048
D132_UNKNOWN_MAX_COUNT = 160
D132_ASSUMPTION_MAX_COUNT = 320
D132_HYPOTHESIS_MAX_COUNT = 64
D132_UNCERTAINTY_REASON_MAX_COUNT = 256
D132_EVIDENCE_ID_MAX_COUNT = 256
```

No truncation is permitted.

## 6. Exact Vocabulary

### Knowledge Status

```text
known
partial
insufficient
unknown
```

### Evidence Sufficiency

```text
not_required
sufficient
insufficient
```

### Confidence Class

```text
sufficient
limited
insufficient
unknown
```

### Recommended Cognitive Action

```text
respond
respond_with_uncertainty
revise_reasoning
ask_owner
insufficient_information
```

All actions are non-authoritative cognitive recommendations only.

## 7. Exact Artifact

```python
@dataclass(frozen=True, slots=True)
class CognitiveMetacognitionArtifact:
    envelope: CognitiveArtifactEnvelope
    intent: CognitiveIntent

    knowledge_status: MetacognitiveKnowledgeStatus
    evidence_sufficiency: MetacognitiveEvidenceSufficiency
    confidence_class: MetacognitiveConfidenceClass
    recommended_cognitive_action: MetacognitiveRecommendedAction

    unknowns: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    uncertainty_reasons: tuple[str, ...] = ()

    considered_evidence_ids: tuple[str, ...] = ()
```

Forbidden field families include:

```text
confidence_score
probability
percentage
rank
winner
selected
selected_option
approval
owner_approval
execute
execution_authorization
provider
model
profile
raw_prompt
system_prompt
hidden_reasoning
chain_of_thought
cot
scratchpad
```

## 8. Envelope Contract

```text
producer_organ = CognitiveOrgan.METACOGNITION
artifact_type = "cognitive.metacognition"
contract_version = "o-ai.cognitive-metacognition.v1"
context_snapshot_digest != None
model_binding_reference = None
```

Allowed deterministic D132 statuses:

```text
READY
INSUFFICIENT
```

Disallowed:

```text
NOT_APPLICABLE
FAILED
```

## 9. Exact Projector Interface

```python
CognitiveMetacognitionProjector.project_metacognition(
    envelope,
    reasoning,
    prediction,
    planning,
    decision_goal,
) -> CognitiveMetacognitionArtifact
```

No raw Context object, repository/service fetch, provider, or model input is accepted.

## 10. Exact Upstream Coherence Requirements

All inputs must share:

```text
same turn_id
same workspace_id
same context_snapshot_digest
```

Intent:

```text
reasoning.intent
==
planning.intent
==
decision_goal.intent
```

Gap coherence:

```text
planning.missing_information
is an ordered subset of
reasoning.information_gaps

decision_goal.missing_information
==
planning.missing_information
```

Evidence coherence:

```text
decision_goal.supporting_evidence_ids
⊆
reasoning evidence IDs
```

Prediction must be a valid D130 Prediction artifact with status READY, NOT_APPLICABLE, or INSUFFICIENT.

Malformed or incoherent upstream state fails closed.

## 11. Exact Signal Projection

### Unknowns

Ordered deduplicated union:

```text
material Reasoning information_gaps
+
Reasoning UNKNOWN statement summaries
+
Prediction.missing_support
```

### Assumptions

Ordered deduplicated union:

```text
Reasoning ASSUMPTION statement summaries
+
Prediction scenarios[].assumptions
```

### Hypotheses

Ordered deduplicated Reasoning HYPOTHESIS statement summaries.

### Uncertainty Reasons

Ordered deduplicated Prediction scenarios[].uncertainty_reasons.

### Considered Evidence IDs

```python
tuple(item.evidence_id for item in reasoning.evidence)
```

IDs only; no raw evidence duplication.

## 12. Material Gap Rule

```text
no_retrieved_context
→ material only when required_information includes document_evidence

no_document_evidence
→ material only when required_information includes document_evidence

comparison_basis
→ material only when required_information includes comparison_basis

any other explicit information gap
→ material by default
```

Unknown future explicit gaps default to material.

## 13. Evidence Sufficiency Rule

```text
if "document_evidence" not in reasoning.required_information:
    evidence_sufficiency = "not_required"

elif at least one D130 reasoning evidence item has kind == "document"
     and "no_document_evidence" is not a material gap:
    evidence_sufficiency = "sufficient"

else:
    evidence_sufficiency = "insufficient"
```

No evidence-count-to-confidence conversion is allowed.

## 14. Exact Epistemic Precedence

```text
1. explicit insufficiency
2. explicit unknown
3. partial / uncertain
4. known / sufficient
```

Lower severity may never override higher severity.

## 15. Explicit Insufficiency

Active when any is true:

```text
material required-information gap exists
OR evidence_sufficiency == insufficient
OR prediction.envelope.status == INSUFFICIENT
OR prediction.missing_support non-empty
OR decision_goal.envelope.status == INSUFFICIENT
OR decision_goal.recommendation_status == "insufficient_information"
```

Result:

```text
knowledge_status = "insufficient"
confidence_class = "insufficient"
recommended_cognitive_action = "insufficient_information"
envelope.status = INSUFFICIENT
```

## 16. Explicit Unknown

If explicit insufficiency is inactive but structured Reasoning UNKNOWN statements remain:

```text
knowledge_status = "unknown"
confidence_class = "unknown"
recommended_cognitive_action = "insufficient_information"
envelope.status = INSUFFICIENT
```

## 17. Partial / Limited

If higher levels are inactive but assumptions, hypotheses, or uncertainty reasons remain:

```text
knowledge_status = "partial"
confidence_class = "limited"
envelope.status = READY
```

Action precedence:

```text
if hypotheses non-empty:
    revise_reasoning
elif decision_goal.recommendation_status == "owner_decision_required":
    ask_owner
else:
    respond_with_uncertainty
```

## 18. Known / Sufficient

If no material gaps, explicit unknowns, assumptions, hypotheses, or uncertainty reasons remain:

```text
knowledge_status = "known"
confidence_class = "sufficient"
envelope.status = READY
```

Action:

```text
if decision_goal.recommendation_status == "owner_decision_required":
    ask_owner
else:
    respond
```

## 19. Self-Consistency Matrix

| confidence_class | envelope status | allowed action |
|---|---|---|
| sufficient | READY | respond, ask_owner |
| limited | READY | respond_with_uncertainty, revise_reasoning, ask_owner |
| insufficient | INSUFFICIENT | insufficient_information |
| unknown | INSUFFICIENT | insufficient_information |

Reject incoherent combinations, including:

```text
sufficient + INSUFFICIENT
insufficient + READY
unknown + READY
insufficient + respond
unknown + ask_owner
limited + insufficient_information
revise_reasoning with no hypothesis
respond_with_uncertainty with no bounded uncertainty signal
ask_owner when Owner decision is not required
```

### 19.1 Rev 0.2 — `ask_owner` Enforcement-Location Amendment

Rev 0.2 resolves one enforcement-location contradiction without changing the
artifact field set, vocabulary, epistemic precedence, authority boundary, or
D133 boundary.

The final example above:

```text
ask_owner when Owner decision is not required
```

remains a mandatory D132 rejection rule, but it is **not independently
enforceable by `CognitiveMetacognitionArtifact` construction** because that
artifact intentionally carries no duplicate D131
`decision_goal.recommendation_status` field.

The exact enforcement split is:

```text
CognitiveMetacognitionArtifact constructor
→ enforces only self-consistency derivable from its own fields
→ enforces READY/INSUFFICIENT + confidence/action matrix
→ enforces revise_reasoning requires hypotheses
→ enforces respond_with_uncertainty requires a bounded uncertainty signal
→ does not infer or duplicate D131 owner-decision state

CognitiveMetacognitionProjector
→ possesses the D131 CognitiveDecisionGoalArtifact
→ may emit ask_owner only when:
   decision_goal.recommendation_status == "owner_decision_required"
   AND the Section 17 / Section 18 action precedence selects ask_owner

CognitiveWorkingState
→ possesses the attached D131 Decision/Goal artifact
→ revalidates the same ask_owner upstream trigger
→ rejects an attached metacognition artifact whose ask_owner action is not
   coherent with the attached D131 Decision/Goal artifact
```

Therefore the frozen exact upstream trigger for `ask_owner` is:

```text
decision_goal.recommendation_status
== "owner_decision_required"
```

This trigger is **necessary but not always sufficient** to emit `ask_owner`:
under Section 17, a non-empty hypothesis still gives `revise_reasoning`
precedence over `ask_owner`.

Any projector result or Working State attachment containing `ask_owner`
without the exact D131 owner-decision trigger fails closed as:

```text
CONTRACT_VIOLATION
```

No new artifact field is added. In particular, D132 must not add a duplicate:

```text
owner_decision_required
owner_decision_status
recommendation_status
```

to `CognitiveMetacognitionArtifact`.

All other Rev 0.1a rules remain unchanged.

## 20. Working State Integration

Add:

```python
metacognition: CognitiveMetacognitionArtifact | None = None
```

Order:

```text
context
reasoning
prediction
planning
decision_goal
metacognition
```

Attachment requires context, reasoning, prediction, planning, and decision_goal.

The artifact must match binding turn/workspace, Context digest, all upstream digests, intent, projected evidence IDs, and upstream-derived epistemic collections.

## 21. Working State Freeze Semantics

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

After metacognition is attached, upstream mutation/removal must revalidate downstream coherence and reject incoherent changes.

## 22. Failure Semantics

```python
class CognitiveMetacognitionContractError(Exception):
    code = "contract_violation"
    failure_code = CognitiveFailureCode.CONTRACT_VIOLATION
```

```text
malformed / incoherent cognition
→ CONTRACT_VIOLATION

valid lack of required knowledge/evidence
→ CognitiveMetacognitionArtifact
   envelope.status = INSUFFICIENT
```

## 23. No Model / Provider Boundary

D132 must never invoke or select:

```text
AIRuntime
AIAdapter
Local AI
Cloud AI
provider
model
profile
routing
retry
fallback
```

`model_binding_reference` must be `None`.

## 24. Persistence Boundary

D132 artifact is ephemeral in V1.

No DB table, ORM model, migration, repository, message persistence, Memory mutation, Project mutation, or audit-persistence change is introduced.

## 25. Authority Boundary

D132 grants no authentication, authorization, approval, routing, provider/model/profile selection, tool invocation, execution, calendar write, Project mutation, Goal activation, Conversation mutation, Memory mutation, policy mutation, prompt mutation, code modification, or publication authority.

## 26. D133 Boundary

Outside D132:

```text
Critic
draft citation verification
draft conflict verification
Publication Gate
PASS / REVISE Critic outcome
Critic model invocation
Revision invocation
Post-revision Critic
Critic exhaustion
final response publication
```

## 27. Exact Implementation Scope

Exactly five paths:

```text
NEW backend/app/contracts/cognitive_metacognition.py
NEW backend/app/services/cognitive_metacognition.py
MODIFY backend/app/intelligence/context/cognitive.py
NEW backend/tests/test_d132_cognitive_metacognition.py
NEW backend/tests/test_d132_cognitive_metacognition_security.py
```

Sixth path:

```text
STOP
→ dependency/conflict report
→ Owner amendment review
```

## 28. Explicitly Unmodified Production Areas

D132 may not modify:

```text
backend/app/contracts/cognitive_brain.py
backend/app/contracts/cognitive_reasoning_prediction.py
backend/app/services/cognitive_reasoning_prediction.py
backend/app/contracts/cognitive_planning_decision_goal.py
backend/app/services/cognitive_planning_decision_goal.py
backend/app/services/knowledge_intelligence.py
backend/app/services/knowledge_answer.py
ReasoningService
PlanningService
DecisionService
GoalService
D104/D105 routing
D125 local AI runtime profiles
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

Historical tests may not be modified.

## 29. Functional Test Contract

```text
backend/tests/test_d132_cognitive_metacognition.py
F01–F50
exactly 50 functional tests
```

Coverage includes contract construction, immutable normalization, all four epistemic levels, material-gap rules, evidence sufficiency, ordered projections, action precedence, deterministic equality, Working State integration, and preservation of historical behavior.

## 30. Security Test Contract

```text
backend/tests/test_d132_cognitive_metacognition_security.py
S01–S88
exactly 88 security tests
```

Coverage includes malformed envelopes/types, bounds, duplicate rejection, false precision, authority fields absent, turn/workspace/digest/intent mismatch, evidence invention, insufficiency/unknown upgrade attempts, no Context reread, no retrieval, no provider/model/network/persistence/routing imports, Working State freeze, D133 leakage prevention, and historical production source preservation.

## 31. Targeted Historical Regression

Exact proposed set: 43 files.

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

The set is the frozen D131 42-file historical regression plus:

```text
backend/tests/test_knowledge_intelligence.py
```

Historical tests may not be edited to make D132 pass.

## 32. Validation Protocol

```text
1. baseline / branch / origin / spec hash verification
2. D132 functional F01–F50
3. D132 security S01–S88
4. exact 43-file historical targeted regression
5. full backend regression
6. final exact implementation scope / file hashes / frozen spec verification
7. Owner Guided Acceptance
8. separate local implementation commit authorization
9. separate normal push authorization
10. independent remote verification
```

## 33. Owner Guided Acceptance Intent

At least:

```text
A. Metacognition occurs after D131 Decision/Goal.
B. D132 does not re-read Context/Memory/Knowledge.
C. Explicit insufficiency cannot be upgraded.
D. Explicit unknown cannot be upgraded.
E. Limited state preserves uncertainty.
F. No numeric false precision exists.
G. ask_owner preserves Owner authority.
H. revise_reasoning is recommendation only.
I. respond is not publication permission.
J. D132 does not select provider/model/profile.
K. D132 does not invoke AI.
L. D132 does not persist cognition.
M. Working State freezes metacognition coherently.
N. D133 Critic/Publication Gate remains outside D132.
O. Historical ConfidenceEvaluator and D130/D131 production behavior remain unchanged.
```

## 34. Design Freeze Scope

A future D132 Design Freeze commit, if separately authorized, must change exactly one path:

```text
docs/specs/D132_METACOGNITION_UNCERTAINTY_V1.md
```

Candidate commit subject:

```text
docs: freeze D132 metacognition uncertainty design
```

Design Freeze does not authorize implementation.

## 35. Current Gate State

```text
D131 BASELINE:
de9503bb770e34d76a19a7eede5c7b129954d072

D132 OWNER DESIGN RECONCILIATION A–N:
PASS

D132 EXACT CONTRACT PROPOSAL REV 0.1:
OWNER APPROVED

D132 SOURCE RECONCILIATION:
PASS

D132 DESIGN SPEC:
FROZEN DESIGN BASELINE

D132 DESIGN FREEZE:
YES — OWNER AUTHORIZED

D132 IMPLEMENTATION:
NOT AUTHORIZED / NOT STARTED

CODE CHANGE:
NONE

GIT COMMIT:
DESIGN FREEZE COMMIT

GIT PUSH:
NOT PUSHED
```

**End of D132 Metacognition & Uncertainty V1 — Rev 0.2 Owner-Approved Amended Design Baseline**
