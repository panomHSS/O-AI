# D111 Final Closeout — AI Brain & Provider Routing Foundation V1

Status: COMPLETE

## Scope

D111 adds the provider-neutral AI brain routing foundation for O-AI.

The user-facing logical modes are:

- Auto
- Local AI
- Cloud AI

These modes express bounded routing preference only.

AI mode does not grant provider authority, model authority, tool authority, shell authority, repository authority, owner approval, apply authority, or credential authority.

D111 does not introduce a new ChatGPT / OpenAI cloud execution adapter. Real Cloud AI integration remains the D112 boundary.

## Final architecture

D111 preserves the core authority model:

AI thinks.
O-AI routes, checks policy, binds workspace/conversation identity, and controls authority.
The owner authorizes controlled effects.

Routing selection remains separate from execution authority.

Executable AI work still passes through the existing authorized planning / guard / runtime chain:

AIRouter
→ D35 ExecutionPlanner
→ D36 ExecutionGuard
→ D49 AIRuntime

A routing decision alone is not execution authority.

## Final routing contract

D111 defines exactly three logical modes:

- `auto`
- `local_ai`
- `cloud_ai`

D111 defines exactly two provider classes:

- `local_ai`
- `cloud_ai`

The browser may request only the logical mode where the API permits it.

The browser cannot provide:

- provider ID
- adapter ID
- model ID
- base URL
- API endpoint
- API key
- credential reference
- fallback target
- execution token
- tool executor

The server owns task classification, provider eligibility, adapter selection, model policy, fallback policy, credentials, workspace binding, conversation binding, and execution authorization.

## Task-aware behavior

General Chat:

- Auto follows the exact server-owned workspace/task policy.
- Local AI may resolve only to the authorized Local AI adapter when execution-ready.
- Cloud AI may use only an already-authorized compatibility lane when execution-ready.
- No D111 cloud adapter or credential path was added.
- No silent Local ↔ Cloud fallback was added.

Software Engineering:

- Auto resolves to Local AI.
- Local AI resolves to Local AI.
- Cloud AI is blocked in D111.
- D110 Engineering Draft remains Local AI only.
- Chat AI mode does not alter Engineering Draft routing.

## Capability presentation

D111 exposes a bounded, read-only workspace capability API for UI presentation.

The capability response exposes only logical mode, bounded status, provider class, reason code, and fallback flag.

It does not expose adapter ID, model ID, endpoint, API key, credential, execution authorization, or mutation authority.

Guided acceptance found one presentation defect:

- Cloud AI initially displayed `ready` from routing-policy enablement even though execution discovery was unavailable.

This was repaired in commit:

- `51a45ff8934d5c8b32ebc3ebdb93eddaf9b273ef`
  - capability presentation now intersects routing eligibility with the existing D34 execution discovery boundary
  - unavailable Cloud does not silently fall back to Local
  - browser authority remains unchanged

After the repair, UI capability status matches the same execution-discovery shape required by the planner.

## Frozen authority boundaries preserved

- AI MODE != PROVIDER AUTHORITY
- AI MODE != MODEL AUTHORITY
- AI MODE != TOOL AUTHORITY
- AI MODE != SHELL AUTHORITY
- AI MODE != GIT AUTHORITY
- AI MODE != REPOSITORY AUTHORITY
- AI MODE != OWNER APPROVAL
- AI MODE != APPLY AUTHORITY
- ROUTING DECISION != EXECUTION AUTHORITY
- ROUTING DECISION != TOOL AUTHORITY
- ROUTING DECISION != MUTATION AUTHORITY
- ROUTING DECISION != APPROVAL AUTHORITY
- ROUTING DECISION != APPLY AUTHORITY
- PROVIDER CLASS != CREDENTIAL AUTHORITY
- PROVIDER CLASS != MODEL AUTHORITY
- BROWSER MODE PREFERENCE != SERVER ROUTING POLICY
- CAPABILITY DISCOVERY != CAPABILITY TOKEN

D107 proposal authority, D108 apply authority, D109 structured Engineering decisions, and D110 non-authoritative Local AI drafting remain unchanged.

## Explicit exclusions preserved

D111 does not add:

- a new OpenAI / ChatGPT cloud adapter
- Cloud AI credentials
- browser-selected cloud models
- arbitrary provider plugins
- arbitrary provider endpoints
- browser-supplied API keys
- unrestricted provider fallback
- Cloud fallback for D110 Engineering Draft
- shell or PowerShell execution authority
- generic process execution
- repository mutation authority
- delete / rename / move authority
- Git mutation or Git push authority
- credential tools
- automatic proposal creation
- automatic owner approval
- automatic apply
- changes to D107-D110 authority
- database migration

## Batch completion

D111 Frozen Design / Implementation Spec:

- commit `02659a1f5fba0f191c43517db8d72ca1f2cc02d5`

D111 Batch 01 — Routing Contract + Policy Foundation:

- commit `62ea85dd877cfb87863c895994f9dd00a17db7af`

D111 Batch 02 — Runtime Integration + Fail-Closed Semantics:

- commit `e09e265635faa17fc57fb8230e419f17779da1ca`

D111 Batch 03 — Capability API + AI Mode UX Foundation:

- commit `434d6ced15c7863332ff3a55bc70bf30d5cd8583`

Guided UI acceptance repair — capability readiness aligned with D34 discovery:

- commit `51a45ff8934d5c8b32ebc3ebdb93eddaf9b273ef`

D111 Batch 04 — Security Acceptance + Regression + Guided UI Acceptance:

- final automated acceptance executed read-only on commit `51a45ff8934d5c8b32ebc3ebdb93eddaf9b273ef`
- no Batch 04 source commit was created before this final closeout
- no Git push occurred

## Final automated acceptance

Final automated acceptance on commit `51a45ff8934d5c8b32ebc3ebdb93eddaf9b273ef` verified:

- pytest temp permission issue isolated with dedicated basetemp
- D111 security acceptance passed
- mode preference grants no provider/model/tool authority
- provider/model/endpoint/credential injection fails closed
- workspace routing isolation passed
- Local unavailable fails closed with no Cloud fallback
- Cloud capability readiness matches D34 execution discovery
- Software Engineering Cloud mode remains blocked in D111
- D110 Engineering Draft remains Local AI only
- D111 targeted regression passed
- full backend regression passed
- frontend typecheck/build passed
- working tree clean
- dedicated pytest basetemp cleaned

The final acceptance run made no source change, no commit, and no Git push.

## Guided UI Acceptance

Observed on the final repair baseline:

- Personal workspace loaded Chat AI mode capability state.
- Company workspace loaded its own workspace-bound capability state.
- Switching Company → Personal restored the Personal workspace binding and capability presentation.
- unavailable logical modes were disabled in the selector.
- current runtime reported Auto unavailable, Local AI unavailable, and Cloud AI unavailable.
- deterministic `/status` created a valid Personal conversation without invoking Local AI or Cloud AI.
- after a valid conversation existed, Engineering owner workflow opened correctly.
- Engineering displayed `Draft with Local AI`.
- Engineering displayed Local AI draft output as non-authoritative.
- Engineering kept proposal creation separate from AI drafting.
- no Cloud AI selection was exposed for Engineering Draft.
- Engineering remained bound to the exact active workspace/conversation.

Not exercised in guided UI acceptance because the corresponding runtime providers were unavailable:

- successful Local AI Chat generation
- successful Cloud AI Chat generation
- live Chat mode switching between executable Local and Cloud providers
- live confirmation that changing an executable Chat provider leaves Engineering routing unchanged

Those unavailable-runtime cases remain covered by automated routing, planner, security, frontend-source, and D110 compatibility regression.

## Acceptance operational notes

During guided acceptance:

- the Next.js development cache became inconsistent after build/dev-server overlap and was cleared by deleting only generated `frontend/.next`
- backend runtime was restarted without source changes
- pytest temporary-directory permission failure was isolated with dedicated writable `--basetemp`
- `Open Engineering` was initially observed before a conversation existed; the panel body intentionally requires an exact existing conversation
- a deterministic D81 `/status` turn was used to create that conversation without AI provider execution

These recovery and observation steps did not change the D111 authority boundary.

## Final D111 status

D111 AI Brain & Provider Routing Foundation V1 is COMPLETE.

D112 — ChatGPT / Cloud AI Brain Integration V1 — is the next milestone boundary.

D112 must separately freeze cloud integration method, credentials, cloud-context/data-egress policy, model policy, timeout/retry behavior, secret-safe logging, task eligibility, fallback semantics, and security acceptance.

No Git push is part of this closeout record unless separately authorized by the owner.