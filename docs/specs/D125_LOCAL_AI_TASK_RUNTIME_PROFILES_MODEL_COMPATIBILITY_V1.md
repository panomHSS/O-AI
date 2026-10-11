# D125 — Local AI Task Runtime Profiles & Model Compatibility V1

Status: DESIGN FROZEN

Baseline: D124 remote-frozen main at
`9216fae36d30bab12fa815c10cc3a2686f7c8612`

## Purpose

D125 introduces exact server-owned Local AI task runtime profiles for the
existing D104 AI task kinds.

The milestone allows O-AI to bind a Local AI generation to an exact configured
model and runtime behavior appropriate to the server-derived task while
preserving all existing routing, authorization, workspace, and execution
boundaries.

D125 specifically addresses the operational class exposed during D123
acceptance where a reasoning-capable model could consume generation budget in
reasoning behavior and leave no usable visible response for an Engineering
draft.

D125 does not grant model-selection authority to the browser, user prompt, AI
output, Skill metadata, Tool, Module, Plugin, or connector.

## Existing boundaries preserved

D125 preserves:

- D31 Adapter Registry;
- D34 model/capability discovery;
- D35 Execution Planning;
- D36 Execution Authorization;
- D39/D47 execution audit;
- D49 AI Runtime one-shot execution;
- D98 workspace AI policy;
- D104/D105 task-aware routing;
- D111 explicit Chat AI mode;
- D110 Engineering AI Draft;
- D113 Engineering Investigation;
- D121/D123 fixed Engineering Skill paths.

Routing continues to select an AI adapter.

D125 profile resolution happens only after the Local AI adapter has been
selected and must not replace or bypass workspace/provider routing.

## Exact task kinds

D125 supports exactly the existing D104 task kinds:

- `general_chat`
- `software_engineering`

No aliases, inferred task names, arbitrary strings, or dynamically registered
task kinds are authorized.

## Exact profile identities

D125 defines exactly two Local AI runtime profile IDs:

- `local_ai.general_chat.v1`
- `local_ai.software_engineering.v1`

The mapping is fixed:

- `general_chat` -> `local_ai.general_chat.v1`
- `software_engineering` -> `local_ai.software_engineering.v1`

Unknown task kinds fail closed.

There is no "closest", default-other-task, profile retry, or profile fallback.

## Immutable profile contract

One Local AI task runtime profile contains exactly bounded server-owned
generation configuration:

- profile ID;
- exact D104 task kind;
- model ID;
- timeout seconds;
- context length;
- reasoning-enabled policy.

The profile contains no:

- workspace authority;
- conversation authority;
- prompt;
- provider credential;
- Tool;
- Module;
- Plugin;
- connector;
- Skill;
- proposal;
- approval;
- Apply authority.

Profiles are immutable deployment configuration.

## Deployment settings

The existing common Local AI settings remain supported:

- `OAI_LOCAL_AI_MODEL`
- `OAI_LOCAL_AI_TIMEOUT_SECONDS`
- `OAI_LOCAL_AI_CONTEXT_LENGTH`

They remain the fallback values when a task-specific override is absent.

D125 may add these exact optional server-owned settings:

- `OAI_LOCAL_AI_GENERAL_CHAT_MODEL`
- `OAI_LOCAL_AI_GENERAL_CHAT_TIMEOUT_SECONDS`
- `OAI_LOCAL_AI_GENERAL_CHAT_CONTEXT_LENGTH`
- `OAI_LOCAL_AI_GENERAL_CHAT_REASONING_ENABLED`
- `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_MODEL`
- `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_TIMEOUT_SECONDS`
- `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_CONTEXT_LENGTH`
- `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_REASONING_ENABLED`

Task-specific model, timeout, and context settings fall back only to the
existing common setting for the same field.

They never fall back to another task profile.

## Reasoning defaults

When no task-specific reasoning setting is supplied:

- General Chat profile uses `reasoning_enabled = None`, preserving runtime
  default behavior.
- Software Engineering profile uses `reasoning_enabled = false`.

The Software Engineering default is a server-owned compatibility policy. It
prevents a reasoning-capable runtime from silently enabling hidden/thinking
generation for D110/D113/D121/D123 Engineering requests unless deployment
configuration explicitly changes that policy.

Reasoning policy is not supplied by the owner prompt or browser request.

## Model compatibility meaning

D125 does not maintain a hard-coded model-family allowlist.

It does not assert that one model is smarter, safer, or higher quality than
another.

For D125 V1, model/runtime compatibility means:

1. the Local AI deployment is enabled;
2. the configured runtime is available;
3. the exact profile model is installed/available;
4. the immutable profile is valid;
5. the runtime accepts the bounded generation options when inference executes.

If any requirement fails, that exact Local AI request fails closed.

No different model, profile, provider, or cloud route is attempted
automatically.

## Profile resolution authority

Profile resolution accepts only the server-derived D104 `AITaskKind`.

It must not inspect or depend on:

- user message text;
- system/retrieved Context;
- AI output;
- Conversation title;
- Project content;
- Skill catalog metadata;
- frontend state;
- browser localStorage;
- model response;
- arbitrary request metadata.

Prompt injection cannot select another profile or model.

## Planning boundary

When D35 selects an adapter other than Local AI, existing planning behavior is
preserved.

When D35 selects the Local AI adapter:

1. resolve the exact Local AI profile from the server-derived task kind;
2. verify the Local AI runtime/profile model is available through a read-only
   runtime availability boundary;
3. fail closed when the exact profile model is unavailable;
4. create one `ai.generate_text` step bound to the selected Local AI profile.

The Local AI execution step must pin exactly:

- `capability_id`
- `model_id`
- `local_ai_profile_id`

The model ID must equal the resolved profile model.

Planning must never select another installed model when the configured profile
model is unavailable.

## Authorization boundary

D36 must authorize the expanded Local AI plan shape explicitly.

For the Local AI adapter, the exact allowed AI step parameters are:

- `capability_id`
- `model_id`
- `local_ai_profile_id`

For non-Local-AI adapters, the pre-D125 AI plan shape remains unchanged unless
separately frozen.

The existing execution-plan digest binds the profile ID and model ID because
they are part of the immutable plan parameters.

Authorization grants no profile-selection authority back to the caller.

## Authorized runtime metadata binding

D125 may define reserved provider-neutral Local AI metadata keys used only
between the authorized AI runtime and LocalAIAdapter.

The exact reserved concepts are:

- authorized Local AI profile ID;
- authorized Local AI model ID.

Caller-supplied AIRequest metadata must not be able to replace these values.

If a caller supplies a reserved authorization metadata key before AIRuntime
binds it, execution fails closed.

AIRuntime derives the reserved values only from the already-authorized
execution plan.

## LocalAIAdapter execution

LocalAIAdapter must:

1. require the exact authorized profile binding;
2. resolve that profile from the immutable server registry;
3. require the authorized model ID to equal the profile model ID;
4. check runtime and exact model availability;
5. invoke the runtime with the profile model;
6. use the profile timeout;
7. use the profile context length;
8. apply the profile reasoning policy;
9. return only a valid non-empty result.

A mismatch fails closed before generation.

The adapter must not retry another profile or model.

## Existing request-specific generation constraints

D113 currently supplies bounded request-specific Local AI generation options
for structured output.

D125 preserves that capability.

Request-specific:

- response schema;
- temperature;

remain bounded generation constraints.

For reasoning:

- if a profile has an explicit boolean reasoning policy, request-specific
  reasoning must match that profile policy;
- a conflicting value fails closed;
- if the profile reasoning policy is `None`, an existing trusted server-side
  request-specific reasoning value may be used.

Browser or prompt text does not gain generation-option authority.

D110, which currently supplies no generation options, inherits the exact
Software Engineering profile and therefore receives the default
`reasoning_enabled = false` behavior.

## General Chat behavior

Normal Chat routed to Local AI uses exactly the General Chat profile.

This applies whether Local AI was selected through an existing permitted
workspace default or explicit Local AI mode.

D125 does not change D98/D111 routing precedence.

## Software Engineering behavior

D110 Engineering AI Draft, D113 Engineering Investigation, and the fixed Skill
paths that delegate to those workflows continue to use
`AITaskKind.SOFTWARE_ENGINEERING`.

They therefore bind exactly the Software Engineering Local AI profile.

D125 adds no proposal, approval, repository mutation, or Apply authority.

## No provider fallback

If the Local AI runtime is unavailable, the exact profile model is missing,
generation times out, the runtime rejects the reasoning option, or the runtime
returns an invalid/empty response:

- fail the exact request;
- preserve the existing safe error envelope;
- do not retry another Local AI model;
- do not switch to another Local AI profile;
- do not switch to Cloud AI.

## Telemetry boundary

Local AI telemetry remains best-effort and non-authoritative.

D125 must ensure inference telemetry observes the model actually selected by
the authorized profile rather than assuming one fixed deployment model.

Telemetry failure must never:

- change model selection;
- change profile selection;
- fail an otherwise successful inference;
- grant execution authority.

## D102 / D103 boundary

D125 does not expand the existing owner-facing D102/D103 Local AI UI into a
model picker or runtime profile editor.

The existing D102 visibility and D103 configured-model load/unload authority
remain frozen.

Profile visibility/editing or per-profile model load/unload controls require a
separately frozen milestone.

## No runtime profile persistence

Profiles come from server deployment configuration.

D125 adds no:

- database table;
- database column;
- Alembic migration;
- browser persistence;
- Conversation persistence;
- Project persistence;
- owner-editable runtime profile record.

Restarting the backend re-resolves profiles from deployment configuration.

## Exact runtime production scope

D125 runtime production changes are limited to exactly:

- `backend/app/core/config.py`
- `backend/app/contracts/local_ai_runtime.py`
- `backend/app/contracts/local_ai_profile.py`
- `backend/app/services/local_ai_profile.py`
- `backend/app/adapters/local_ai.py`
- `backend/app/services/execution_planner.py`
- `backend/app/services/execution_guard.py`
- `backend/app/services/ai_runtime.py`
- `backend/app/api/dependencies.py`
- `backend/app/telemetry/system_metrics.py`

The two Local AI profile files may be newly created.

Any additional runtime production file requires an explicit D125 design
amendment before implementation.

## Exact deployment/support scope

D125 may additionally update exactly:

- `.env.example`
- `scripts/smoke_mvp.ps1`
- `docs/MVP_RUNBOOK.md`

The smoke script must use the effective General Chat profile model when
performing its existing Local AI Chat smoke instead of assuming only the
legacy common model.

Documentation must describe task-specific settings as optional server-owned
deployment configuration.

## Explicitly unchanged production surfaces

D125 does not modify:

- frontend production code;
- Chat API request schema;
- Engineering API routes;
- Skill API routes;
- D102 API/UI contract;
- D103 model-control contract;
- database models;
- migrations;
- repositories;
- workspace routing policy;
- provider credentials;
- Local AI backend selection;
- Ollama HTTP endpoint semantics.

## Explicitly out of scope

D125 does not add:

- browser model selection;
- browser profile selection;
- arbitrary model ID request parameters;
- automatic model benchmarking;
- automatic model quality scoring;
- automatic model download/pull;
- model deletion;
- generic Ollama administration;
- automatic profile creation;
- dynamic task types;
- profile selection from AI output;
- profile selection from prompt text;
- automatic Cloud AI fallback;
- automatic alternate Local AI fallback;
- persistent profile management;
- LAN/public deployment changes.

## Historical compatibility

Existing D104/D105 task routing semantics remain unchanged: routing selects
provider/adapter class before D125 Local AI profile resolution.

Existing D110/D113/D121/D123 authority boundaries remain unchanged.

If a historical test encodes a single-model assumption that directly conflicts
with this frozen D125 profile design, implementation must stop and report the
exact test/assertion before changing that historical assertion.

No historical security test may be silently weakened.

## Dedicated D125 tests

D125 implementation must add dedicated tests covering at least:

1. exact two-profile registry;
2. exact D104 task-to-profile mapping;
3. invalid task fails closed;
4. legacy common configuration fallback;
5. task-specific model override;
6. task-specific timeout/context override;
7. General Chat reasoning default is runtime default/None;
8. Software Engineering reasoning default is false;
9. local planner pins exact model plus profile ID;
10. missing exact profile model fails without fallback;
11. Local AI authorization accepts only the exact expanded plan shape;
12. Cloud/non-Local-AI plan shape remains unchanged;
13. execution-plan digest changes when profile/model changes;
14. caller cannot inject reserved Local AI authorization metadata;
15. LocalAIAdapter rejects profile/model mismatch;
16. LocalAIAdapter uses profile timeout/context/reasoning;
17. D113 structured schema and temperature remain supported;
18. conflicting D113/profile reasoning fails closed;
19. D110 inherits Software Engineering reasoning policy;
20. normal Local AI Chat inherits General Chat profile;
21. D121/D123 Skill delegation inherits Software Engineering profile;
22. telemetry uses the actual profile model;
23. no model/profile/cloud fallback;
24. no frontend production change;
25. no database/migration change.

## Regression requirements

D125 must run relevant historical Local AI, routing, planning, authorization,
runtime, Engineering, Skill, workspace, and security tests.

Full backend regression remains required before acceptance.

Deployment verification must include:

- MVP smoke;
- frontend regression/build because unchanged frontend must remain compatible;
- `git diff --check`.

## Guided deployment acceptance

D125 Guided Acceptance must prove at least:

1. O-AI starts with legacy common Local AI settings only;
2. common settings correctly populate both profiles when no overrides exist;
3. explicit Local AI normal Chat succeeds through the General Chat profile;
4. D110 Engineering draft succeeds through the Software Engineering profile;
5. D123 fixed Engineering AI Draft Skill succeeds through the same Software
   Engineering profile;
6. Software Engineering default reasoning control does not create repository
   mutation or proposal authority;
7. an exact missing profile model fails closed without alternate-model or
   Cloud fallback;
8. optional distinct General Chat and Software Engineering model configuration
   can be resolved when both exact models are installed;
9. no browser request can choose an arbitrary model/profile;
10. Git repository remains unchanged by inference acceptance operations.

## Suggested implementation staging

Batch 01:
- immutable profile contract/registry;
- deployment settings;
- exact task resolution;
- profile-aware planner binding;
- authorization/runtime binding;
- adapter generation behavior;
- telemetry model binding;
- focused D125 tests.

Batch 02:
- `.env.example`;
- smoke/runbook updates;
- dedicated security acceptance;
- historical regression;
- full backend regression;
- frontend typecheck/lint/build;
- Guided Deployment Acceptance.

No implementation batch may push until all required gates are complete and the
owner explicitly authorizes push.

## Frozen security principle

D125 changes which exact server-configured Local AI model/runtime behavior is
bound to an already-selected Local AI task.

It does not change who may select Local AI, does not give the browser model
authority, and does not expand execution authority.
## Amendment A — Historical LocalAIAdapter Test Migration Authorization

During the required pre-implementation historical-test review, the existing
`backend/tests/test_local_ai_adapter.py` was found to encode the pre-D125
direct-adapter invocation contract.

That historical test surface constructs LocalAIAdapter with one deployment
model and invokes `generate()` using an AIRequest that has no authorized
Local AI profile/model binding.

D125 intentionally makes that historical assumption invalid.

This amendment is the explicit authorization required by the frozen
Historical Test Conflict Rule.

### Exact historical test authorization

D125 Batch 01 may modify exactly this existing historical test file:

- `backend/tests/test_local_ai_adapter.py`

This authorization is test-only and does not expand D125 production scope.

The file may be migrated so existing direct LocalAIAdapter unit tests simulate
the post-authorization internal request state required by D125.

Permitted migration includes:

- adapting the LocalAIAdapter test fixture to the D125 immutable profile
  resolver/registry;
- adding test helpers that construct an exact valid authorized Local AI
  profile/model binding;
- updating historical successful-generation tests to use that valid binding;
- updating historical runtime-unavailable tests to use that valid binding;
- updating historical model-unavailable tests to use that valid binding;
- updating historical timeout tests to use that valid binding;
- updating historical malformed/empty-response tests to use that valid
  binding;
- updating historical no-fallback tests to use that valid binding;
- updating historical structured-generation tests to use that valid binding;
- updating historical telemetry tests to use that valid binding;
- preserving the original behavioral purpose of those tests;
- adding or strengthening assertions that missing, malformed, conflicting, or
  mismatched authorization binding fails before unauthorized generation.

### Required security preservation

This amendment does not authorize any production behavior in which an
unbound request may successfully invoke LocalAIAdapter.

In particular:

- `AIRequest(content="...")` with no D125 authorized profile/model binding
  must not be accepted by the D125 LocalAIAdapter execution path;
- caller-supplied reserved authorization metadata must not bypass AIRuntime
  authorization;
- a model/profile mismatch must fail closed;
- existing no-fallback behavior must remain tested;
- timeout/runtime/model/response failures must remain fail-closed;
- telemetry remains non-authoritative.

Historical assertions may be mechanically updated only where the assertion
depends on the superseded pre-D125 direct-adapter invocation shape.

The behavioral intent of historical tests must not be weakened.

### Scope limit

This amendment authorizes changes only to:

- the already frozen D125 production scope;
- dedicated D125 tests;
- `backend/tests/test_local_ai_adapter.py`.

If any other historical test file contains a distinct frozen-design conflict,
implementation must stop and report that exact conflict before modifying it.

No frontend production change, database change, migration, routing expansion,
provider fallback, model fallback, or execution-authority expansion is
authorized by this amendment.
