# Architectural Decisions

This document records architectural decisions. New decisions should be appended with a stable identifier and reviewed before implementation.

## ADR-001: FastAPI backend

**Decision**  
Use FastAPI as the backend HTTP API framework.

**Context**  
O-AI needs a typed, versioned API foundation with validation, operational health endpoints, and room for modular capabilities.

**Alternatives**  
Flask, Django REST Framework, Node.js API frameworks, or a monolithic full-stack framework.

**Rationale**  
FastAPI combines Pydantic validation, async support, OpenAPI generation, and a focused Python service model suited to explicit API contracts.

**Consequences**  
Backend contracts use Pydantic schemas and routes remain versioned. The team must maintain Python typing and separate service logic from route handlers.

## ADR-002: Next.js frontend

**Decision**  
Use Next.js with React and TypeScript for the web frontend.

**Context**  
O-AI requires a production-oriented web client that can grow from a small shell into a richer personal workspace.

**Alternatives**  
Plain React with Vite, server-rendered Python templates, or another SPA framework.

**Rationale**  
Next.js provides App Router conventions, React ecosystem compatibility, TypeScript support, and production deployment options.

**Consequences**  
Frontend routes follow App Router conventions. Server/client boundaries must remain explicit, and browser code must not hold backend integration secrets.

## ADR-003: Layered, modular application structure

**Decision**  
Separate API, core infrastructure, schemas, services, and models in the backend; keep frontend route concerns within the App Router.

**Context**  
Future capabilities will add integrations and data domains that should not entangle transport or presentation logic.

**Alternatives**  
Featureless flat folders, a single monolithic service layer, or provider-specific logic in route handlers.

**Rationale**  
Layering makes system boundaries clear, supports testing, and allows provider adapters to change without rewriting product contracts.

**Consequences**  
Changes may require explicit interfaces and small additional files. Architecture changes require approval before implementation.

## ADR-004: Versioned API boundary

**Decision**  
Expose HTTP endpoints below a versioned API prefix.

**Context**  
The frontend and future external clients need stable contracts as O-AI evolves.

**Alternatives**  
Unversioned routes, versioning through headers only, or breaking changes in place.

**Rationale**  
Path versioning is visible, simple for clients, and allows deliberate compatibility management.

**Consequences**  
New public endpoints must be placed in an API version. Breaking changes require a new version or an approved migration plan.

## ADR-005: Approval-first integrations and plugins

**Decision**  
Treat external integrations and plugins as permissioned boundaries requiring explicit approval and documented capabilities.

**Context**  
Gmail, Calendar, document stores, and plugins can access sensitive data or create external effects.

**Alternatives**  
Implicit provider access, broad default OAuth scopes, or unrestricted plugin execution.

**Rationale**  
Explicit boundaries support privacy, least privilege, user control, auditability, and safe revocation.

**Consequences**  
Future modules need consent flows, scoped credentials, audit logging, and a documented capability model before implementation.

## ADR-006: Provider-neutral chat service

**Decision**  
Keep `ChatService` dependent only on the `ChatProvider` interface and compose the active provider through dependency injection.

**Context**  
O-AI now needs an OpenAI implementation while preserving the existing chat endpoint and leaving room for Anthropic, Gemini, Ollama, Azure OpenAI, or other providers.

**Alternatives**  
Call the OpenAI SDK directly from the API router, hardcode a provider in `ChatService`, or create provider-specific API endpoints.

**Rationale**  
A provider-neutral service isolates external SDK concerns at the infrastructure edge. The API route continues to call only `ChatService`, while configuration supplies the selected provider credentials and model.

**Consequences**  
Provider implementations must honor the `ChatProvider` contract and translate unsafe external failures into safe service errors. A new provider can be substituted in the composition layer without changing the API contract or frontend.

## ADR-007: Standard API response envelopes and request correlation

**Decision**  
Return all API results in success or error envelopes and attach an `X-Request-ID` to every response.

**Context**  
As O-AI grows beyond health and chat, clients need a predictable transport contract and operators need a correlation value for diagnosing failures without exposing internals.

**Alternatives**  
Use endpoint-specific top-level responses only, expose framework-default errors, or add correlation only to selected endpoints.

**Rationale**  
A shared envelope centralizes client parsing and safe error behavior. Request IDs preserve caller correlation when supplied and make unexpected server failures traceable in logs.

**Consequences**  
Endpoint data contracts are nested under `data`; frontend API clients unwrap the envelope before passing typed data to UI components. New exception handlers must return safe codes and messages, never stack traces or provider details.
