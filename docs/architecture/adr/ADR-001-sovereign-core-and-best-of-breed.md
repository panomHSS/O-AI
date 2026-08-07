# ADR-001: Sovereign Core and Best-of-Breed Architecture

## Status

Accepted

## Date

2026-08-07

## Context

O-AI was initially developed by implementing many capabilities
directly inside the project.

As the system grew, it became clear that some capabilities are
fundamental to O-AI identity and authority, while others are
commodity capabilities already implemented effectively by mature
external systems.

Building every capability internally would increase development
time, maintenance cost, operational complexity, and technical risk.

However, allowing external frameworks to own O-AI policy,
authorization, memory authority, project state, or execution
governance would weaken O-AI sovereignty and create architectural
lock-in.

A new architectural boundary is therefore required.

## Decision

O-AI adopts a:

**Sovereign Core + Best-of-Breed Components**

architecture.

The O-AI Sovereign Core owns authoritative policy and state.

External systems provide replaceable capabilities through
O-AI-controlled ports and adapters.

External capability does not imply external authority.

No external AI model, agent framework, workflow engine,
vector database, or connector may become the authoritative
source for:

- O-AI identity
- user authority
- goals
- project authority
- memory policy
- approval
- permissions
- execution governance
- revision safety
- audit provenance

Side-effecting capabilities must remain subordinate to O-AI
policy and execution governance.

## Principles

### 1. Sovereignty

O-AI retains authority over its defining policies and state.

### 2. Replaceability

External components must be replaceable behind stable boundaries.

### 3. Data Ownership

Authoritative O-AI data remains under O-AI control.

### 4. Capability Is Not Authority

External systems may perform work but do not decide whether
O-AI has authority to perform that work.

### 5. Minimum Necessary Infrastructure

New infrastructure is introduced only for demonstrated requirements.

### 6. Graceful Degradation

External failures may reduce capability but must not corrupt
authoritative O-AI state.

### 7. Exit Strategy

Every adopted external component must have a viable replacement
and removal path.

## Initial Technology Direction

Adopt:

- PostgreSQL + pgvector
- OpenTelemetry
- Ollama as an optional provider
- Playwright behind controlled execution boundaries

Trial:

- Docling
- LiteLLM
- n8n

Defer:

- Qdrant
- LangGraph
- Temporal
- Langfuse
- Keycloak
- OpenHands

## Consequences

### Positive

- O-AI preserves its identity and governance model.
- Development effort can focus on unique O-AI capabilities.
- Commodity capabilities can use mature external implementations.
- Vendor lock-in is reduced.
- External technologies can evolve independently from the Core.
- Local and cloud capabilities can coexist.
- Future replacement is possible through ports and adapters.

### Negative

- Adapter boundaries require additional design discipline.
- Some capabilities may temporarily exist in multiple
  implementations during migration.
- Integration testing becomes increasingly important.
- Data ownership and failure boundaries must be explicitly designed.
- External licenses and operational requirements must be reviewed
  before adoption.

## Rejected Alternative

### Build Everything Internally

Rejected because it creates unnecessary implementation and
maintenance burden for commodity infrastructure.

### Let an Agent Framework Become the Application Architecture

Rejected because it would allow an external framework to become
the implicit owner of O-AI state, workflow, or authority.

### Standardize Entire O-AI Around One Vendor

Rejected because it creates excessive vendor lock-in and weakens
replaceability.
