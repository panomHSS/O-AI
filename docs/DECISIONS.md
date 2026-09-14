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

## ADR-008: Local SQLite conversation memory for Version 1

**Decision**
Use SQLite and SQLAlchemy for persistent Version 1 conversation memory, with repository/service boundaries and local-only Docker volume persistence.

**Context**
O-AI needs durable conversation continuity without introducing external infrastructure, embeddings, vector databases, Redis, or remote persistence services.

**Alternatives**
Browser-only history, PostgreSQL, a vector database, Redis, external memory services, or no persisted history.

**Rationale**
SQLite is local-first, deploys with the application, supports transactional message history, and is sufficient for bounded recent-context retrieval. Repositories isolate SQLAlchemy; services own transactions and provider coordination.

**Consequences**
Alembic owns production schema evolution. Startup verifies the configured managed SQLite schema read-only and never creates, upgrades, or stamps it. Recent context is bounded and string-formatted before the unchanged provider interface.

## ADR-009: Local SQLite FTS5 knowledge indexing

**Decision**
Use reader adapters, SQLite ORM tables, and a separate SQLite FTS5 virtual table for Version 1 local document knowledge.

**Context**
O-AI needs traceable local document ingestion and keyword search without cloud upload, embeddings, vector infrastructure, OCR, or external search services.

**Alternatives**
Embeddings with a vector database, cloud document storage/search, a managed full-text service, LangChain/LlamaIndex, or no persistent index.

**Rationale**
SQLite is already the local persistence foundation. FTS5 provides a small, local keyword-search index while reader adapters preserve source locations and keep format-specific parsing outside services and API routes.

**Consequences**
Documents are identified by normalized root-relative source path; identical content at different paths remains separately searchable for provenance. FTS5 is created idempotently outside `create_all()` and requires an explicit migration plan if its definition changes. Search is lexical, not semantic. OCR, attachment extraction, and embeddings remain out of scope; scanned/image-only PDF support is planned for 0.6.2.

## ADR-010: Evidence-first knowledge answers

**Decision**
Retrieve and deterministically rank local evidence before invoking the unchanged provider, then return only validated citations and transparent evidence quality.

**Consequences**
The current single-string provider input reduces, but cannot fully prevent, prompt injection. Assistant-message citation snapshots are persisted through Alembic revision `0002_message_citations` and are transactionally associated with assistant messages as historical evidence.

## ADR-011: Architecture Review 1.0 operational baseline

**Decision**
Treat O-AI as ready with required pre-hardening corrections for the trusted local, single-owner deployment model.

**Consequences**
No P0 architectural finding is confirmed. Releases 0.9.0A through 0.9.0E prioritize documentation truth, backup/restore confidence, retry/privacy boundaries, composition/test hardening, and measured readiness. Authentication, distributed infrastructure, semantic/vector retrieval, and local-LLM infrastructure remain deferred until an owner-approved requirement and evidence justify them.

## ADR-012: Durable owner-approved Project update proposals

**Decision**
Introduce durable Project update proposals as the write-intent boundary between Project-aware AI conversations and owner-controlled Project state.

A Project-associated conversation may produce a proposal for `current_summary` and/or `next_action`, but the proposal must not mutate the Project when it is created. Applying a proposal requires explicit owner approval.

Each proposal records the Project revision on which it was based. Approval must pass through the existing `ProjectService` mutation boundary and its optimistic-concurrency rules rather than writing Project state directly.

Project update proposals use the lifecycle states `PENDING`, `APPLIED`, `REJECTED`, and `STALE`.

**Context**
O-AI can already associate a conversation with a durable Project and resolve the Project's current read-only state at provider-request time. The Project backbone also provides immutable revision history and owner-controlled mutations.

The next capability should allow O-AI to identify useful Project progress during conversation without weakening the existing rule that AI output cannot autonomously change durable owner-controlled Project state.

A proposal also needs to survive browser refreshes and application restarts and must remain traceable to the Project revision that informed it.

**Alternatives**
Allow the AI to update Projects directly, return transient non-persisted suggestions only in chat responses, allow the frontend to write proposed values directly to Project endpoints, or introduce a separate autonomous task/execution system.

**Rationale**
A durable proposal separates AI-generated intent from authoritative Project state. Explicit approval preserves owner control, while persistence provides continuity, auditability, and safe handling across sessions.

Recording `base_revision` allows approval to detect when the Project has changed since the proposal was generated. Reusing `ProjectService` preserves the existing mutation, immutable revision, validation, and optimistic-concurrency boundaries instead of creating a second Project write path.

Limiting Version 1 proposals to `current_summary` and `next_action` keeps AI-assisted changes focused on operational Project progress. Project `title`, `objective`, and `status` remain outside automatic proposal generation.

**Consequences**
Project update proposals require durable SQLite persistence and an Alembic migration.

Creating a proposal never creates a Project revision and never changes Project state.

A `PENDING` proposal may be explicitly approved or rejected by the owner. Approval applies the proposed Project fields through `ProjectService` only when the proposal's `base_revision` still matches the Project's current revision.

If the Project has changed since proposal creation, the proposal must not overwrite newer state and must be treated as stale according to the approved service contract.

Rejecting a proposal changes only proposal state and does not create a Project revision.

Conversations without a Project association cannot create Project update proposals.

Proposal generation does not authorize autonomous execution, scheduling, status transitions, title changes, objective changes, external side effects, or plugin/integration actions.

## ADR-013: Versioned adapter and command contracts

**Decision**
Introduce additive, provider-neutral Python contracts for AI adapters, tool/module adapters, and the command flow `CommandRequest -> ExecutionPlan -> Result -> Response`.

AI Adapter Contract v1 uses `AIRequest`, `AIResult`, and the structural `AIAdapter` protocol. Tool/Module Adapter Contract v1 uses distinct structural `ToolAdapter` and `ModuleAdapter` protocols over the shared command contracts. Contract implementations identify the contract version they implement.

The existing `ChatProvider.generate_reply(message: str) -> str` contract remains the active chat compatibility path. `OpenAIChatProvider`, chat dependency wiring, the versioned chat API, and its response schema remain unchanged.

**Context**
O-AI needs stable boundaries for future AI providers, bounded tools/modules, and owner-controlled command handling before D22-D30 add implementations. Defining those boundaries now reduces future coupling to provider SDKs and avoids requiring Core services to be rewritten when additional adapters are approved.

D21 does not require a Local AI runtime, tool dispatcher, module runtime, public endpoint, persistence, or autonomous execution behavior.

**Alternatives**
Extend `ChatProvider` in place, make future adapters depend directly on provider SDK types, reuse the existing plugin contract for every module, or defer all contracts until runtime implementations are introduced.

**Rationale**
Additive protocols preserve the proven chat path while giving future implementations a small, typed, provider-neutral boundary. Shared immutable command values make the hand-offs explicit without selecting an orchestrator or granting execution authority. Distinct tool and module protocols preserve capability boundaries while allowing them to share the same command vocabulary.

**Consequences**
The new contracts are internal Python boundaries, not public HTTP schemas. They add no external integration, dependency, database change, migration, side effect, or execution runtime.

Creating a `CommandRequest` or `ExecutionPlan` never authorizes or initiates execution. `ExecutionPlan.owner_approval_required` defaults to `True`, and an adapter can run only if a separately approved future orchestration layer explicitly calls it after enforcing owner-control policy.

Future adapter or orchestration implementations require their own owner-approved scope, security and permission review, composition changes, and tests. Migrating chat from `ChatProvider` to `AIAdapter` also requires a separate approved compatibility plan.

Rollback consists only of removing the D21 contract modules, focused tests, and this documentation. It requires no data or public API rollback.

## ADR-014: Command/Input Pipeline for the existing chat boundary

**Decision**
Introduce `CommandInputPipeline` as the narrow, internal D22 input boundary between the existing versioned chat route and the existing `ConversationService` chat path.

The chat route remains the Web/Chat input adapter. After `ChatRequest` validation, it uses the existing HTTP correlation value from `request.state.request_id` to create a `CommandRequest` with the fixed identifier `chat.message` and the existing `message`, `conversation_id`, and `project_id` values. The pipeline validates that exact internal argument shape before delegating unchanged values to `ConversationService.send_message`.

**Context**
D21 established provider-neutral command contracts, but normal chat did not yet cross the internal command boundary. O-AI needs that input seam before later, separately approved command capabilities can be considered, while preserving the stable UI, HTTP, conversation, Project, and provider behavior.

**Alternatives**
Keep the chat route calling `ConversationService` directly, create a new public command endpoint, make the existing intelligence or Decision pipelines handle commands, or add generic command dispatch and routing now.

**Rationale**
A fixed, fail-closed `chat.message` boundary makes the current web input explicit without changing public contracts or conflating command intake with intent, routing, planning, or execution. Exact argument and runtime type validation prevents malformed internal mappings from reaching the existing conversation path.

**Consequences**
`CommandInputPipeline.normalize_chat` is side-effect free: it performs no persistence, provider call, message-content logging, tool/module invocation, or external access. `process_chat` supports only `chat.message`; unsupported commands and malformed arguments fail before `ConversationService` is called.

The pipeline does not create `ExecutionPlan`, call AI/tool/module adapters, select providers, classify intent, dispatch commands generically, or authorize execution. `ChatProvider`, `OpenAIChatProvider`, the chat endpoint/schema/envelope, frontend behavior, and existing ConversationService/project-linked behavior remain unchanged from the caller's perspective.

This is an internal, additive change with no data migration or public API migration. Rollback restores the direct route-to-ConversationService call and removes the D22 pipeline, tests, and documentation without affecting persisted data or clients. Any additional command, routing, adapter invocation, execution behavior, or external side effect requires separate owner-approved architecture work.

## ADR-015: Deterministic command intent and decision boundary

**Decision**
Introduce an additive, internal D23 `CommandDecisionEngine` that transforms a `CommandRequest` into an ephemeral `CommandDecision` for future command routing preparation.

The decision taxonomy is intentionally narrow: `chat_message` or `unknown` intent, with `defer_to_existing_chat` or `reject` disposition. D23 may preserve a provider preference hint of `unspecified`, `automatic`, or `local_ai_explicit`, but it does not select, configure, or invoke a provider.

**Context**
D22 makes the existing chat input explicit as `chat.message` before it delegates to `ConversationService`. Future routing requires a deterministic, reviewed command-level decision seam that is separate from answer composition and from execution.

**Alternatives**
Reuse `ReasoningService` intent classification, extend explanatory `DecisionService`, add provider routing now, add generic command dispatch, or defer all command decisions until adapter implementations exist.

**Rationale**
A separate pure engine preserves the established semantics and responsibilities of existing reasoning and decision analysis. Its fail-closed disposition makes unsupported commands explicit rather than inferred. Narrow phrase detection captures only unmistakable future provider-routing preferences while treating generic, ambiguous, conflicting, or absent hints as `unspecified`.

**Consequences**
`CommandDecisionEngine` has no provider, AI adapter, tool/module, database, HTTP, persistence, logging, or external dependency. It is deterministic, side-effect free, non-executable, and returns no public API data.

D22 retains its exact `chat.message` identifier and argument validation before D23 is called. A valid chat command may be delegated only when D23 returns `defer_to_existing_chat`; any rejection fails before `ConversationService` is called. Unsupported D22 commands remain rejected by D22 before D23 evaluation.

The existing `DecisionService` remains explanatory and non-executable, and `ReasoningService` remains unchanged. D23 does not begin D24: it performs no AI/provider selection, Local AI integration, generic routing, execution-plan creation, adapter invocation, tool execution, or autonomous behavior.

This change requires no data or public API migration. Rollback removes the D23 contract, engine, focused tests, D22 integration, and documentation without affecting persisted conversations, Projects, providers, HTTP clients, or frontend behavior.

## ADR-016: Deterministic AI route selection

**Decision**
Add the internal, provider-neutral D24 `AIRouter`, which receives only `CommandDecision` and returns an ephemeral `AIRouteDecision`. It selects a stable logical adapter ID but never instantiates or invokes an AI adapter or provider.

`unspecified` and `automatic` preferences select `chatgpt.default`. An explicit Local AI preference selects only `local_ai.default`; if Local AI is unavailable, the route is `unavailable` and never falls back to ChatGPT. A D23 rejection or malformed decision is rejected fail-closed.

**Consequences**
D22 retains its exact command and argument validation, then calls D23 and D24 before delegating. Only the selected `chatgpt.default` logical route continues through the existing `ConversationService` compatibility path. An unavailable Local AI route, or a selected Local AI route without the future D26 invocation implementation, stops before `ConversationService` and provider calls.

D24 adds no Local AI runtime, provider SDK, selection implementation, adapter invocation, public API change, persistence, execution plan, tool execution, or autonomous behavior. Route decisions are internal and ephemeral. D25/D26 are separately approved future work.

## ADR-017: ChatGPT adapter bridge

**Decision**
Add `ChatGPTAdapter` as the concrete `AIAdapter Contract v1` implementation for the stable `chatgpt.default` ID and contract version `1`. It wraps the existing `OpenAIChatProvider`, translating only `AIRequest.content` to the provider's existing `generate_reply()` call and returning its text as `AIResult.content`.

**Consequences**
Composition now gives `ChatService` the adapter rather than the provider directly. The adapter also exposes the unchanged `generate_reply(str) -> str` compatibility shim, so `ChatService`, `ConversationService`, and the public chat API retain their current behavior. Provider and configuration errors are deliberately not caught or remapped by the adapter, preserving their established handling. This adds no Local AI, registry, generic execution, D26 invocation, provider SDK work, persistence, or public API change.

## ADR-018: Local AI runtime adapter and isolated telemetry

**Decision**
Add a provider-neutral Local AI runtime client contract, an Ollama HTTP implementation, and `LocalAIAdapter` for the stable `local_ai.default` AI Adapter v1 identity. Runtime URL, model, timeout, context, and enablement are deployment configuration; no model-storage path is encoded in O-AI. Add `SystemMetricsProvider` as an isolated, best-effort telemetry boundary using `psutil` and NVIDIA tooling where available.

**Consequences**
The adapter fails closed when Local AI is disabled, offline, missing its configured model, times out, or returns malformed/empty output. It never falls back to cloud AI. Each isolated daemon inference session resets and then retains its own latest and peak CPU/RAM/GPU/VRAM values for a future monitor; its session identity prevents a stopped sampler from writing into a newer inference. ACTIVE is bounded by the generation call; model LOADED remains a separate runtime state. Telemetry failures are swallowed and never affect inference. D24 continues to select only; no registry, generic executor, or chat-path invocation is introduced. Moving Ollama to O-SERVER later changes only deployment configuration.

## ADR-019: Fail-closed Tool/Module route selection

**Decision**
Add `ToolModuleRouter`, which accepts only structured `CommandRequest` and `ExecutionPlan` contracts and returns an ephemeral route decision. It validates request/plan identity, registered adapter identity, supported Tool/Module Adapter Contract v1, and owner-approval state without parsing raw user text or executing an adapter. Add the deterministic, read-only `StandardToolAdapter` with the sole `standard.echo` operation.

**Consequences**
Unknown adapters are unavailable, request/plan mismatches are rejected, and plans requiring owner approval are blocked. Router construction rejects duplicate IDs and unsupported contract versions. The router returns only selection metadata; no chat path, generic executor, autonomous behavior, tool invocation, file/network/process/database action, or D28 capability is introduced. `StandardToolAdapter` can only return a structured echo `Result` for its exact supported plan shape and otherwise fails safely.

## ADR-020: Safe orchestration response composition

**Decision**
Add a pure internal D28 `OrchestrationErrorNormalizer` and `ResponseComposer`. The normalizer classifies terminal D24/D27 route outcomes, known ChatGPT and Local AI exceptions, Tool/Module results, and unexpected exceptions into a fixed safe error taxonomy. The composer independently converts successful AI/Tool results or normalized errors into the existing D21 `Response` and `Result` contracts.

**Consequences**
`blocked` stays distinct from `failed`: owner-approval outcomes retain `Result.status = "blocked"`. Normalized error results retain only a stable error code, never raw exception text or arbitrary adapter error detail. Explicit Local AI failures remain local-only and cannot cause cloud fallback. Both services are deterministic, ephemeral, side-effect free, and exposed through dependency injection only; they do not alter FastAPI exception handlers, public envelopes, D24/D27 routing, adapter invocation, tool execution, or the chat pipeline. Rollback removes these internal services, contracts, tests, and documentation without data or public API migration.

## ADR-021: End-to-end orchestration with selected AI and guarded Tool execution

**Decision**
Add `CommandOrchestrator` as the D29 coordinator for validated chat commands. It obtains a D23 decision, D24 route, and a selected adapter from a DI-composed AI Adapter v1 registry before delegating exactly one turn to `ConversationService`. The selected adapter is passed explicitly per turn, so `ConversationService` retains its existing persistence, context, analysis, and project behavior without shared mutable provider state. Add a separate structured Tool/Module execution lane that invokes only a D27-selected registered adapter.

**Consequences**
The registry rejects duplicate IDs and unsupported contract versions; missing selected adapters fail closed. Local AI becomes route-available only when deployment configuration enables it, while runtime/model checks remain inside `LocalAIAdapter`. Explicit Local AI failure never falls back to ChatGPT. D28 normalizes terminal outcomes before safe API error presentation, preserving the request ID and excluding raw error details.

The existing `/api/v1/chat` endpoint and success response stay intact. No `ExecutionPlan` is created from chat input and normal chat does not execute tools. The guarded tool lane permits only separately supplied structured plans and preserves blocked/unavailable/rejected non-execution. This introduces no autonomous behavior, side-effect tool, data migration, public API schema change, or new deployment dependency.

## ADR-022: Native Windows MVP run path

**Decision**
Establish native Windows as the D30 MVP operational path: FastAPI on `127.0.0.1:8000`, Next.js on `127.0.0.1:3000`, SQLite, and optional Ollama on the configured loopback URL. Bootstrap creates missing local configuration only from examples, provisions existing dependencies, and migrates the configured database. Start, stop, and smoke scripts manage only O-AI-owned local processes.

**Consequences**
The MVP remains trusted single-owner localhost-only with no authentication, LAN/public exposure, new Core capability, Docker redesign, PostgreSQL migration, or O-SERVER work. Local AI remains opt-in, uses deployment configuration without a hard-coded model path, and its explicit route cannot fall back to cloud. Docker is retained as deferred/non-MVP deployment work. Smoke checks exercise the running API and persistence path, including explicit Local AI E2E only when enabled; OpenAI smoke skips when no credentials are configured.

## ADR-023: Unified immutable adapter runtime registry

**Decision**
Introduce D31 `AdapterRegistry` as the single dependency-composed registration and discovery boundary for AI, Tool, and Module Adapter Contract v1 implementations. The registry is an immutable construction-time snapshot: it classifies each supplied adapter against exactly one approved structural contract, validates the matching contract version and a non-empty trimmed stable ID, rejects ambiguous contracts, and enforces globally unique adapter IDs across adapter kinds.

Preserve `AIAdapterRegistry` as a D29 compatibility view over the unified registry and allow `ToolModuleRouter` to use the same registry. Dependency composition registers the configured ChatGPT adapter, Local AI adapter, and standard read-only Tool adapter into one snapshot. D24 route availability remains an independent policy boundary and continues to decide whether Local AI is selectable from deployment configuration.

**Context**
D29 introduced an AI-only registry while D27 kept a separate Tool/Module adapter map inside its router. Those local registries validate similar identity/version rules but leave registration ownership split across runtime boundaries. D31 needs one stable composition seam before future provider/module extensibility without changing the already proven D24 routing, D27 approval guard, or D29 execution behavior.

**Alternatives**
Keep separate registry maps indefinitely, move adapter registration into routers/orchestrators, add dynamic filesystem or Python entry-point discovery now, or combine registration with provider/capability routing.

**Rationale**
A single explicit snapshot removes duplicate registration state and gives future adapters one provider-neutral composition boundary. Keeping discovery limited to registered IDs/kinds makes behavior deterministic and testable, while compatibility views avoid rewriting D29 callers. Separating registration from availability, routing, approval, and invocation prevents a registered adapter from becoming executable merely because it exists in the registry.

**Consequences**
D31 registration never invokes adapters, creates plans, selects providers, grants owner approval, loads external code, scans the filesystem, performs network/database access, or mutates runtime state after construction. Unknown IDs resolve to `None` and downstream fail-closed behavior remains authoritative. Local AI may be registered while disabled; D24 still reports it unavailable and `LocalAIAdapter` remains responsible for runtime/model validation.

There is no public API/schema, persistence, migration, dependency, frontend, Docker, or deployment change. Rollback restores the D29 AI registry implementation and D27 router-local adapter map, removes the unified registry/tests, and reverts only dependency composition and documentation.

## ADR-024: Registry-backed AI provider routing

**Decision**
Evolve the existing D24 `AIRouter` into a registry-backed, configuration-neutral routing boundary driven by the D31 `AdapterRegistry` and an immutable `AIProviderRoutingPolicy`. Do not introduce a second provider router. Runtime composition uses the unified registry to prove that a candidate ID is a registered AI adapter and uses the routing policy only to decide whether that registered AI ID is enabled and which enabled AI ID is the configured default.

**Context**
D24 established deterministic provider selection from structured command decisions, but availability was supplied as an independent collection of adapter IDs. D31 then introduced a unified adapter registry that distinguishes AI, Tool, and Module adapters and centralizes registration. D32 must connect these boundaries without allowing registration to imply route availability or routing to imply invocation.

**Alternatives**
Keep D24 availability independent from the registry, create a parallel provider router, move provider selection into `CommandOrchestrator`, or combine routing with capability discovery, health probing, retry, or fallback.

**Rationale**
Using `AdapterRegistry.resolve_ai()` makes registered AI identity authoritative while keeping deployment enablement explicit and immutable. This prevents Tool/Module IDs or unknown enabled IDs from becoming AI routes, preserves deterministic D24 decisions, and keeps provider implementation details outside the routing core. Keeping automatic fallback out of D32 avoids hidden changes to privacy, cost, data-boundary, and owner expectations.

**Consequences**
A registered-but-disabled Local AI adapter remains unavailable for routing. An enabled-but-unregistered ID also fails closed. `AIRouter` never invokes an adapter and does not probe models/providers. D29 remains responsible for controlled orchestration/invocation through the selected adapter. Settings remain at the composition root and are translated into `AIProviderRoutingPolicy`; the routing service itself does not import configuration.

The D24 constructor remains as a compatibility surface for existing tests/callers, but application runtime composition uses registry-backed mode. There is no public API/schema, database, migration, frontend, Docker, dependency/package, capability-discovery, execution-planner, approval, or dynamic-plugin change in D32.

## ADR-025: Replaceable Local AI runtime backend

**Decision**
Keep `LocalAIAdapter` provider-neutral and designate `LocalAIRuntimeClient` as the official replaceable Local AI runtime seam. Select the runtime implementation only at the application composition boundary through an immutable `LocalAIAdapterConfig` and a fail-closed `LocalAIRuntimeFactory`. Keep `local_ai.default` as the stable AI adapter identity, independent from runtime backend and model identity.

**Context**
D26 already separated `LocalAIAdapter` from Ollama behind `LocalAIRuntimeClient`, but application dependency composition still instantiated `OllamaRuntimeClient` directly. D31 and D32 subsequently made adapter registration and routing provider-neutral. D33 completes the Local AI replacement boundary without redesigning inference behavior or taking on D34 capability/model discovery.

**Alternatives**
Instantiate Ollama directly in `get_local_ai_adapter`, encode backend/model identity into the AI adapter ID, create one AI adapter per runtime implementation, dynamically discover local runtimes, or silently fall back to Ollama/cloud providers when configuration is invalid.

**Rationale**
A stable `LocalAIAdapter` plus a small runtime protocol keeps routing and orchestration independent from Local AI implementation details. Explicit runtime configuration makes replacement deterministic and testable. Fail-closed selection avoids hidden privacy, cost, and execution-boundary changes. Reusing the same runtime protocol for telemetry preserves the D26 separation between inference and best-effort monitoring.

**Consequences**
Ollama remains the default supported D33 runtime backend, identified by `ollama`, but it is no longer instantiated inside the Local AI adapter dependency itself. A future runtime can satisfy `LocalAIRuntimeClient` and be injected without changing `LocalAIAdapter`, D31 registration, or D32 routing. Unknown backends raise a composition error and do not fall back. D26 runtime/model availability checks and safe error normalization remain unchanged.

D33 does not add model/capability discovery, runtime probing during factory creation, automatic retry/fallback, dynamic plugins, model downloading, database/persistence changes, migrations, public API/schema changes, frontend changes, dependency/package changes, or Docker/deployment changes.

## ADR-026: AI capability and model discovery metadata boundary

**Decision**
Represent AI model and capability discovery as immutable, read-only metadata separate from executable plugin capabilities, routing policy, runtime selection, and execution. Validate discovery sources against the D31 AI registry. Describe the configured model for ChatGPT without network enumeration, and use an optional Local AI model-discovery protocol for runtimes that can enumerate installed models.

**Context**
D31 established a unified immutable adapter registry, D32 separated route enablement from registration, and D33 made the Local AI runtime replaceable behind `LocalAIRuntimeClient`. The repository also has a plugin capability registry, but that registry represents executable plugin capabilities that can be registered, unregistered, and resolved; it is not AI model metadata.

**Alternatives**
Reuse the executable plugin capability registry for AI metadata, query all models from external providers, require every `LocalAIRuntimeClient` to enumerate models, encode capabilities into adapter IDs, infer unsupported capabilities, or let discovery influence routing/fallback.

**Rationale**
A dedicated metadata contract keeps discovery read-only and makes its semantics explicit. Configured-model discovery for ChatGPT avoids unnecessary external calls and avoids implying that every provider-visible model is usable by O-AI. Keeping `LocalAIModelDiscoveryProvider` optional preserves D33 runtime replaceability for generation-only backends. Conservative capability reporting prevents later planning from acting on guessed features.

**Consequences**
D34 can describe registered AI adapters without invoking them. Missing discovery sources and expected runtime failures produce structured unavailable results. Local AI disabled state is reported without runtime probing. Ollama adds read-only deterministic model listing through `/api/tags`; future Local AI runtimes may implement the optional discovery protocol without changing `LocalAIAdapter`. Capability v1 advertises only `text_generation`.

D34 does not add capability-based routing, model switching, model installation/download, execution planning, public discovery APIs, frontend selectors, persistence, migrations, Docker changes, new dependencies, or fallback behavior.

## ADR-027: Deterministic execution planning boundary

**Decision**
Convert validated internal commands and registered/discovered execution resources into immutable proposed `ExecutionPlan` values without authorizing or executing them. Reuse the D21 plan contracts. AI planning reuses D23 decision semantics, D32 routing, D31 registration, and D34 capability/model discovery. Tool and Module planning accepts only explicit structured internal commands and validates adapter kind through the D31 registry.

**Context**
D21 defined `CommandRequest`, `ExecutionStep`, and `ExecutionPlan`; D27 already consumes those plans for guarded Tool/Module routing; D29 coordinates live execution; D31-D34 established registration, AI route enablement, replaceable Local AI runtime composition, and read-only AI capability/model metadata. What is missing is a mechanism that describes what should happen before D36 decides whether execution is authorized.

**Alternatives**
Create a second plan schema, generate plans with an LLM, let the planner execute selected adapters, merge approval into planning, infer Tool/Module intent from free text, add multi-step decomposition immediately, or rewire the live D29 chat path before an execution guard exists.

**Rationale**
A deterministic one-step planner preserves clear ownership boundaries and is easy to test. Reusing the existing D21 plan type avoids contract duplication. Structured Tool/Module commands avoid unsafe free-text interpretation. Keeping live orchestration unchanged prevents D35 from becoming an authorization or runtime milestone. Explicit approval flags describe the required ceremony but do not themselves grant permission.

**Consequences**
D35 v1 emits at most one execution step. AI text generation plans use `owner_approval_required=False`; Tool and Module plans always require owner approval. Route/discovery failures produce structured non-planned outcomes and never trigger fallback. User message content remains in the original command rather than being copied into the plan. D36 must still implement the actual approval and execution guard before planner output is wired into live orchestration.

D35 does not add execution, approval persistence, approval UI, public APIs, frontend behavior, database changes, migrations, Docker changes, new dependencies, model switching, capability discovery, multi-step decomposition, retries, parallelism, or automatic fallback.

## ADR-028: Plan-bound owner approval and execution authorization

**Decision**
Require approval-gated execution to pass through a fail-closed `ExecutionGuard` that revalidates request/plan identity, adapter kind, operation policy, and approval requirements. Bind explicit owner approval evidence to the exact proposed plan using a deterministic SHA-256 digest, then emit a separate immutable `ExecutionAuthorization`. Tool and Module targets always require approval in v1; AI text generation does not require a separate approval ceremony but still passes structural policy checks.

**Context**
D35 can now deterministically propose `ExecutionPlan` values, but plan construction is not authorization. Existing Project action proposal persistence is domain-specific and database-backed, while D36 must provide a provider-neutral core boundary for AI, Tool, and Module execution. D27 and D29 previously allowed an execution-ready raw Tool plan to reach adapter execution, which leaves authorization semantics distributed across callers and plan flags.

**Alternatives**
Trust `owner_approval_required` directly, let callers clear the approval flag, reuse Project proposal database rows as universal authorization tokens, mutate plans in place after approval, bind approval only to request ID, execute directly inside the guard, add signatures/authentication immediately, or defer enforcement until Tool/Module runtime milestones.

**Rationale**
Defense in depth requires the guard to enforce target-kind policy independently from planner output. Binding approval to a canonical digest prevents an approval for Plan A from authorizing a modified Plan B. Materializing a new execution-ready immutable plan preserves the approved proposal and keeps D27 compatibility. Keeping the guard side-effect-free separates authorization from runtime execution.

**Consequences**
Tool and Module plans with `owner_approval_required=False` are rejected rather than trusted. Missing approval blocks; denied approval blocks; mismatched approval rejects. Only authorized Tool execution can enter the D29 execution path. Safe D28 normalization adds owner-denied and authorization-rejected outcomes. The plan digest supports JSON-safe parameters and fails closed for unsupported values.

The digest is not a digital signature and does not authenticate owner identity. D36 does not add approval UI/API, authentication, persistence, database tables, migrations, cross-process replay protection, Module Runtime, Tool Runtime redesign, public schema changes, frontend changes, Docker changes, or new dependencies.

## ADR-029: Authorization-gated Module Runtime

**Decision**
Invoke `ModuleAdapter` implementations only through a dedicated `ModuleRuntime` that accepts D36 `ExecutionAuthorization`, resolves modules exclusively from the D31 `AdapterRegistry`, revalidates execution-ready module plan structure, invokes the selected adapter exactly once, and returns only validated D21 `Result` values.

**Context**
D31 established central adapter registration, D35 creates deterministic plans, and D36 binds owner approval to plans and materializes execution-ready authorization. A Module runtime is now needed, but O-AI already has a separate Plugin subsystem whose contracts and lifecycle differ from `ModuleAdapter`.

**Alternatives**
Execute raw plans directly, let modules bypass D36, add a second Module registry, reuse PluginRuntime as though Plugin and ModuleAdapter were the same contract, add filesystem discovery/dynamic imports now, retry failed modules automatically, or add a Plugin-to-Module bridge in the same milestone.

**Rationale**
Keeping authorization separate from invocation preserves the D35/D36 security boundary. Resolving only registered `ModuleAdapter` objects keeps D31 as the single registration authority. A one-shot runtime is deterministic, easy to test, and establishes the pattern D38 can mirror for Tool execution. Keeping PluginRuntime separate avoids conflating two existing contract families.

**Consequences**
Raw `ExecutionPlan` values cannot invoke ModuleRuntime. Non-authorized, wrong-kind, mismatched, approval-gated, malformed, or unavailable Module executions fail closed without adapter invocation. Valid adapters run exactly once with no retry/fallback. Invalid adapter results and exceptions become safe failed `Result` values. Dynamic module discovery/loading, Plugin bridging, public APIs, UI, DB changes, migrations, observability, and multi-step execution remain out of scope.

## ADR-030: Authorization-gated Tool Runtime

**Decision**
Route authorized Tool execution through a dedicated `ToolRuntime` that accepts D36 `ExecutionAuthorization`, resolves only registered Tool adapters from the D31 `AdapterRegistry`, revalidates execution-ready Tool plan boundaries, invokes the selected adapter exactly once, and returns validated provider-neutral D21 `Result` values. `CommandOrchestrator.execute_tool` delegates authorized execution to this runtime and remains responsible for normalization/response composition.

**Context**
D36 established plan-bound authorization and hardened the Tool boundary against raw plan execution. D37 established an authorization-gated Module runtime. Tool execution still lived inside `CommandOrchestrator` through the older D27 routing mechanism, leaving execution ownership asymmetric.

**Alternatives**
Keep Tool invocation inside the orchestrator, make D27 `ToolModuleRouter` the permanent execution owner, accept raw plans, introduce a second Tool registry, retry failed tools automatically, add Tool discovery/install mechanisms now, or combine Tool and Module runtime into one generic executable runtime.

**Rationale**
A dedicated Tool runtime creates the same security and lifecycle boundary as D37 while preserving Tool-specific adapter typing. D31 remains registration authority, D36 remains authorization authority, and D38 becomes Tool invocation authority. Keeping D27 for compatibility avoids an unnecessary removal/refactor during this milestone.

**Consequences**
Raw `ExecutionPlan` values cannot invoke ToolRuntime. Wrong-kind, non-authorized, mismatched, approval-gated, malformed, or unavailable Tool executions fail closed without adapter invocation. Valid adapters run exactly once with no retry/fallback. `CommandOrchestrator` no longer resolves or invokes Tool adapters directly. Public APIs, UI, databases, migrations, dynamic Tool loading, observability, and multi-step execution remain out of scope.

## ADR-031: Safe non-authoritative execution audit trail

**Decision**
Record allowlisted planning, authorization, and execution metadata through an immutable execution-audit contract and pluggable `AuditSink`. D35 `ExecutionPlanner`, D36 `ExecutionGuard`, D37 `ModuleRuntime`, and D38 `ToolRuntime` emit observations at the layer that owns each action. Audit recording is non-authoritative and all sink failures are isolated from business execution.

**Context**
D35-D38 established deterministic planning, plan-bound authorization, and dedicated Module/Tool execution owners. D39 needs visibility into those decisions and executions without weakening the authorization boundary, duplicating execution ownership, or leaking request/adapter payloads. A durable compliance store has not yet been selected and would prematurely couple Core behavior to persistence.

**Alternatives**
Log arbitrary objects or payloads, place all audit generation in `CommandOrchestrator`, make successful audit recording mandatory for execution, write directly to the application database, add a migration now, expose raw adapter exceptions, add OpenTelemetry or a remote collector dependency, or postpone all observability until after D40.

**Rationale**
An allowlisted event contract creates a stable privacy boundary. Layer-local instrumentation avoids duplicate or misleading events. A pluggable sink keeps Core independent from the final storage/telemetry backend. Fail-open observation preserves the D35-D38 business and security semantics: audit system availability cannot authorize, deny, retry, or duplicate execution.

**Consequences**
Operational logs can observe planning, authorization, and Tool/Module execution without storing prompts, arguments, step parameters, outputs, or raw exceptions. `LoggingAuditSink` and `InMemoryAuditSink` are available in v1. Audit delivery is best-effort and is not durable, exactly-once, tamper-evident, cryptographically signed, cross-process ordered, or compliance-grade. Database persistence, retention, dashboards, public audit APIs, distributed tracing, and D40 live-pipeline integration remain out of scope.
