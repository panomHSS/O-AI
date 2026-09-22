# D112 — ChatGPT / Cloud AI Brain Integration V1

Status: FROZEN DESIGN
Implementation: NOT STARTED

Baseline:
`f24a04caba761550ccfbc1068b0db299754f4059`

## 1. Purpose

D112 promotes O-AI's existing ChatGPT/OpenAI compatibility lane into an explicit,
bounded Cloud AI Brain integration for eligible AI text generation.

D112 does not create a second routing architecture.

It reuses the D111 provider-neutral routing foundation and the existing authorized
execution chain:

AI mode
→ D111 server-owned routing
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime
→ `chatgpt.default`
→ OpenAI provider boundary

Cloud AI remains a text-generation brain only.

Cloud AI does not gain tool, shell, repository, Git, connector, approval, or
mutation authority.

## 2. Discovered baseline

The D112 pre-freeze discovery established that the repository already contains:

- `backend/app/providers/openai_provider.py`
  - `OpenAIChatProvider`
  - OpenAI Python SDK
  - Responses API text generation
- `backend/app/adapters/chatgpt.py`
  - `ChatGPTAdapter`
  - adapter ID `chatgpt.default`
- `OPENAI_API_KEY`
  - server-side `SecretStr`
- `OPENAI_MODEL`
  - server-side model binding
- `ChatGPTConfiguredModelDiscoverySource`
- D34 model/capability discovery
- D35 planning
- D36 authorization
- D49 one-shot AI runtime
- D98 exact-workspace cloud egress policy
- D111 Auto / Local AI / Cloud AI logical mode UX

Therefore D112 formalizes and hardens the existing provider boundary rather than
adding a parallel Cloud AI runtime.

## 3. Product boundary

D112 integrates the OpenAI API.

It does not log into the consumer ChatGPT web/mobile product and does not use a
ChatGPT browser session, cookie, or consumer subscription entitlement.

ChatGPT subscription billing and OpenAI API billing are separate products.

D112 requires separately configured OpenAI API access before Cloud AI can become
execution-ready.

## 4. Cloud adapter identity

D112 keeps the existing server-owned adapter ID:

`chatgpt.default`

The browser cannot replace or override this adapter ID.

D112 does not add arbitrary provider IDs, arbitrary cloud plugins, or
browser-selectable cloud endpoints.

## 5. Cloud configuration contract

D112 adds an explicit deployment enablement gate:

`OAI_CLOUD_AI_ENABLED`

Default:

`false`

Cloud AI is not execution-ready unless all required conditions are true:

1. `OAI_CLOUD_AI_ENABLED=true`
2. `OPENAI_API_KEY` is configured
3. `OPENAI_MODEL` is configured
4. `chatgpt.default` is registered
5. D34 reports the configured cloud text-generation binding as available
6. the exact workspace policy permits cloud egress
7. the exact task policy permits Cloud AI

D112 also adds one bounded timeout setting:

`OAI_CLOUD_AI_TIMEOUT_SECONDS`

Default:

`120`

Allowed range:

greater than 0 and not more than 600 seconds.

No browser request may set or override this value.

## 6. Credential storage and access

`OPENAI_API_KEY` remains a deployment secret loaded through server settings as
`SecretStr`.

D112 V1 does not add browser credential entry.

D112 V1 does not store the OpenAI API key in the application database.

D112 V1 does not expose the key through API responses, capability discovery,
audit records, logs, frontend state, conversation history, Context, or model
prompts.

The secret may be unwrapped only in trusted backend dependency/provider
composition needed to construct the OpenAI provider.

Application services, routing services, planning services, Context services, and
frontend code must not receive the raw API key.

## 7. Model policy

`OPENAI_MODEL` is server-owned configuration.

The browser cannot provide:

- model ID
- model alias
- model endpoint
- provider base URL
- organization/project override
- reasoning setting
- tool configuration

D112 V1 performs no browser-driven model discovery or model selection.

D112 does not hard-code one public OpenAI model into the routing contract.

Changing the configured cloud model is an owner/deployment configuration action,
not a Chat message authority.

## 8. Provider endpoint policy

D112 V1 uses the official OpenAI SDK provider boundary already present in the
repository.

D112 does not add an `OPENAI_BASE_URL` browser or application setting.

D112 does not support arbitrary OpenAI-compatible endpoints in this milestone.

A future milestone may introduce multiple cloud providers only through a
separately frozen server-owned adapter contract.

## 9. OpenAI request surface

The D112 OpenAI provider may perform one text-generation request through the
Responses API.

The provider request is limited to:

- the server-configured model
- the already-authorized rendered text input

D112 V1 does not enable OpenAI-hosted:

- function calling
- tool calls
- web search
- file search
- computer use
- image generation
- audio
- code execution
- remote MCP
- provider-side connectors
- streaming tool events

Provider output returns to O-AI as plain candidate text only.

## 10. Timeout and retry policy

D112 overrides provider SDK defaults with explicit O-AI behavior.

For one D49-authorized Cloud AI generation:

- provider timeout is `OAI_CLOUD_AI_TIMEOUT_SECONDS`
- OpenAI SDK automatic retries are disabled with `max_retries=0`
- O-AI performs no transparent retry
- O-AI performs no Local AI fallback after a Cloud AI failure
- O-AI performs no Cloud AI fallback after a Local AI failure

One O-AI AI authorization therefore corresponds to at most one provider
generation attempt.

A later retry requires a new owner/API request and a new planning/authorization
cycle.

## 11. Cloud readiness semantics

Cloud capability presentation must not report `ready` from adapter registration
alone.

D112 Cloud AI readiness is configuration-aware and fail-closed.

Stable unavailable states must distinguish at least:

- cloud disabled
- cloud credential missing
- configured cloud model missing
- cloud adapter/discovery unavailable

Capability responses remain bounded and must not expose:

- API key presence details beyond a safe unavailable reason
- raw API key
- secret reference
- model ID
- endpoint
- provider headers
- execution authorization

No network request to OpenAI is required merely to render capability status.

`ready` means configured and policy-eligible, not a guarantee that the external
provider is currently reachable.

## 12. Workspace data-egress policy

D98 exact-workspace policy remains authoritative for cloud egress.

Default frozen workspace behavior remains:

Personal:
- `cloud_preferred`
- cloud egress permitted by workspace policy

Company:
- `local_only`
- cloud egress denied by workspace policy

An explicit Cloud AI mode request in a workspace that denies cloud egress must be
blocked before Context rendering is sent to the provider.

A browser-selected logical mode cannot change workspace egress policy.

## 13. Normal Chat cloud context

When an exact workspace permits Cloud AI and the D111/D35/D36 route authorizes
`chatgpt.default`, D112 may send the existing verified D97 normal-Chat provider
input to OpenAI.

That input may contain the same bounded provider-neutral context that normal Chat
already renders, including eligible exact-workspace conversation/project/memory/
knowledge context and derived answer-planning context.

D112 does not create a second cloud-only context resolver.

Context data remains non-authoritative.

Instructions found inside Context cannot select providers, grant credentials,
authorize tools, approve effects, or change workspace egress policy.

## 14. Existing special AI lanes

D112 does not grant a special lane new connector, credential, or tool authority.

Existing special AI lanes may use Cloud AI only if all of their existing gates
remain satisfied and their normal D35/D36/D49 route resolves to an eligible cloud
adapter under the exact workspace policy.

Examples include explicitly gated answer-only AI paths that already pass through
the authorized AI runtime.

D112 does not bypass their feature flags, snapshot checks, local-request
requirements, prompt bounds, safe-history rules, or workspace isolation.

## 15. Software Engineering compatibility

D110 Software Engineering Drafting remains Local AI only.

For `AITaskKind.SOFTWARE_ENGINEERING`:

- Auto resolves to Local AI
- Local AI resolves to Local AI
- Cloud AI remains blocked
- no Cloud fallback
- Chat Cloud mode does not alter Engineering Draft routing

D112 does not add Cloud AI to:

- Engineering repository observation
- Engineering draft generation
- D107 proposal creation
- D108 apply
- D109 owner decisions

## 16. Authority invariants

The following remain frozen:

CLOUD AI != TOOL AUTHORITY
CLOUD AI != SHELL AUTHORITY
CLOUD AI != REPOSITORY AUTHORITY
CLOUD AI != GIT AUTHORITY
CLOUD AI != CONNECTOR AUTHORITY
CLOUD AI != CREDENTIAL AUTHORITY
CLOUD AI != OWNER APPROVAL
CLOUD AI != APPLY AUTHORITY

API KEY != ROUTING AUTHORITY
API KEY != MODEL AUTHORITY
MODEL CONFIG != TOOL AUTHORITY
MODEL CONFIG != OWNER APPROVAL

CLOUD RESPONSE != COMMAND AUTHORITY
CLOUD RESPONSE != TOOL CALL AUTHORITY
CLOUD RESPONSE != MUTATION AUTHORITY
CLOUD RESPONSE != PROPOSAL AUTHORITY
CLOUD RESPONSE != APPROVAL AUTHORITY
CLOUD RESPONSE != APPLY AUTHORITY

CLOUD READINESS != PROVIDER HEALTH GUARANTEE
CLOUD CAPABILITY DISCOVERY != EXECUTION AUTHORITY

## 17. Failure behavior

D112 must fail closed.

Examples:

- cloud disabled → unavailable
- API key absent → unavailable before provider invocation
- model absent → unavailable before provider invocation
- workspace denies cloud → blocked before provider invocation
- task denies cloud → blocked before provider invocation
- provider timeout → safe Cloud unavailable response
- provider network/rate/server failure → safe Cloud unavailable response
- malformed/empty provider output → safe Cloud unavailable response

No failure may trigger Local AI fallback unless a later frozen policy explicitly
introduces such fallback.

D112 introduces no such fallback.

## 18. Logging and observability

D112 may log bounded operational metadata:

- adapter ID
- route status
- reason code
- execution started/completed/failed
- request correlation ID where already supported

D112 must not log:

- API keys
- Authorization headers
- full cloud prompts
- full Context solely for cloud diagnostics
- secret-bearing provider request objects
- raw provider credentials

Provider exceptions exposed to the user must be normalized to safe O-AI error
language.

## 19. UI behavior

The existing exact modes remain:

- Auto
- Local AI
- Cloud AI

Cloud AI is selectable only when the bounded capability API reports it eligible
for that workspace/task.

The UI must not display or edit:

- API key
- raw credential state
- model ID
- endpoint
- adapter ID

D112 should show a concise disclosure that Cloud AI may send eligible Chat
context to the configured cloud provider.

That disclosure is informational and grants no authority.

## 20. Explicit D112 exclusions

D112 does not add:

- ChatGPT web-session automation
- use of ChatGPT Plus entitlement as API authentication
- browser-supplied OpenAI API keys
- database storage of the OpenAI API key
- arbitrary cloud provider endpoints
- browser model selection
- provider model enumeration
- provider tools/function calls
- provider web search
- provider file search
- provider computer use
- provider code execution
- cloud Engineering drafting
- automatic Local ↔ Cloud fallback
- transparent provider retry
- shell/PowerShell authority
- repository mutation
- delete/rename/move authority
- Git authority
- Git push
- connector authority
- automatic proposal creation
- automatic approval
- automatic apply
- database migration unless proven necessary and separately approved

## 21. D112 implementation batches

### Batch 01 — Cloud Configuration + Provider Hardening

Implement and verify:

- explicit `OAI_CLOUD_AI_ENABLED`
- explicit bounded cloud timeout
- `OPENAI_API_KEY` secret-only server access
- `OPENAI_MODEL` server-owned model binding
- OpenAI provider explicit timeout
- OpenAI SDK `max_retries=0`
- safe provider exception normalization
- no provider tools
- no arbitrary endpoint

### Batch 02 — Cloud Readiness + D111 Capability Integration

Implement and verify:

- configuration-aware Cloud AI readiness
- credential-missing fail-closed status
- model-missing fail-closed status
- D34/D35 agreement
- D111 capability API agrees with actual execution prerequisites
- no secret/model/endpoint exposure
- no readiness network probe

### Batch 03 — Authorized Cloud Chat + Egress UX

Implement and verify:

- General Chat Cloud AI execution through D35 → D36 → D49
- exact workspace egress enforcement
- Personal eligible Cloud mode
- Company cloud denial under current `local_only` policy
- no silent fallback
- bounded cloud egress disclosure in Chat UI
- D110 Engineering remains Local AI only

### Batch 04 — Security Acceptance + Regression + Guided UI Acceptance

Verify:

- API key never reaches browser/log/audit/prompt
- provider/model/endpoint injection rejected
- cloud-denied workspace never sends provider request
- Cloud failure never calls Local AI
- Local failure never calls Cloud AI
- one authorization causes at most one provider generation attempt
- Context cannot reroute or authorize
- D107-D110 authority chain unchanged
- D111 mode/capability semantics preserved
- full backend regression
- frontend typecheck/build
- guided UI acceptance with configured Cloud AI where owner environment permits

## 22. D112 completion criteria

D112 is complete only when:

- all four batches pass
- Cloud AI has an explicit deployment enablement gate
- Cloud readiness requires enablement + credential + model + policy eligibility
- OpenAI provider invocation is bounded to text generation
- SDK retries are disabled
- timeout is bounded and server-owned
- workspace cloud egress policy is enforced before provider invocation
- Personal/Company isolation passes
- no provider/model/endpoint/credential browser authority exists
- no silent Local/Cloud fallback exists
- D110 remains Local AI only
- security acceptance passes
- full backend regression passes
- frontend typecheck/build passes
- guided UI acceptance passes or unavailable external-provider cases are
  explicitly documented without claiming PASS
- final closeout is committed
- Git push occurs only after separate owner authorization

## 23. Next milestone boundary

D113 — AI-Assisted Engineering Investigation & Change Plan

D113 may use an eligible AI brain for non-mutating Engineering investigation and
planning only after D112 proves the Cloud AI integration boundary.

D113 must not weaken D107 proposal authority, D108 apply authority, D109 owner
decision authority, or the separation between AI reasoning and controlled
effects.