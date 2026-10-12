# O-AI Cognitive Brain Architecture V1

**Document status:** DESIGN FROZEN - OWNER APPROVED<br>
**Design revision:** Rev 0.6 - FROZEN ARCHITECTURE BASELINE<br>
**Architecture phase:** Brain Formation<br>
**Baseline:** D125 COMPLETE / PUSHED / REMOTE FROZEN<br>
**Baseline commit:** `74b26ef725ef576e24062e6de5f096265ced3301`<br>
**Owner Architecture Review:** PASS<br>
**Owner approval:** YES<br>
**Implementation status:** NOT STARTED<br>
**D126 status:** NOT STARTED<br>
**Code changes:** NONE<br>
**Git commit:** DESIGN FREEZE COMMIT<br>
**Git push:** NOT PUSHED<br>

---

## 1. Purpose

O-AI Cognitive Brain Architecture V1 defines the architecture of the **cognitive brain** that will sit between the O-AI Sovereign Core and the intelligence engines that O-AI uses, including Local AI and Cloud AI.

The objective of Brain Formation is **not** to make O-AI maximally intelligent yet.

The objective is to make O-AI analogous to a **newborn child whose core brain organs exist and are correctly connected**, while learning, accumulated experience, maturation, and wider autonomous action remain constrained.

The governing development sequence is:

```text
D125
AI Runtime / Model Foundation
        ↓
BRAIN FORMATION
Complete the cognitive anatomy
        ↓
O-AI BRAIN V1 — BORN
        ↓
LEARNING & DEVELOPMENT
Experience + Benchmark + Improvement
        ↓
MATURATION
Better reasoning / context / judgment
        ↓
HANDS & LEGS
Tools / Browser / Workflow / Automation
```

The central architectural principle is:

> **Model is not the O-AI brain. A model is an intelligence engine used by the O-AI brain.**

---

## 2. Architectural Position

O-AI Cognitive Brain V1 does **not** replace the current Sovereign Core, Context architecture, Memory architecture, execution governance, AI routing, Local AI profiles, or existing intelligence services.

It evolves and reconciles what already exists.

```text
                     OWNER
                       │
                       ▼
            O-AI SOVEREIGN CORE
     Identity / Policy / Authority / Approval
                       │
              authority boundary
                       │
                       ▼
╔══════════════════════════════════════════════╗
║           O-AI COGNITIVE BRAIN V1           ║
║                                              ║
║ Self / Perception / Attention                ║
║ Task Understanding / Working State           ║
║ Context / Memory Retrieval                   ║
║ Reasoning / Prediction / Planning            ║
║ Decision / Metacognition / Verification      ║
║ Model Intelligence / Experience Boundary     ║
║ Communication / Cognitive Executive          ║
╚══════════════════════════════════════════════╝
                       │
              capability boundary
                       │
                       ▼
            INTELLIGENCE ENGINES
          Local AI / Cloud AI / Future
```

A second, equally important separation exists between cognition and execution:

```text
Cognitive thought
      │
      ▼
Recommendation / Plan / Draft
      │
      X  no implicit authority
      │
      ▼
Sovereign Policy / Approval / Guard
      │
      ▼
Execution
```

Therefore:

```text
Thought        ≠ Permission
Reasoning      ≠ Authorization
Prediction     ≠ Truth
Cognitive Plan ≠ Execution Plan
Decision       ≠ Owner Decision
Experience     ≠ Policy
Model Output   ≠ Fact
```

---

## 3. Core Architectural Invariants

O-AI Cognitive Brain V1 adopts the following governing invariants.

1. **Cognition may inform authority, but cognition is never authority.**
2. **External models provide capability, not sovereignty.**
3. **No cognitive artifact grants execution permission.**
4. **No model output can self-authorize routing, provider selection, execution, memory mutation, policy mutation, or code modification.**
5. **One Cognitive Turn operates in exactly one workspace.**
6. **One Cognitive Turn uses one frozen Context truth after ContextSnapshot capture.**
7. **Deterministic security and integrity checks cannot be overruled by an LLM.**
8. **Insufficient evidence is a valid cognitive result, not a system failure.**
9. **Brain Formation must be evolutionary, not destructive.**
10. **Existing authoritative components are reused before new parallel components are introduced.**
11. **Hidden chain-of-thought is not a persistence target.**
12. **ExperienceCandidate is not confirmed Memory and is not Policy.**
13. **No hidden model retry, provider fallback, or model fallback exists in Newborn Brain V1.**
14. **A single explicit bounded pre-freeze Context stabilization retry may be permitted only for a verified source-change conflict; it must rebuild the entire Context candidate set and must never refresh Context after freeze.**
15. **Every Cognitive Turn and expensive cognitive stage operates under server-owned time/resource budgets; no organ may extend the turn deadline.**
16. **Circuit breakers may fail fast around unreliable external/runtime dependencies, but may never silently switch provider, model, workspace, or authority path.**
17. **The Cognitive Executive is deterministic orchestration, not an autonomous LLM agent.**
18. **No two Cognitive Turns may silently interleave mutable conversation state or commit assistant results out of order for the same conversation.**
19. **Once a Cognitive Turn reaches a terminal state or its deadline expires, late provider/Critic results are stale and may not mutate Working State or durable response state.**
20. **Every cross-organ cognitive artifact must carry bounded provenance/version identity sufficient to prove which turn, ContextSnapshot, contract version, and producing organ created it.**
21. **Brain V1 task interpretation must not silently expand or alter the frozen D104/D125 routing/profile authority. Descriptive cognitive task semantics are non-authoritative unless a separately frozen milestone explicitly changes routing authority.**
22. **Hands and Legs remain outside Brain Formation.**

---

## 4. Brain Anatomy

O-AI Brain V1 is considered anatomically complete only when the following 17 cognitive organs exist as coherent contracts and are integrated into one bounded cognitive runtime.

| # | Brain Organ | Primary Responsibility | Current Foundation |
|---|---|---|---|
| 1 | Self / Identity Model | Know current workspace, conversation, project, and cognitive identity | `WorkspaceScope`, Conversation, Project |
| 2 | Perception | Convert bounded system inputs into cognitive percepts | Context Sources, RequestContext |
| 3 | Attention | Select what deserves cognitive focus | Context budgets, memory scoring, evidence ranking |
| 4 | Goal & Task Understanding | Understand what the Owner is asking and what kind of cognition is needed | Reasoning intent, Knowledge intent, D104 task kind |
| 5 | Working Memory | Hold bounded state for one turn | `ExecutionContext` prototype |
| 6 | Memory Retrieval | Retrieve relevant confirmed owner memory | `MemoryResolver`, `MemoryContextSource` |
| 7 | Context Intelligence | Build verified, workspace-safe cognitive context | D94–D97 Context architecture |
| 8 | Reasoning | Analyze evidence, unknowns, assumptions, alternatives, risks | `ReasoningService`, `ReasoningPlan` |
| 9 | Prediction / Simulation | Estimate outcomes and risks of alternatives | **Missing — new organ** |
| 10 | Cognitive Planning | Organize reasoning and problem-solving steps | `PlanningService`, `PlanningPlan` |
| 11 | Decision / Goal Support | Compare alternatives and expose decision structure | `DecisionService`, `GoalService` |
| 12 | Verification / Critic | Check cognition and draft responses before publication | Citation, conflict, schema, integrity validators |
| 13 | Metacognition | Know what O-AI knows, does not know, and how uncertain it is | Missing information + confidence foundations |
| 14 | Model Intelligence | Understand model capability and compatibility without owning routing authority | D34, D111, D125 |
| 15 | Experience System | Convert outcomes into bounded ExperienceCandidates | **Missing — new organ** |
| 16 | Communication / Response | Turn verified cognitive state into owner-facing output | `ChatService`, `ResponseComposer`, Conversation persistence |
| 17 | Cognitive Executive | Coordinate all cognitive organs in a bounded state machine | `Pipeline`, `DomainStep`, `KnowledgeOrchestrator` |

The architectural rule is:

> **If an existing component already represents an organ foundation, Brain V1 must reconcile, extend, or generalize it before introducing a duplicate system.**

### 4.1 Cross-Cutting Brain Substrates

The 17 organs are the cognitive anatomy. The following concerns are **cross-cutting substrates**, not additional organs:

```text
Cognitive Artifact Provenance / Versioning
Turn Identity / Correlation
Time & Resource Budget
Failure Normalization
Audit / Telemetry
Workspace Isolation
Authorized Model Invocation
```

Every structured artifact that crosses an organ boundary should be representable by a bounded envelope conceptually containing:

```text
CognitiveArtifactEnvelope
├── turn_id
├── artifact_type
├── contract_version
├── producer_organ
├── workspace_id
├── context_snapshot_digest
├── created_at
├── status
├── input_reference_digests
└── model_binding_reference?   # only when model-produced
```

This envelope is provenance metadata, not hidden reasoning content.

The architecture may persist a minimal **Cognitive Turn Manifest** containing safe metadata and digests needed for audit, benchmark, diagnosis, and future Experience eligibility without persisting raw chain-of-thought or unnecessary Context content.

---

## 5. Canonical Cognitive Flow

```text
OWNER INPUT
    │
    ▼
0. INPUT / AUTHORITY GATE
    │
    ├─ Validate request
    ├─ Bind workspace
    ├─ Separate cognitive lane from action lane
    │
    ▼
1. PERCEPTION
    │
    ├─ Conversation
    ├─ Project
    ├─ Memory
    ├─ Knowledge
    └─ Request
    │
    ▼
2. ATTENTION / CONTEXT
    │
    ├─ Retrieve
    ├─ Rank
    ├─ Budget
    ├─ Deduplicate
    └─ Preserve provenance
    │
    ▼
3. VERIFIED CONTEXT SNAPSHOT
    │
    ▼
4. WORKING STATE
    │
    ▼
5. TASK UNDERSTANDING
    │
    ├─ Interaction Intent
    ├─ Cognitive Intent
    └─ Task Domain
    │
    ▼
6. REASONING
    │
    ▼
7. PREDICTION / SIMULATION
    │
    ▼
8. COGNITIVE PLANNING
    │
    ▼
9. DECISION / GOAL
    │
    ▼
10. METACOGNITION
    │
    ▼
11. AUTHORIZED INTELLIGENCE ENGINE INVOCATION
    │
    ├─ Local AI
    └─ Cloud AI
    │
    ▼
12. DRAFT RESPONSE / DRAFT COGNITION
    │
    ▼
13. VERIFICATION / CRITIC
    │
    ├─ PASS
    ├─ REVISE
    ├─ INSUFFICIENT_EVIDENCE
    └─ INVALID_COGNITION
    │
    ▼
14. PUBLICATION GATE
    │
    ▼
15. FINAL RESPONSE
    │
    ▼
16. DURABLE RESPONSE / PROVENANCE PERSISTENCE
    │
    ▼
17. TURN COMPLETE
    │
    ▼
18. EXPERIENCE ELIGIBILITY
```

Experience processing is explicitly outside the critical response path.

```text
Turn Complete
    ↓
Experience Eligibility
    ↓
ExperienceCandidate
    ↓
Validation / Promotion Boundary
    X
No automatic Memory / Policy / Prompt / Routing / Code mutation
```

---

## 6. Canonical Task Semantics

Existing O-AI uses multiple concepts that resemble “intent” or “task.” Brain V1 must preserve them but assign each one a distinct meaning.

```text
A. Interaction Intent
"What kind of interaction is this?"
Examples:
- chat
- action request
- approval-related input
- runtime-status request

B. Cognitive Intent
"How should O-AI think about this?"
Examples:
- factual lookup
- explanation
- comparison
- procedure
- troubleshooting
- summary

C. Task Domain
"What capability domain is this?"
Current D104 examples:
- GENERAL_CHAT
- SOFTWARE_ENGINEERING
```

Required relation:

```text
Owner Goal
   ↓
Interaction Intent
   ↓
Cognitive Intent
   ↓
Task Domain
   ↓
Server-owned Model / Runtime Policy
```

> **Cognitive Intent does not select a provider or model directly.**

---

## 7. Organ Contracts

### 7.1 Self / Identity Model

**Input:** WorkspaceScope, Conversation identity, optional Project identity.<br>
**Output:** Cognitive Self projection.<br>
**May read:** workspace identity, conversation identity, project association.<br>
**May write:** ephemeral identity state only.<br>
**Persistence:** no new persistence.<br>
**Authority:** none.<br>
**LLM:** no.<br>
**Existing ownership:** `WorkspaceScope`, Conversation, Project.

The Cognitive Self answers which workspace, conversation, and project the current cognition belongs to. It does not answer what O-AI is authorized to execute.

### 7.2 Perception

**Input:** current request plus Conversation, Project, Memory, and Knowledge sources.<br>
**Output:** bounded source candidates/percepts.<br>
**May read:** read-only source projections.<br>
**May write:** ephemeral perception state.<br>
**Persistence:** no.<br>
**Authority:** none.<br>
**LLM:** no.<br>
**Existing ownership:** `ConversationContextSource`, `ProjectContextSource`, `MemoryContextSource`, `KnowledgeContextSource`, `RequestContext`.

Perception is observation, not authorization.

### 7.3 Attention

**Input:** task metadata, perception candidates, relevance information, budgets.<br>
**Output:** selected cognitive focus / attention policy.<br>
**May read:** relevance scores, source identity, task metadata, budget policy.<br>
**May write:** ephemeral attention selection metadata.<br>
**Persistence:** no.<br>
**Authority:** none.<br>
**LLM:** no in Newborn Brain V1.<br>
**Existing ownership:** ContextResolver, memory scoring, EvidenceRanker, context layer budgets, ContextBuilder.

Brain V1 unifies these behaviors rather than creating an unrelated ranking system.

### 7.4 Goal & Task Understanding

**Input:** Owner input, interaction context, selected cognitive context.<br>
**Output:** Interaction Intent, Cognitive Intent, Task Domain, desired output, constraints, information gaps.<br>
**Persistence:** no.<br>
**Authority:** none.<br>
**LLM:** model assistance may be considered later, but model output cannot become routing authority.<br>
**Existing ownership:** `CommandDecisionEngine`, `ReasoningService`, `IntentAnalyzer`, `AITaskKind`.

These systems must be reconciled rather than replaced with another overlapping taxonomy.

### 7.5 Working Memory / Cognitive Working State

The existing `ExecutionContext` is the primary prototype.

Current structure:

```text
ExecutionContext
├── RequestContext
├── ConversationContext
├── KnowledgeContext
├── IntelligenceContext
├── ResponseContext
└── RuntimeContext
```

Brain V1 direction:

```text
Cognitive Working State
├── identity
├── request
├── perception
├── attention
├── task
├── conversation
├── knowledge
├── intelligence
│   ├── reasoning
│   ├── prediction
│   ├── planning
│   ├── decision
│   ├── goals
│   ├── metacognition
│   └── verification
├── model
├── response
└── runtime
```

**Persistence:** no by default.<br>
**Authority:** none.<br>
**LLM:** no.

Working Memory is the bounded scratch state of one cognitive turn.

### 7.6 Memory Retrieval

**Input:** current query/task and workspace.<br>
**Output:** relevant confirmed Memory references and bounded projections.<br>
**May read:** confirmed active Memory only.<br>
**May write:** selected memory references into Working State.<br>
**Persistence:** retrieval output is ephemeral.<br>
**Authority:** none.<br>
**LLM:** no.<br>
**Existing ownership:** `MemoryResolver`, `MemoryRepository`, `MemoryContextSource`.

```text
Retrieval ≠ Memory mutation
Retrieval ≠ Learning
Retrieval ≠ Confirmation
```

### 7.7 Context Intelligence

D94–D97 becomes the canonical cognitive context substrate.

**Input:** `ContextResolveRequest`, context sources, ContextBudgetPolicy.<br>
**Output:** `ContextBundle` followed by verified `ContextSnapshot`.<br>
**Persistence:** ContextSnapshot may persist through the existing repository.<br>
**Authority:** none.<br>
**LLM:** no.<br>
**Existing ownership:** `ContextSourceRef`, `ContextItem`, `ContextBundle`, `ContextResolver`, `ContextSnapshotService`, Context provenance contracts, `ContextSnapshotRepository`.

The snapshot verifies the bounded source truth shown to cognition. It does not declare every source statement to be true in the world.

### 7.8 Reasoning

**Input:** task, verified Context, evidence, known information, unknowns.<br>
**Output:** safe structured ReasoningArtifact.<br>
**May write:** `intelligence.reasoning`.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory.<br>
**Existing ownership:** `ReasoningService`, `ReasoningPlan`, `ReasoningStep`.

Conceptual artifact:

```text
facts
evidence
unknowns
assumptions
hypotheses
constraints
alternatives
risks
inferences
```

```text
ReasoningArtifact ≠ hidden chain-of-thought
```

### 7.9 Prediction / Simulation

This is a new cognitive organ.

**Input:** reasoning, alternatives, constraints, evidence, assumptions.<br>
**Output:** PredictionArtifact.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory.

Conceptual fields:

```text
alternative
expected_effect
risk
dependency
assumption
uncertainty
```

```text
Prediction ≠ Fact
Prediction ≠ Decision
```

### 7.10 Cognitive Planning

**Input:** goal, reasoning, prediction, constraints.<br>
**Output:** Cognitive Plan.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory.<br>
**Existing ownership:** `PlanningService`, `PlanningPlan`, `PlanningStep`.

```text
CognitivePlan ≠ ExecutionPlan
```

`ExecutionPlanner` remains outside Cognitive Planning.

### 7.11 Decision / Goal Support

**Input:** alternatives, evidence, reasoning, prediction, planning, owner-visible constraints.<br>
**Output:** DecisionAnalysis, GoalAnalysis, trade-offs, recommendation status, missing information.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory.<br>
**Existing ownership:** `DecisionService`, `DecisionAnalysis`, `GoalService`, `GoalAnalysis`.

This organ may recommend and compare. It cannot approve, commit, execute, or mutate Project state.

### 7.12 Verification / Critic

This is a new coordinating organ built over existing validators.

**Input:** draft cognition/response, ContextSnapshot, evidence, citations, metacognitive state.<br>
**Output:** `PASS`, `REVISE`, `INSUFFICIENT_EVIDENCE`, or `INVALID_COGNITION`.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory; deterministic vetoes dominate.<br>
**Existing foundations:** CitationEngine, ConflictDetector, ContextSnapshot integrity, PlanningPlan validation, execution plan integrity checks, Local AI profile/model binding validation.

Verification order:

```text
Deterministic invariants
        ↓
Evidence / Provenance validation
        ↓
Structured schema validation
        ↓
LLM Critic
```

### 7.13 Metacognition

**Input:** reasoning state, evidence sufficiency, verification state, known unknowns.<br>
**Output:** MetacognitiveState.<br>
**Persistence:** no in V1.<br>
**Authority:** none.<br>
**LLM:** yes — advisory.<br>
**Existing foundations:** missing-information behavior and `ConfidenceEvaluator`.

Conceptual state:

```text
knowledge_status
unknowns
assumptions
evidence_sufficiency
confidence_class
recommended_cognitive_action
```

Permitted cognitive actions include:

```text
respond
respond_with_uncertainty
revise_reasoning
ask_owner
insufficient_information
```

Not execution actions.

Initial confidence classes:

```text
sufficient
limited
insufficient
unknown
```

### 7.14 Model Intelligence

**Input:** Task Domain, model discovery, profile metadata, capability/evaluation evidence.<br>
**Output:** read-only ModelCapabilityKnowledge.<br>
**Persistence:** no new DB initially.<br>
**Authority:** none.<br>
**LLM:** no for routing authority.<br>
**Existing ownership:** D34 discovery, D111 routing, D125 profile contracts and resolver.

Conceptual fields:

```text
task strengths
known limitations
context capacity
reasoning support
structured-output support
latency observations
privacy/locality
evaluation evidence
```

```text
Model Intelligence ≠ Model Authority
```

Actual model access remains:

```text
Task Domain
   ↓
Workspace Policy
   ↓
D111 Routing
   ↓
D125 Profile
   ↓
ExecutionPlanner
   ↓
ExecutionGuard
   ↓
AIRuntime
```

### 7.15 Experience System

This is a new organ whose anatomy exists before autonomous learning authority.

**Input:** situation, goal, Context references, approach, outcome, verification result, model/runtime evidence.<br>
**Output:** ExperienceCandidate.<br>
**Persistence:** candidate persistence may be introduced later under a separately frozen contract.<br>
**Authority:** none.<br>
**LLM:** may assist lesson summarization only.

Conceptual structure:

```text
situation
goal
relevant_context
approach
outcome
evaluation
lesson_candidate
provenance
confidence
```

Promotion path:

```text
ExperienceCandidate
      ↓
Experience Validation
      ↓
Promotion Policy / Owner
      ↓
Promoted Experience
```

Forbidden automatic transitions:

```text
ExperienceCandidate → Memory
ExperienceCandidate → Policy
ExperienceCandidate → Prompt rewrite
ExperienceCandidate → Model routing
ExperienceCandidate → Code modification
```

### 7.16 Communication / Response

**Input:** verified Cognitive State, metacognitive uncertainty, evidence/citations.<br>
**Output:** Candidate Response and Final Response.<br>
**Persistence:** final assistant Message and required provenance may persist.<br>
**Authority:** none.<br>
**LLM:** yes — response synthesis.<br>
**Existing ownership:** `ChatService`, Context builders, `ResponseComposer`, `ConversationService`, `ConversationRepository`.

Future canonical path:

```text
Verified Cognitive State
        ↓
Response Synthesis
        ↓
Candidate Response
        ↓
Critic
        ↓
Publication Gate
        ↓
Final Response
```

### 7.17 Cognitive Executive

The Cognitive Executive is deterministic orchestration, not an LLM agent.

**Input:** Cognitive Working State, organ status, server-owned lifecycle policy.<br>
**Output:** ordered stage transitions and terminal state.<br>
**Persistence:** no.<br>
**Authority:** none.<br>
**LLM:** no.<br>
**Existing ownership:** `Pipeline`, `DomainStep`, `KnowledgeOrchestrator`.

Brain V1 direction:

```text
Perceive
→ Attend
→ Build Working State
→ Understand Task
→ Reason
→ Predict
→ Plan
→ Decide
→ Metacognize
→ Invoke authorized model
→ Verify
→ bounded revision if allowed
→ Publish
```

---

## 8. LLM Access Boundary

No cognitive organ may hold a raw provider client.

Forbidden architecture:

```text
ReasoningService → OpenAI directly
CriticService    → Ollama directly
Prediction       → provider.generate()
```

Required architecture:

```text
Cognitive Organ
       ↓
Cognitive Engine Request
       ↓
Cognitive Executive / Invocation Coordinator
       ↓
Authorized AI Boundary
       ↓
AIRuntime
       ↓
AIAdapter
       ↓
Local AI / Cloud AI
```

### 8.1 Invocation Ownership

An organ marked `LLM: YES — advisory` does **not** mean the organ may directly call a provider.

It means the organ may request bounded engine assistance through the Executive-owned invocation boundary.

Every model invocation must have a server-owned purpose, for example:

```text
PRIMARY_SYNTHESIS
CRITIC
REVISION
POST_REVISION_CRITIC
```

Each invocation requires its own valid authorization/binding and its own remaining-budget check.

### 8.2 Newborn Brain V1 Invocation Topology

The logical cognitive stages are not separate model calls.

For Brain V1, pre-model organs such as Reasoning, Prediction, Planning, Decision, and Metacognition should primarily operate on deterministic or structured state and may contribute instructions/artifacts to the primary synthesis request.

The bounded model-call topology is:

```text
PRIMARY_SYNTHESIS          max 1
CRITIC                     max 1 when policy requires
REVISION                   max 1
POST_REVISION_CRITIC       max 1 when policy requires
```

Thus:

```text
maximum draft generations = 2
maximum bounded model invocations = 4
```

This is an architectural maximum, not a requirement to make four calls.

Task policy may require fewer calls.

No organ may invent a new invocation purpose dynamically.

This preserves D125 and existing execution-security boundaries while removing ambiguity between logical cognitive stages and provider calls.


---

## 9. Persistence Boundary

Brain V1 separates three state classes.

### 9.1 Ephemeral Cognition

```text
Attention
Working State
Reasoning
Prediction
Planning
Decision
Metacognition
Critic report
```

Default: **no durable persistence**.

### 9.2 Durable Evidence / Domain State

Existing authoritative persistence remains the owner of:

```text
Conversation
Messages
ContextSnapshot
Memory
Knowledge
Projects
Audit
Citations
```

### 9.3 Controlled Learning State

Future controlled learning may introduce:

```text
ExperienceCandidate
Promoted Experience
```

under separately frozen contracts.

Brain V1 does not persist raw hidden model reasoning.

### 9.4 Cognitive Turn Manifest

A minimal durable Cognitive Turn Manifest is permitted and recommended for Brain V1.

It may contain only bounded metadata such as:

```text
turn_id
workspace_id
conversation_id
project_id?
terminal_status
context_snapshot_digest
task_semantics_version
authoritative_ai_task_kind
authorized_adapter_id
authorized_model_id
authorized_profile_id?
verification_status
revision_count
deadline / duration metadata
artifact contract versions / digests
safe normalized failure codes
```

It must not become a second Conversation store and must not contain raw hidden chain-of-thought.

The manifest exists to make the cognitive lifecycle auditable and reproducible even when most cognition remains ephemeral.

---

## 10. Existing-System Reconciliation

### 10.1 Existing Components That Must Be Preserved

```text
Workspace / workspace isolation
Conversation / Message persistence
Project / Project revisions
Personal Memory lifecycle
Knowledge ingestion / retrieval
D94–D97 Context architecture
Context provenance / snapshots
ReasoningService
PlanningService
DecisionService
GoalService
ExecutionContext prototype
Intelligence Pipeline
KnowledgeOrchestrator
AI discovery
AI routing
Workspace AI policy
D125 Local AI profiles
ExecutionPlanner
ExecutionGuard
AIRuntime
AIAdapter
ChatService
ResponseComposer
Execution audit
```

These are not discarded.

### 10.2 Working Memory Reconciliation

`ExecutionContext` is the current strongest foundation for Brain Working Memory and must be evolved rather than duplicated.

Normal Context Chat currently carries cognitive state through local variables and `ChatTurnResult`, while Grounded Knowledge already uses `ExecutionContext`.

Brain V1 must converge these paths toward one shared cognitive-state model.

### 10.3 Executive Reconciliation

Grounded Knowledge currently resembles:

```text
KnowledgeOrchestrator
    ↓
Pipeline
    ↓
RetrievalStep
EvidenceStep
ReasoningStep
PlanningStep
DecisionStep
GoalStep
```

Normal Chat resembles:

```text
ConversationService
    ↓
ReasoningService
PlanningService
DecisionService
GoalService
```

Brain V1 should generalize the existing intelligence pipeline instead of creating an unrelated third orchestration layer.

### 10.4 Pipeline Reconciliation

The repository currently contains both:

```text
backend/app/intelligence/pipeline/*
```

and:

```text
backend/app/pipeline/*
```

These abstractions must be reconciled before a new Cognitive Pipeline architecture is introduced.

### 10.5 Duplicate Knowledge Cognition Reconciliation

Grounded Knowledge currently contains a pipeline path that creates Reasoning / Planning / Decision / Goal artifacts and a compatibility path capable of rebuilding intelligence analysis later in the same service.

The target is:

```text
one Cognitive Working State
+
one ordered cognitive pipeline
+
one source of each cognitive artifact per turn
```

This is an architectural reconciliation target, not authorization to patch implementation before the relevant milestone is designed.

### 10.6 Planning Reconciliation

Three planning concepts remain distinct:

```text
Cognitive Planning
PlanningService / PlanningPlan
```

```text
Execution Planning
ExecutionPlanner / ExecutionPlan
```

```text
Project Action Planning
ProjectActionPlanningService / ProjectActionPlan
```

Invariant:

```text
Cognitive Plan
        ≠
Execution Plan
        ≠
Project Action Approval
```

---

## 11. Cognitive Turn Lifecycle

A Cognitive Turn begins only after request validation and assignment to the Cognitive Lane.

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
REVISING?  (bounded)
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

`INSUFFICIENT` is not equivalent to `FAILED`.

### 11.1 Cognitive Time Budget and Latency Resilience

The 18 logical stages are **architectural states, not 18 mandatory model calls**. An organ may be deterministic, may return `NOT_APPLICABLE`, or may be skipped only when the server-owned task policy explicitly marks it as unnecessary.

Every Cognitive Turn owns one monotonic server-controlled deadline:

```text
TurnDeadline
    ↓
remaining budget
    ↓
each cognitive stage
```

Rules:

```text
No organ may extend TurnDeadline.
Model timeout ≤ remaining TurnDeadline.
Critic / revision may run only when sufficient budget remains.
Budget exhaustion → bounded timeout outcome, never an unbounded wait.
```

Per-organ budgets are required for expensive or potentially blocking work such as Context retrieval, model inference, Critic inference, and future external cognitive dependencies. Pure deterministic local organs should remain fail-fast and bounded rather than receiving unnecessary autonomous retry behavior.

### 11.2 Circuit Breaker Boundary

Circuit breakers are permitted around unreliable runtime or external dependencies, for example:

```text
AI provider/runtime
future external retrieval service
future remote cognitive dependency
```

A circuit breaker may:

```text
observe bounded failures
open after server-owned thresholds
reject early while open
probe recovery under bounded policy
```

A circuit breaker may **not**:

```text
switch provider automatically
switch model automatically
change workspace
change task domain
grant execution authority
change policy
```

Circuit breaker state is operational resilience metadata, not cognition and not learning.

Exact timeout values, thresholds, and breaker persistence are milestone-level implementation decisions and are not frozen by this architecture draft.

### 11.3 Same-Conversation Turn Concurrency

Brain V1 must prevent silent concurrent mutation of one Conversation's cognitive order.

The Newborn behavior is:

```text
one active Cognitive Turn per conversation
```

If another turn for the same conversation arrives while one is active:

```text
TURN_IN_PROGRESS
```

or an equivalent safe conflict outcome is returned.

Brain V1 does not create an autonomous background queue for conflicting turns.

Different conversations may execute independently subject to global resource policy.

The implementation mechanism may use a server-owned lease, revision token, transactional guard, or equivalent, but the invariant is architectural:

> **Assistant turns for one conversation may not be committed out of cognitive order.**

### 11.4 Terminality and Late Results

A Cognitive Turn becomes immutable with respect to provider output when it reaches:

```text
COMPLETED
FAILED
INSUFFICIENT
deadline_expired
```

Any model, Critic, or future asynchronous result that arrives after terminality is **stale**.

Stale results:

```text
may be audited as late
may not update Working State
may not publish a response
may not write an assistant Message
may not create an authoritative Experience outcome
```

Cancellation should be attempted where the runtime supports it, but correctness must not depend on cancellation succeeding.

---

## 12. Context Freeze Semantics

Before freeze:

```text
ContextResolver
    ↓
ContextBundle
    ↓
ContextSnapshotService
    ↓
re-observe authoritative source
```

The existing verify-before-freeze behavior remains the security foundation.

### 12.1 Source Change Before Freeze

If source content changes before freeze, O-AI must never merge old and new Context fragments into one mixed snapshot.

The first verified source-change conflict may enter one **explicit bounded stabilization attempt**:

```text
Attempt #1
Context source changed
      ↓
discard entire unresolved candidate set
      ↓
re-resolve the complete Context request
      ↓
re-observe authoritative sources
      ↓
attempt a new ContextSnapshot
```

Maximum automatic stabilization retries:

```text
1
```

This is not a hidden general retry loop. It is permitted only for a recognized pre-freeze source-change conflict and must preserve:

```text
same request
same workspace
same conversation binding
same project binding
same task input
same Context policy
```

Partial merge, selective patching, or carrying stale candidates across attempts is forbidden.

Where a source supports version/revision tokens, digests, or equivalent optimistic-concurrency metadata, Context acquisition should use them as an additional early conflict signal. The authoritative D96-style re-observation remains the final verification boundary.

If the second acquisition still cannot produce a stable snapshot:

```text
CONTEXT_UNSTABLE
    ↓
bounded user-facing response
```

The system must not hang and must not continue cognition on an unverified Context mixture.

### 12.2 After Freeze

After `ContextSnapshot` is successfully captured:

> **The Cognitive Turn uses that immutable Context truth for the remainder of the turn.**

If the database changes after freeze, the current turn does not silently refresh.

```text
One Cognitive Turn
    ↓
One frozen ContextSnapshot
```

Automatic post-freeze Context refresh in Brain V1:

```text
0
```

If more information is required after freeze:

```text
INSUFFICIENT_INFORMATION
```

or:

```text
ASK_OWNER
```

A new turn may see newer Context. The current turn may not.


---

## 13. Organ Failure Semantics

Each cognitive organ should distinguish:

```text
READY
NOT_APPLICABLE
INSUFFICIENT
FAILED
```

| Situation | Expected Result |
|---|---|
| Prediction not relevant to simple factual lookup | `NOT_APPLICABLE` |
| No relevant Memory | Continue |
| Grounded Knowledge requires evidence but has none | `INSUFFICIENT` |
| Context source unavailable | `FAILED` |
| Context changed before snapshot freeze, first occurrence | One bounded full Context stabilization attempt |
| Context remains unstable after bounded stabilization | `FAILED` with `CONTEXT_UNSTABLE`-class safe outcome |
| Cognitive turn deadline exhausted | `FAILED` with bounded timeout outcome |
| Circuit breaker open for required dependency | Fail fast as unavailable; no silent fallback |
| Reasoning artifact violates contract | `FAILED` |
| Model unavailable | `FAILED` |
| Model returns malformed or empty result | `FAILED` |
| Critic cannot verify required evidence | No normal publication |
| Critic remains `REVISE` after Revision #1 | Degraded/limited publication path or safe stop according to verification severity |
| Experience generation fails after turn completion | User turn remains successful |

---

## 14. Model Failure Policy

Newborn Brain V1 preserves fail-closed provider behavior.

```text
Automatic model retry:       0
Automatic provider fallback: 0
Automatic model fallback:    0
```

Existing foundations already support this direction:

```text
OpenAI max_retries = 0
D111 fallback_allowed = False
D125 exact Local AI profile/model binding
Local AI no cloud fallback
```

If Local AI fails, O-AI does not silently switch to Cloud AI.

If Cloud AI fails, O-AI does not silently switch to Local AI.

Failures remain observable, measurable, and reproducible.

Model invocation must also respect the Cognitive Turn deadline:

```text
effective_model_timeout
=
min(
    authorized profile/provider timeout,
    remaining Cognitive Turn budget
)
```

Timeout or breaker behavior may fail fast, but it may not create a hidden model/provider fallback path.

---

## 15. Critic Feedback Loop

Brain V1 permits at most one automatic revision.

```text
Initial Draft
     ↓
Critic
 ┌───┴──────────────┐
 │                  │
PASS              REVISE
 │                  │
 │                  ▼
 │              Revision #1
 │                  │
 │                  ▼
 │                Critic
 │          ┌───────┼──────────────┐
 │          │       │              │
 │        PASS    REVISE       INVALID /
 │          │       │          INSUFFICIENT
 │          │       │              │
 └──────────┴───────┴──────────────┘
                    ↓
            Publication policy
```

Maximum model draft generations:

```text
2
```

One initial generation plus one bounded revision.

Critic calls are counted separately from draft generations and remain subject to the invocation maximum defined in Section 8.

`AIRuntime` currently issues a one-shot authorized adapter. Therefore a second model generation must require a fresh bounded authorization/binding. Authorization may not be replayed.

Revision must preserve:

```text
same workspace
same conversation
same project
same ContextSnapshot
same task domain
same provider policy
same authorized model/profile policy
```

Critic cannot change authority-bearing state.

### 15.1 Critic Exhaustion Policy

A second `REVISE` result must never create a third autonomous model loop.

The Publication Gate classifies the unresolved condition by severity:

```text
A. Deterministic / integrity veto
   → no substantive publication
   → safe terminal failure response

B. INVALID_COGNITION
   → no substantive publication
   → safe terminal failure response

C. INSUFFICIENT_EVIDENCE
   → bounded uncertainty / ask Owner / insufficient-information response

D. Residual advisory quality issue only
   → LIMITED publication may be permitted
     only when deterministic, provenance, schema,
     and evidence requirements already pass
```

`LIMITED` publication means the system explicitly discloses that full verification was not achieved and must not assert the unresolved conclusion as established fact.

There is no silent acceptance of a failed Critic and no indefinite waiting.

### 15.2 Critic Unavailability

If an LLM Critic is required by the server-owned verification policy but cannot run because of timeout, provider failure, or an open circuit breaker:

```text
CRITIC_UNAVAILABLE
```

The system must not silently treat this as `PASS`.

It may either:

```text
publish a bounded non-substantive uncertainty/failure response
```

or, if the task policy explicitly permits deterministic-only verification for that task class:

```text
continue only after all required deterministic checks pass
```

Whether a task requires an LLM Critic is a server-owned policy decision, never a model decision.


---

## 16. Verification Hierarchy

Deterministic checks dominate model judgment.

```text
Deterministic Invariants
        ↓
Evidence / Provenance Checks
        ↓
Structured Validation
        ↓
LLM Critic
```

Canonical Critic outcomes:

```text
PASS
REVISE
INSUFFICIENT_EVIDENCE
INVALID_COGNITION
CRITIC_UNAVAILABLE
```

---

## 17. Uncertainty Behavior

Metacognition must allow O-AI to state that it does not know.

Initial qualitative confidence classes:

```text
sufficient
limited
insufficient
unknown
```

Expected behavior:

```text
sufficient
    ↓
normal answer

limited
    ↓
answer with explicit uncertainty

insufficient
    ↓
ask Owner or return insufficient-information response

unknown / invalid
    ↓
do not assert a conclusion
```

Brain V1 must not manufacture precise numerical confidence until a calibrated benchmark exists.

Unresolved Critic quality after the single allowed revision does not automatically become `FAILED` if all deterministic and evidence-integrity requirements pass. It becomes a metacognitive limitation that the Publication Gate may expose as a `LIMITED` response.

However:

```text
deterministic veto
INVALID_COGNITION
required evidence missing
```

may never be downgraded into mere uncertainty.

---

## 18. Publication Gate

A response is not final merely because a model returned text.

```text
Draft
  ↓
Verification
  ↓
Metacognitive Check
  ↓
Publication Gate
```

Minimum publication conditions:

```text
required schema valid
required verification complete
no deterministic veto
uncertainty represented correctly
citation / evidence requirements satisfied
```

Publication readiness is not execution authority.

---

## 19. Turn Completion

For Context-aware Chat, a normal cognitive turn becomes `COMPLETED` only after required durable state succeeds:

```text
Final Response
        +
Assistant Message persistence
        +
Required ContextSnapshot persistence
        +
Required citation / provenance persistence
```

If persistence fails:

```text
Turn ≠ COMPLETED
```

Existing `complete_context_turn()` transaction behavior should be preserved:

```text
assistant message
+
ContextSnapshot
+
commit
```

with rollback on failure.

A provider answer alone does not define turn success.

---

## 20. Accepted User Event vs Completed Cognitive Turn

Current O-AI may persist the user message before AI inference.

Therefore:

```text
Conversation Event Accepted
        ≠
Cognitive Turn Completed
```

A user message may legitimately exist while the corresponding assistant turn failed. This remains useful for provenance, diagnosis, and future Experience evaluation.

---

## 21. Experience Eligibility

Experience processing occurs only after the primary response path has reached its terminal state.

```text
Final Response
   ↓
Durable Persistence
   ↓
COMPLETED
   ↓
──────── primary user task finished ────────
   ↓
Experience Eligibility
```

Experience is not part of response criticality.

During Brain Formation, Experience eligibility/evaluation may run only as a bounded post-turn hook associated with the completed request or an explicit owner/test invocation.

It may not create:

```text
an independent scheduler
a self-waking background agent
an unbounded autonomous learning loop
```

If Experience processing fails:

```text
User turn remains successful
```

Potential ExperienceCandidate sources include bounded outcomes such as successful cognitive turns, `INSUFFICIENT`, model timeout/unavailability, verification failure, and structured cognition failure.

### 21.1 Default Persistence Rule

In Newborn Brain V1, an ExperienceCandidate is **ephemeral by default**.

```text
Candidate created
    ↓
safe evaluation
    ↓
discard unless a separately frozen persistence contract permits retention
```

Brain Formation does not require durable accumulation of every candidate.

### 21.2 Experience Data Minimization

An ExperienceCandidate should prefer references and bounded summaries over raw data copies.

Prefer:

```text
ContextSnapshot ID / digest
Message IDs
Model/profile IDs
bounded task features
outcome codes
verification codes
safe lesson summary
```

Avoid by default:

```text
full prompts
full responses
full Context text
full Memory values
credentials
tokens
API keys
hidden system prompts
raw hidden reasoning
unnecessary personal identifiers
```

### 21.3 Sanitization and Sensitive-Data Rules

Before any future durable Experience persistence, candidates must pass a server-owned hygiene boundary that can:

```text
reject prohibited fields
redact recognized secrets / credentials
minimize unnecessary PII
pseudonymize identifiers when identity is not required
enforce workspace isolation
enforce field-size limits
preserve safe provenance references
```

“Anonymization” must not be claimed unless it is actually guaranteed. The preferred architecture is **data minimization + redaction + bounded pseudonymization**.

### 21.4 Bloat Controls for Future Persistence

Any later durable Experience store must define before activation:

```text
retention / TTL
per-workspace quotas
per-candidate size limits
deduplication / fingerprinting
promotion-state lifecycle
owner inspection / deletion path
archival / expiry behavior
```

No Experience store may grow without explicit retention and quota policy.


---

## 22. Experience Semantics

Example of a valid bounded candidate:

```text
Situation:
software_engineering task

Model:
qwen3.5:9b

Context:
snapshot abc123

Outcome:
valid structured draft
verification PASS

Lesson candidate:
This model completed this task shape successfully
under profile X.
```

Invalid automatic generalization:

```text
qwen3.5 is always the best engineering model.
```

Failure can also become Experience evidence:

```text
Situation:
Local Engineering

Model:
X

Outcome:
timeout

Candidate:
Model X timed out under profile Y
for task characteristic Z.
```

This still does not imply:

```text
Never use model X again.
```

Experience provenance should reference source artifacts rather than copy sensitive source contents whenever possible.

```text
ExperienceCandidate
    ├─ safe bounded metadata
    ├─ provenance references
    └─ minimal lesson summary
```

not:

```text
ExperienceCandidate
    └─ duplicated raw conversation / Context / secret-bearing payload
```

---

## 23. Newborn Learning Boundary

Brain V1 is born with the anatomy necessary to observe and form candidate experience, but without autonomous permanent learning authority.

```text
Observe                          YES
Reason                           YES
Evaluate                         YES
Create ExperienceCandidate       YES

Automatically promote experience NO
Automatically change Memory      NO
Automatically change Policy      NO
Automatically rewrite prompts    NO
Automatically change model route NO
Automatically modify own code    NO
Automatically execute tools      NO
Persist every ExperienceCandidate   NO
Retain raw sensitive Context copies NO
```

> **Learning anatomy exists; autonomous learning authority does not.**

---

## 24. Missing Organs and New Work

After Existing Brain reconciliation, the major systems that genuinely remain to be created are:

1. **Unified Attention Policy** over existing Context/Memory/Knowledge selectors.
2. **Canonical Task Interpretation Model** reconciling Interaction Intent, Cognitive Intent, and Task Domain.
3. **Prediction / Simulation organ.**
4. **Brain-level Metacognition coordinator.**
5. **Cognitive Critic / Verification coordinator.**
6. **ExperienceCandidate representation.**
7. **Experience Validation / Promotion boundary.**
8. **Model capability / evaluation knowledge layer** over D34/D111/D125.
9. **Generalized Cognitive Executive** built from the existing intelligence pipeline/orchestrator foundation.
10. **Working State convergence** so Normal Chat and Grounded Knowledge share one canonical cognitive state.
11. **Cognitive Resilience Governor** for turn deadlines, per-stage budgets, and circuit-breaker integration without fallback authority.
12. **Context Stabilization Policy** for one bounded pre-freeze reacquisition on verified source-change conflicts.
13. **Experience Hygiene & Retention Policy** covering minimization, secret/PII handling, quotas, deduplication, and lifecycle before any durable candidate store is enabled.
14. **Critic Exhaustion / Degraded Publication Policy** so unresolved verification never hangs and never silently publishes invalid cognition.
15. **Cognitive Artifact Envelope / Turn Manifest** for versioned provenance without raw chain-of-thought persistence.
16. **Conversation Turn Concurrency Guard** preventing out-of-order same-conversation commits.
17. **Late-Result / Terminality Enforcement** so expired or completed turns reject stale provider/Critic output.
18. **Central Cognitive Engine Invocation Coordinator** defining bounded invocation purpose and fresh authorization per call.

Reasoning, Planning, Decision, Context, Memory, routing, AI runtime, response composition, and execution governance already have meaningful foundations and are not to be rebuilt from zero.

---

## 25. What Brain Formation Explicitly Does Not Build

Until Brain V1 is born, this architecture excludes:

```text
Browser autonomy
Arbitrary tool autonomy
Background autonomous loops
Unbounded workflow autonomy
Automatic model switching
Automatic provider fallback
Autonomous memory mutation
Autonomous experience promotion
Policy learning
Prompt self-rewriting
Self-modifying code
Hidden retry loops
Unbounded Context reacquisition loops
Unbounded Critic loops
Autonomous background Experience loops
Out-of-order same-conversation cognitive commits
Acceptance of late provider results after turn terminality
Public / LAN / Internet exposure expansion
```

These belong to later phases and require separately frozen security design.

---

## 26. Brain V1 Birth Criteria

O-AI Brain V1 may be declared **BORN** only when all of the following are demonstrated:

1. All 17 brain organs have explicit bounded contracts.
2. Cross-cutting Cognitive Artifact provenance/versioning contracts exist without adding an unnecessary eighteenth organ.
3. Cognitive Self is bound to exact workspace / conversation / project context.
4. D94–D97 remains the canonical Context substrate.
5. One Cognitive Turn uses one verified frozen ContextSnapshot after any permitted pre-freeze stabilization attempt.
6. Context source-change handling is bounded to at most one full reacquisition and never performs partial stale/fresh merges.
7. `ExecutionContext` or its reconciled successor serves as canonical Working State.
8. Normal Chat and Grounded Knowledge use a coherent shared cognitive-state architecture.
9. Intent/Task semantics are separated into Interaction Intent, Cognitive Intent, and Task Domain.
10. Brain task semantics preserve D104/D125 routing authority unless a separately frozen milestone explicitly changes it.
11. Reasoning artifacts remain safe structured metadata and do not persist hidden chain-of-thought.
12. Prediction is explicitly distinguishable from Fact.
13. Cognitive Planning remains distinct from Execution Planning.
14. Decision support remains advisory and cannot grant Owner authority.
15. Metacognition can return `insufficient`, `limited`, or `unknown`.
16. Cognitive Critic combines deterministic and advisory verification with deterministic veto priority.
17. Critic revision is bounded to at most one automatic revision.
18. Critic exhaustion has explicit terminal behavior and cannot create an unbounded loop.
19. `INVALID_COGNITION` and deterministic vetoes cannot be downgraded into uncertainty-only publication.
20. Model invocation purposes are server-owned, bounded, and mediated through the central authorized invocation boundary.
21. Maximum draft generations and maximum total model invocations are separately defined and enforced.
22. No hidden model retry, provider fallback, or model fallback exists.
23. Cognitive Turn deadlines and expensive-stage budgets are enforced with bounded timeout outcomes.
24. Circuit breakers fail fast without silently changing provider, model, workspace, task domain, or authority path.
25. One active Cognitive Turn per conversation is enforced or an equivalent mechanism proves ordered commits.
26. Late model/Critic results after terminality cannot mutate cognitive or durable response state.
27. D125 model/profile bindings remain server-owned and fail-closed.
28. No Cognitive Organ receives raw provider authority.
29. A minimal Cognitive Turn Manifest or equivalent safe provenance record can bind turn, Context, model authorization, verification outcome, and terminal status without raw hidden reasoning.
30. ExperienceCandidate cannot auto-promote into Memory, Policy, Prompt, Routing, or Code.
31. ExperienceCandidate is ephemeral by default until a separately frozen persistence contract exists.
32. Any durable Experience design includes data minimization, secret handling, PII minimization, workspace isolation, size limits, retention, quotas, and deduplication before activation.
33. Experience processing cannot create an autonomous background learning loop during Brain Formation.
34. Response completion preserves required provenance transactionally.
35. Brain failures normalize safely without leaking provider internals.
36. Existing O-AI authority, workspace isolation, execution governance, Memory governance, and Context security invariants remain intact.
37. Brain integration regression tests pass.
38. Brain-specific security tests pass.
39. Latency/resilience tests cover timeouts, open breakers, Context instability, same-conversation concurrency, late results, model failure, and Critic exhaustion without hangs.
40. Owner Guided Acceptance demonstrates multi-stage cognition without autonomous action.
41. Brain benchmark baseline can be established for the next Learning & Development phase.

At that point:

```text
O-AI COGNITIVE BRAIN V1
STATUS: BORN
```

This does not mean:

```text
STATUS: MATURE
STATUS: AUTONOMOUS
STATUS: SELF-LEARNING
```


---

## 27. Proposed D126–D137 Boundaries

These boundaries are **proposed architecture boundaries only**. They are not Design Freeze milestones and are not authorized for implementation until separately reviewed and frozen.

| Milestone | Proposed Boundary | Primary Existing Assets Reused | Primary New Work |
|---|---|---|---|
| **D126** | Cognitive Brain Constitution & Core Contracts V1 | Sovereign Core, Context/Workspace invariants | Brain contracts, authority rules, lifecycle vocabulary, artifact envelope/turn-manifest contracts, resilience invariants, D104/D125 compatibility rules |
| **D127** | Perception / Attention / Task Understanding V1 | Context Sources, ContextResolver, CommandDecisionEngine, Reasoning intent, D104 | Unified attention + canonical task semantics without routing-authority expansion |
| **D128** | Working Memory & Cognitive State V1 | `ExecutionContext`, ChatTurnResult | Shared cognitive state convergence + same-conversation turn ordering/concurrency contract |
| **D129** | Cognitive Context & Memory Integration V1 | D94–D97, MemoryResolver, Knowledge retrieval | Brain-facing context integration + bounded pre-freeze Context stabilization |
| **D130** | Structured Reasoning & Prediction V1 | ReasoningService, ReasoningPlan | Extended structured reasoning + new Prediction organ |
| **D131** | Planning / Decision Cognitive Integration V1 | PlanningService, DecisionService, GoalService | Canonical sequencing and clearer boundaries |
| **D132** | Metacognition & Uncertainty V1 | Missing-information behavior, ConfidenceEvaluator | Brain-level uncertainty, limited/insufficient behavior, and “I do not know” behavior |
| **D133** | Verification / Critic & Publication Gate V1 | CitationEngine, ConflictDetector, Context integrity, schema validators, D132 metacognitive state | Cognitive Critic coordinator + publication gate + Critic exhaustion behavior |
| **D134** | Experience / Learning Boundary V1 | Conversation history, snapshots, audit, revisions | ExperienceCandidate + promotion boundary + hygiene/minimization/retention contract + bounded post-turn hook, no autonomous learning |
| **D135** | Model Intelligence & Capability Knowledge V1 | D34, D111, D125 | Read-only capability/evaluation knowledge |
| **D136** | Cognitive Executive / Integrated Brain Runtime V1 | Pipeline, DomainStep, KnowledgeOrchestrator, AIRuntime boundary | Generalized Cognitive Executive + central invocation coordinator + fresh authorization per call + turn deadlines + stage budgets + circuit-breaker integration + late-result enforcement + bounded Critic revision |
| **D137** | Newborn Brain Integration & Security Review V1 | Entire Brain V1 | Regression, adversarial, concurrency, late-result, latency/resilience, privacy-hygiene, guided acceptance, Birth decision |

No implementation should begin merely because this table exists.

Each milestone must still receive its own design review and authorization.

---

## 28. Proposed Brain Formation Exit State

After D137, if all Birth Criteria pass:

```text
O-AI BRAIN FORMATION
STATUS: COMPLETE

O-AI COGNITIVE BRAIN V1
STATUS: BORN

Autonomous Learning: DISABLED
Hands / Legs:        NOT STARTED
```

The next phase may then be designed separately:

```text
O-AI LEARNING & DEVELOPMENT
```

That phase may introduce:

```text
Brain Benchmark
Experience accumulation
Experience validation
Model capability evaluation
Context optimization
Reasoning quality improvement
Learning policy
Longitudinal improvement
```

Only after cognitive maturation is measured and safe should O-AI proceed toward:

```text
HANDS
Tools / Browser / Workflow

LEGS
Long-running / Background / Autonomous Work
```

---

## 29. Architecture Summary

O-AI already contains a substantial embryonic cognitive system:

```text
Context
Memory
Knowledge
Reasoning
Planning
Decision
Goals
AI routing
Model profiles
ExecutionContext
Pipeline
Response
Execution governance
```

Brain Formation does not discard these systems.

It does three things:

```text
RECONCILE what already exists

ADD only the genuinely missing organs

INTEGRATE everything into one bounded cognitive lifecycle
```

The final architectural identity is:

```text
O-AI Intelligence
=
Sovereign Authority
+
Cognitive Architecture
+
Verified Context
+
Memory
+
Reasoning
+
Prediction
+
Planning
+
Decision Support
+
Metacognition
+
Verification
+
Experience Boundary
+
Intelligence Engines
```

The governing developmental principle remains:

> **Think well → understand correctly → judge safely → learn carefully → only then act more broadly.**

Or in the newborn analogy:

> **First, make sure the child is born with the full cognitive anatomy. Then teach, observe, measure, and let intelligence mature. Only after that do we give O-AI stronger hands and legs.**

---


## 29.1 Architecture Review Hardening Summary

Draft 0.6 incorporates the Draft 0.5 resilience hardening plus the Owner Architecture Final Review findings without weakening the original sovereignty boundaries:

```text
Latency / hang risk
→ Turn deadline + stage budgets + circuit breakers
→ no hidden fallback authority

Context race condition
→ one bounded full pre-freeze stabilization attempt
→ immutable snapshot after freeze

Critic blind spot
→ explicit Critic exhaustion and limited/safe terminal publication behavior
→ no third autonomous revision

Experience data bloat / privacy
→ ephemeral-by-default candidate policy
→ data minimization, secret/PII hygiene, quotas, retention, deduplication

Cross-organ provenance gap
→ CognitiveArtifactEnvelope + minimal Cognitive Turn Manifest

LLM invocation ambiguity
→ Executive-owned Invocation Coordinator
→ explicit purpose + fresh authorization per call

Same-conversation race / late-result risk
→ one active turn per conversation
→ terminal turns reject stale provider/Critic output

D104/D125 compatibility risk
→ richer cognitive task metadata remains non-authoritative for routing unless separately frozen

Milestone dependency inversion
→ Metacognition moved before Verification/Critic
```

These changes preserve the original Brain Formation principle:

> **Resilience may improve availability and UX, but it may not weaken provenance, authority, workspace isolation, or fail-closed safety.**

---

## 30. Current Status

```text
O-AI COGNITIVE BRAIN ARCHITECTURE V1

Existing Brain Survey:            COMPLETE
Reconciliation Pass 1:            COMPLETE
Reconciliation Pass 2:            COMPLETE
Reconciliation Pass 3:            COMPLETE
Reconciliation Pass 4:            COMPLETE

Mother Architecture:               FROZEN
Design Revision:                   0.6
Architecture Final Review:         PASS
Architecture:                      DESIGN FROZEN
Brain Anatomy:                     FROZEN
Canonical Flow:                    FROZEN
Organ Contracts:                   FROZEN
Lifecycle:                         FROZEN
Invariants:                        FROZEN
Existing-System Reconciliation:    FROZEN
Missing Organs:                    FROZEN
Birth Criteria:                    FROZEN
D126-D137 Boundaries:              APPROVED / FROZEN AS BOUNDARIES

DESIGN FREEZE:                     YES
IMPLEMENTATION:                   NOT STARTED
D126:                             NOT STARTED
CODE CHANGE:                      NONE
COMMIT:                            DESIGN FREEZE COMMIT
PUSH:                              NO
```

---

**End of O-AI Cognitive Brain Architecture V1 - Design Freeze**
