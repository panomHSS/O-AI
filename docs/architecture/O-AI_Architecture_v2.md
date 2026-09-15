# O-AI Architecture v2

## Status

Accepted

## Baseline

Architecture v2 begins from the stable O-AI baseline:

- Commit: `a1243be`
- Tests: 300 passed
- Skipped: 1
- Warnings: 4
- Subtests: 54
- Failures: 0

---

## 1. Architecture Vision

O-AI Architecture v2 follows the principle:

> รักษากฎ O-AI 100% แต่ใช้ Best-of-Breed Components

สิ่งใดเป็นหัวใจของ O-AI เราสร้างและควบคุมเอง

สิ่งใดมีเครื่องมือที่ดีอยู่แล้ว เราใช้มันอย่างฉลาด

แต่ไม่มีเครื่องมือใดมีสิทธิ์อยู่เหนือกฎของ O-AI

A third-party component is selected because it fits O-AI.

O-AI must never be redesigned merely to fit a third-party component.

---

## 2. Sovereign Core

The O-AI Sovereign Core owns authoritative policy and state for:

- Constitution and HEART
- User authority and identity
- Goals
- Projects
- Personal context
- Memory policy
- Decision policy
- Proposals
- Approvals
- Permissions and capabilities
- Execution governance
- Revision safety
- Audit and provenance

No external model, framework, workflow engine, vector database,
or connector may become the source of truth for these responsibilities.

---

## 3. Capability Is Not Authority

External components may provide capabilities.

They do not receive O-AI authority.

Examples include:

- LLM inference
- Embeddings
- Vector search
- Document processing
- Workflow automation
- Browser automation
- Speech processing
- External integrations
- Observability

A component may propose or execute an operation only through
O-AI-controlled boundaries.

Side-effecting operations must follow the appropriate governance path:

Intent
→ Policy
→ Capability Validation
→ Proposal / Approval when required
→ Trusted Execution Context
→ Execution Governance
→ Port
→ Adapter
→ External Component

---

## 4. Ports and Adapters

O-AI Core must depend on capability abstractions rather than vendors.

Planned ports include:

- LLMPort
- EmbeddingPort
- VectorStorePort
- DocumentPort
- WorkflowPort
- BrowserPort
- SpeechToTextPort
- TextToSpeechPort
- SearchPort
- NotificationPort
- ExternalToolPort
- ObservabilityPort

Vendor-specific implementations belong behind adapters.

Examples:

LLMPort
→ OpenAIAdapter
→ GeminiAdapter
→ OllamaAdapter

VectorStorePort
→ PostgresVectorAdapter
→ pgvector

DocumentPort
→ DoclingAdapter

WorkflowPort
→ N8nAdapter

BrowserPort
→ PlaywrightAdapter

---

## 5. Replaceability Principle

Every important external dependency must have an exit strategy.

Before adoption, O-AI must be able to answer:

1. How is the component integrated?
2. Where does its data live?
3. Who owns the data?
4. How is the data backed up?
5. How is the component upgraded?
6. How are failures detected?
7. What happens when it is unavailable?
8. How can it be replaced?
9. How can its data be migrated?
10. How can it be removed completely?

If removing a third-party component causes O-AI to lose identity,
memory authority, project authority, approval authority,
or execution governance, the architecture boundary is incorrect.

---

## 6. Data Ownership

O-AI distinguishes authoritative data from derived data.

### Authoritative Data

Examples:

- Identity
- Goals
- Projects
- Project revisions
- Memory records
- Memory provenance
- User decisions
- Approvals
- Execution history
- Audit records

Authoritative data must remain under O-AI control.

### Derived or Rebuildable Data

Examples:

- Embeddings
- Vector indexes
- Caches
- Temporary chunks
- Search indexes
- Non-promoted model responses
- Observability traces

Derived data should be rebuildable from authoritative sources
whenever practical.

Vector storage is not memory.

An embedding is not knowledge.

An LLM response is not automatically truth.

---

## 7. Database Strategy

SQLite remains suitable for lightweight development during migration.

The target production-grade data platform is:

PostgreSQL
+ pgvector

PostgreSQL will hold authoritative relational state.

pgvector will provide derived vector retrieval capabilities.

Migration from SQLite must be staged and regression-tested.

---

## 8. AI Provider Independence

O-AI must not depend permanently on a single model provider.

The intended architecture is:

O-AI
→ LLMPort
→ Provider Adapter

Potential providers include:

- OpenAI
- Gemini
- Ollama
- other future providers

LiteLLM may be evaluated as an optional gateway.

It must not become mandatory to the O-AI Sovereign Core.

Model routing policy belongs to O-AI.

Provider selection may consider:

- Privacy
- Cost
- Latency
- Capability
- Task complexity
- Availability

---

## 9. Local Intelligence

Local inference is an optional capability.

Ollama is the initial local-provider candidate.

O-AI policy determines when local or cloud inference is appropriate.

Provider-specific logic must not leak into domain policy.

---

## 10. Memory Architecture

O-AI owns:

- Memory policy
- Memory lifecycle
- Memory authority
- Provenance
- Update rules
- Forgetting rules
- Memory resolution

External systems may provide:

- Embeddings
- Vector storage
- Similarity search

The retrieval infrastructure must not become the authority
for personal memory.

---

## 11. Document Intelligence

Existing document parsers remain available during migration.

Docling will be evaluated behind DocumentPort.

Migration must be based on testing against real O-AI document
workloads rather than feature claims alone.

---

## 12. Workflow Automation

Workflow engines are optional execution capabilities.

n8n may be evaluated behind WorkflowPort.

n8n must not become:

- O-AI's policy engine
- O-AI's approval authority
- O-AI's source of truth
- O-AI's execution governance authority

Important workflow intent, authorization, execution outcome,
and audit information remain under O-AI control.

---

## 13. Browser Automation

Playwright is the initial BrowserPort implementation candidate.

Browser automation is treated as a side-effecting capability.

Browser actions must pass through O-AI policy and execution
governance before execution.

Isolation and safe execution boundaries are required.

---

## 14. Observability and Audit

Observability and audit have different responsibilities.

OpenTelemetry answers:

"What happened technically?"

O-AI Audit answers:

"What did O-AI decide or do, under whose authority,
and why was it permitted?"

Audit remains part of the Sovereign Core.

OpenTelemetry is an external observability capability.

---

## 15. Minimum Necessary Infrastructure

O-AI will not add infrastructure merely because the technology
is powerful or popular.

A component is introduced only when it solves a demonstrated
O-AI requirement with sufficient benefit.

Currently deferred technologies include:

- Qdrant
- LangGraph
- Temporal
- Langfuse
- Keycloak
- OpenHands

Deferred does not mean rejected.

These technologies may be reconsidered when requirements change.

---

## 16. Graceful Degradation

External component failure may reduce capability.

It must never corrupt O-AI authority or authoritative state.

Examples:

- LLM unavailable → inference capability degrades safely.
- Workflow engine unavailable → execution fails safely.
- Vector retrieval unavailable → authoritative memory remains intact.
- Browser worker fails → action is recorded as failed, not assumed successful.

Principle:

> Unavailability may reduce capability, but must never corrupt authority.

---

## 17. Technology Decisions

### Sovereign / Build

- O-AI Core
- Goals
- Projects
- Memory Policy
- Decision Policy
- Proposal
- Approval
- Permissions
- Execution Governance
- Revision Safety
- Audit and Provenance

### Adopt

- PostgreSQL + pgvector
- OpenTelemetry
- Ollama as an optional local provider
- Playwright behind a controlled browser boundary

### Trial

- Docling
- LiteLLM
- n8n

### Defer

- Qdrant
- LangGraph
- Temporal
- Langfuse
- Keycloak
- OpenHands

---

## 18. Architecture Invariant

The defining invariant of O-AI Architecture v2 is:

> External systems may extend O-AI capability,
> but only the O-AI Sovereign Core may exercise O-AI authority.

This invariant must remain true across future architecture changes.

## 19. D50 Implementation Reconciliation Checkpoint

The historical Architecture v2 baseline above records the point at which the v2
direction was accepted. D50 does not replace that historical record. It records
the implementation reconciliation reached after D31-D49 and Grounded Knowledge
AI integration.

By D50, the Sovereign Core principles are concretely represented by:

- explicit Adapter Registry and provider routing boundaries;
- capability/model discovery separated from routing and execution;
- deterministic execution planning;
- authorization separated from planning;
- dedicated Tool, Module and AI runtimes;
- owner-controlled capability permission and approval paths;
- explicit Chat Action and bounded Safe Write paths;
- durable, non-authoritative execution audit;
- authorization-gated normal Chat and Grounded Knowledge AI generation.

Normal Chat and Grounded Knowledge may use cloud or Local AI capabilities, but
the provider receives no O-AI authority. Retrieved documents, Memory content,
provider prompts and model output likewise remain data rather than execution
authority.

The implementation therefore preserves the defining Architecture v2 invariant:

> External systems may extend O-AI capability, but only the O-AI Sovereign Core
> may exercise O-AI authority.

D50 does not claim that every future Architecture v2 technology direction is
implemented. PostgreSQL/pgvector migration, optional external workflow/browser
capabilities, OCR, future connectors and other planned integrations remain
separate owner-approved milestones.
