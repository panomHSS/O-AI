# D111 — AI Brain & Provider Routing Foundation V1

Status: FROZEN DESIGN
Implementation: NOT STARTED

## 1. Purpose

D111 introduces the provider-neutral AI brain routing foundation for O-AI.

D111 does not add an OpenAI / ChatGPT cloud adapter. Cloud execution is reserved for D112.

D111 establishes the contracts and server-owned routing policy required so future tasks can request one of these user-facing AI modes:

- Auto
- Local AI
- Cloud AI

The selected mode is a routing preference, not provider authority, model authority, tool authority, repository authority, approval authority, or apply authority.

## 2. Frozen roadmap

- D110 — AI-Assisted Engineering Drafting — COMPLETE
- D111 — AI Brain & Provider Routing Foundation V1
- D112 — ChatGPT / Cloud AI Brain Integration V1
- D113 — AI-Assisted Engineering Investigation & Change Plan
- D114 — Controlled Multi-File Proposal Bundle
- D115 — Engineering Validation / Test Assistance
- D116 — Read-Only Git Awareness
- D117 — Controlled Git Workflow

## 3. Core architectural principle

AI thinks.
O-AI routes, checks policy, binds identity, and controls authority.
The owner authorizes controlled effects.

Brain selection must remain separate from mutation authority.

## 4. User-facing routing modes

D111 defines exactly three logical modes:

### AUTO

The owner allows O-AI to choose an eligible AI class according to the server-owned task policy.

AUTO does not mean unrestricted fallback.

Every task kind has an explicit allowed-provider-class policy and fallback policy.

### LOCAL_AI

The owner requests Local AI.

The server may resolve this only to an authorized Local AI adapter.

The browser cannot choose an arbitrary local endpoint, provider ID, model ID, or execution backend.

### CLOUD_AI

The owner requests Cloud AI.

D111 recognizes the mode and its policy contract but does not provide a Cloud AI execution adapter.

Until D112 is complete, a task requiring CLOUD_AI must fail closed with a stable unavailable/not-enabled outcome unless an already-authorized existing cloud lane is explicitly preserved by a task-specific compatibility rule.

D111 must not silently route a CLOUD_AI request to Local AI.

## 5. Provider classes

D111 defines provider classes, not arbitrary client-selected providers:

- local_ai
- cloud_ai

Specific adapter IDs are server-owned.

The browser may never supply:

- provider ID
- adapter ID
- model ID
- base URL
- API endpoint
- API key
- credential reference
- fallback target
- authority token
- tool executor

## 6. Routing decision contract

A routing decision must be a server-generated value object with enough information to explain and enforce the route.

Logical fields:

- contract_version
- task_kind
- requested_mode
- effective_provider_class
- effective_adapter_id
- route_status
- reason_code
- fallback_allowed

`effective_adapter_id` may be null when no executable adapter is available.

`route_status` is a bounded server-defined enum such as:

- ready
- unavailable
- blocked

The exact code representation may use equivalent stable enum names.

The routing result is not an execution result and is not authority to perform tools or mutations.

## 7. Task-aware routing policy

Routing must remain task-aware.

D111 extends the existing D105/D35 task-aware planning/routing structure rather than introducing an independent provider router that bypasses it.

Each task kind must define:

- allowed provider class or classes
- default provider class for AUTO
- whether fallback is allowed
- whether a requested mode is supported
- the authorized adapter mapping

No task may inherit unrestricted Local/Cloud interchangeability by default.

## 8. D110 compatibility rule

D110 Software Engineering Drafting remains frozen as Local AI only.

For the D110 drafting task:

- AUTO resolves to Local AI
- LOCAL_AI resolves to Local AI
- CLOUD_AI is blocked/unavailable for this task in D111
- no Cloud fallback
- no Local-to-Cloud fallback
- no Cloud-to-Local silent fallback

Existing D110 API authority and browser request shape must remain unchanged unless a later explicitly frozen milestone changes it.

D110 continues to use the existing D36/D49 authorization-gated Local AI runtime.

## 9. D36 / D49 execution boundary

D111 does not create a new generic AI execution bypass.

All executable AI routes must continue through the existing authorized runtime boundary or an explicitly authorized future runtime introduced by a later milestone.

Routing selection alone must never execute a provider.

Provider routing and provider execution are separate responsibilities.

## 10. Browser authority boundary

The browser may express a logical mode preference only where an API explicitly permits it.

Browser input must not become routing authority.

The server owns:

- workspace identity
- conversation binding
- task classification
- provider eligibility
- adapter selection
- model selection policy
- fallback policy
- credentials
- execution authorization

A browser-supplied mode must be validated against the server task policy.

## 11. Workspace and conversation isolation

Any mode preference or routing request tied to a conversation must remain bound to the exact server-verified workspace and conversation.

No routing preference or route result may cross workspace authority boundaries.

No route result may be reused as a capability token.

## 12. Capability discovery

D111 may expose a read-only capability description for UI presentation.

If implemented, it must be server-derived and non-authoritative.

Logical capability information may include:

- supported logical modes
- whether Local AI is available
- whether Cloud AI is enabled
- task-specific mode availability
- stable reason codes

Capability discovery must not expose secrets, raw credentials, arbitrary endpoints, or internal security tokens.

A capability response is informational only.

## 13. Failure semantics

Routing must fail closed.

Examples:

- requested Local AI but Local AI unavailable -> unavailable
- requested Cloud AI before D112 -> unavailable/blocked
- requested mode not permitted for task -> blocked
- no authorized adapter for resolved provider class -> unavailable
- invalid or client-injected provider/model fields -> rejected at schema boundary

No silent provider switching is allowed unless the task policy explicitly allows fallback.

## 14. Logging / observability

D111 may record bounded routing metadata for diagnostics:

- task kind
- requested mode
- effective provider class
- effective adapter ID
- reason code
- route status

It must not log:

- API keys
- credentials
- secret headers
- full sensitive prompts merely for routing telemetry

D111 adds no durable prompt archive requirement.

## 15. No authority escalation

The following invariants are frozen:

AI MODE != PROVIDER AUTHORITY
AI MODE != MODEL AUTHORITY
AI MODE != TOOL AUTHORITY
AI MODE != SHELL AUTHORITY
AI MODE != GIT AUTHORITY
AI MODE != REPOSITORY AUTHORITY
AI MODE != OWNER APPROVAL
AI MODE != APPLY AUTHORITY

ROUTING DECISION != EXECUTION AUTHORITY
ROUTING DECISION != TOOL AUTHORITY
ROUTING DECISION != MUTATION AUTHORITY
ROUTING DECISION != APPROVAL AUTHORITY
ROUTING DECISION != APPLY AUTHORITY

PROVIDER CLASS != CREDENTIAL AUTHORITY
PROVIDER CLASS != MODEL AUTHORITY
BROWSER MODE PREFERENCE != SERVER ROUTING POLICY
CAPABILITY DISCOVERY != CAPABILITY TOKEN

## 16. Explicit D111 exclusions

D111 does not add:

- OpenAI / ChatGPT API execution
- Cloud AI credentials
- Cloud AI model selection
- arbitrary provider plugins
- arbitrary model IDs from browser input
- arbitrary provider endpoints
- browser-supplied API keys
- cloud fallback for D110 Engineering Drafting
- direct shell execution
- PowerShell execution authority
- generic process execution
- repository mutation
- delete / rename / move
- Git mutation
- Git push
- credential tools
- email/calendar/tool execution
- automatic proposal creation
- automatic approval
- automatic apply
- changes to D107 proposal authority
- changes to D108 apply authority
- changes to D109 structured Engineering decisions
- changes to D110 draft authority
- database migration unless separately proven necessary and explicitly added before implementation

## 17. Compatibility requirements

D111 must preserve:

- existing general Chat behavior unless explicitly covered by a D111 task policy
- D105 task-aware routing semantics
- D35 planner compatibility
- D36 authorization guard
- D49 AI runtime boundary
- D89 read-only frontend client tail
- D106 repository observation authority
- D107 proposal authority
- D108 apply authority
- D109 Engineering owner workflow
- D110 Local-AI-only Engineering drafting

Legacy test doubles that implement the pre-D111 routing signature must remain compatible where practical, especially general-chat paths.

## 18. D111 implementation batches

### Batch 01 — Routing Contract + Policy Foundation

Implement:

- logical AI mode enum
- provider-class enum
- route status / reason-code contract
- task-aware server routing policy
- provider capability registry abstraction
- compatibility with existing planner/router behavior

No cloud execution.

### Batch 02 — Runtime Integration + Fail-Closed Semantics

Integrate routing decision with authorized AI execution boundaries.

Verify:

- Local AI route remains authorized
- Cloud route has no executable adapter in D111
- unavailable/blocked outcomes are stable
- no silent fallback
- D110 stays Local AI only

No UI requirement yet.

### Batch 03 — Capability API + AI Mode UX Foundation

Add only the bounded UI/API surface needed to present and request logical mode preferences.

Rules:

- browser can request only Auto / Local AI / Cloud AI
- browser cannot choose provider/model/endpoint/credential
- unsupported modes are visibly unavailable or fail closed
- D110 Engineering Draft remains Local AI only
- no Cloud AI execution in D111

### Batch 04 — Security Acceptance + Regression + Guided UI Acceptance

Verify:

- mode preference cannot escalate authority
- provider/model injection rejected
- workspace/conversation isolation
- Local AI unavailable behavior
- Cloud AI unavailable/blocked behavior before D112
- D110 authority chain unchanged
- full D105-D110 security regression
- frontend typecheck/build
- full backend regression
- guided UI acceptance for mode presentation and isolation

## 19. D111 completion criteria

D111 is complete only when:

- all four batches pass
- the routing contract is server-owned and task-aware
- Auto / Local AI / Cloud AI are represented as logical modes
- Local AI remains executable through the existing authorized runtime
- Cloud AI remains non-executable in D111
- no silent fallback exists outside explicit task policy
- D110 remains Local AI only
- browser cannot inject provider/model/endpoint/credential authority
- workspace and conversation isolation pass
- security regression passes
- frontend build/typecheck passes
- full backend regression passes
- guided UI acceptance passes
- final closeout is committed
- Git push occurs only after separate owner authorization

## 20. Next milestone boundary

D112 — ChatGPT / Cloud AI Brain Integration V1

D112 may add a real Cloud AI adapter only after D111 has proven the provider-neutral routing and authority boundary.

D112 must separately freeze:

- OpenAI / ChatGPT integration method
- credential storage and access
- cloud context policy
- data egress rules
- cloud model policy
- timeout/retry behavior
- no-secret logging
- availability/fallback semantics
- task eligibility
- security acceptance
