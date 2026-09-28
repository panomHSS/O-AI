# D122 — Engineering AI Draft Dedicated Skill Owner API V1

Status: FROZEN DESIGN

## 1. Purpose

D122 adds one explicit owner-facing HTTP Skill invocation surface for the already
trusted and bridge-supported built-in Skill:

`engineering.ai_draft`

D122 reuses the completed D110 Engineering AI Draft request/response contract and
the completed D121 bounded `SkillInvocationBridge` mapping.

D122 does not redesign the existing D116 generic-looking dynamic Skill route into a
multi-contract runtime.

The frozen D122 rule is:

EXACT STATIC OWNER ROUTE
+ EXACT D110 REQUEST CONTRACT
+ EXACT TRUSTED D121 SKILL ID
→ EXISTING BOUNDED D121 BRIDGE
→ EXISTING OWNER-BOUND D110 WORKFLOW
→ EXISTING D110 RESPONSE CONTRACT

and never:

SKILL URL → GENERIC MULTI-CONTRACT EXECUTION AUTHORITY


## 2. Reused completed boundaries

D122 must preserve and reuse:

- D35 ExecutionPlanner;
- D36 ExecutionGuard;
- D49 AIRuntime;
- D106 bounded Engineering repository observation;
- D107 immutable Engineering proposal authority;
- D108 controlled Engineering Apply authority;
- D109 exact owner workspace/conversation workflow;
- D110 AI-assisted Engineering drafting;
- D111 task-aware AI routing;
- D113 Engineering Investigation workflow;
- D114 SkillDescriptor / SkillCatalog;
- D115 bounded SkillInvocationBridge semantics;
- D116 investigation-specific owner-facing Skill invocation API;
- D117 fixed investigation Skill frontend invocation control;
- D118 read-only Skill catalog API;
- D119 read-only Skill catalog frontend;
- D120 second built-in Skill metadata;
- D121 explicit `engineering.ai_draft` bridge mapping.

D122 must not duplicate or weaken those systems.


## 3. Exact new owner-facing route

D122 adds exactly one new static route:

`POST /api/v1/engineering/skills/engineering.ai_draft/invoke`

The route is owner-facing and must retain the existing local Engineering owner
request marker requirement.

The route must be declared before the existing D116 dynamic route:

`POST /api/v1/engineering/skills/{skill_id}/invoke`

so the exact static `engineering.ai_draft` route is not consumed by the existing
investigation-specific D116 path operation.


## 4. Exact D122 request contract

The D122 static route must reuse the existing D110 API schema:

`EngineeringAIDraftCreateRequest`

The request fields remain exactly the existing D110 owner fields:

- `conversation_id`
- `relative_path`
- `instruction`

D122 adds no generic request envelope and no discriminator field.

D122 adds no owner-supplied:

- `skill_id`
- provider ID
- model ID
- tool ID
- module ID
- connector ID
- credential reference
- operation selector
- proposal selector
- Apply selector
- repository root.


## 5. Exact D122 response contract

The D122 static route must reuse the existing D110 API response schema:

`EngineeringAIDraftResponse`

The response remains the existing non-authoritative D110 draft response.

D122 adds no generic Skill response envelope beyond the already existing API success
wrapper used by the Engineering API.

D122 must not transform the D110 result into:

- Engineering Investigation result;
- D107 proposal;
- approval artifact;
- Apply payload;
- generic execution result;
- tool result;
- module result.


## 6. Exact bridge invocation

The route must construct the existing exact D110 contract object:

`EngineeringAIDraftRequest`

from the existing D110 API request schema.

The route must invoke the D121 bridge using the exact trusted built-in Skill ID:

`ENGINEERING_AI_DRAFT_SKILL_ID`

with semantics equivalent to:

```python
result = bridge.invoke(
    skill_id=ENGINEERING_AI_DRAFT_SKILL_ID,
    request=request,
)
```

D122 must not call the D110 workflow `.draft()` method directly from the new Skill
route.

The purpose of the D122 route is to expose the already bounded D121 Skill bridge,
not to create a second direct owner workflow path.


## 7. Existing direct D110 owner API remains unchanged

The existing D110 owner route remains:

`POST /api/v1/engineering/ai-drafts`

D122 must not change that route's:

- path;
- request schema;
- response schema;
- local owner marker;
- exact workspace binding;
- exact conversation binding;
- D106 observation semantics;
- AI routing semantics;
- D110 error semantics;
- frontend use.

The direct D110 route and the new D122 Skill route are two owner HTTP surfaces over
the same bounded D110 capability, but only the D122 route must pass through the D121
SkillInvocationBridge.


## 8. Existing D116 investigation Skill route remains investigation-specific

The existing D116 dynamic route remains:

`POST /api/v1/engineering/skills/{skill_id}/invoke`

Its request contract remains:

`EngineeringInvestigationCreateRequest`

Its response contract remains:

`EngineeringInvestigationResponse`

D122 must not redesign this route as:

- a discriminated union request;
- a discriminated union response;
- a generic request envelope;
- a generic response envelope;
- a runtime-selected schema;
- a catalog-selected schema;
- a handler registry;
- a dynamic dispatch table.

For the existing trusted investigation Skill:

`engineering.investigation_change_plan`

D116 behavior remains unchanged.


## 9. Route-order boundary

Because D122 adds a static route that is a specialization of the existing D116
dynamic path shape, production source ordering is part of the frozen design.

The exact static D122 route must be registered before:

`/skills/{skill_id}/invoke`

Automated acceptance must prove the D122 static path reaches the D110-specific path
operation rather than the D116 investigation-specific path operation.


## 10. Exact dependency usage

The new route must use the existing request-scoped:

`SkillInvocationBridge`

through the existing dependency provider:

`get_skill_invocation_bridge`

D122 must not create a second bridge provider.

D122 must not directly compose:

- EngineeringAIDraftWorkflowService;
- EngineeringInvestigationWorkflowService;
- SkillCatalog;
- AIRuntime;
- ExecutionPlanner;
- ExecutionGuard;
- provider adapters;
- model adapters;
- credential brokers.

Existing D121 dependency composition remains authoritative.


## 11. Exact error boundaries

D122 must preserve the existing error ownership boundaries.

### Request construction / D110 request errors

If construction of the existing `EngineeringAIDraftRequest` raises an existing
D110-prefixed request validation error, the route must preserve the existing D110
error semantics used by the direct D110 owner route.

Unexpected request-construction `ValueError` must fail closed as the existing:

`engineering_ai_draft_request_invalid`

D122 does not invent a second D110 request error vocabulary.

### Bridge errors

`SkillInvocationError` from the D121 bridge must continue through the existing
Engineering Skill invocation HTTP mapping:

- not found → existing 404 mapping;
- descriptor mismatch → existing 503 mapping;
- request invalid → existing 422 mapping;
- unsupported → existing 422 mapping.

### D110 workflow errors

Existing `EngineeringAIDraftError` values must continue through the existing D110
HTTP mapping used by the direct D110 owner route.

D122 adds no retry or error normalization layer.


## 12. D110 authority remains non-authoritative

D122 Skill invocation still means only:

owner-bound exact workspace + exact conversation
→ exact owner-provided relative path + instruction
→ D106 observation
→ SOFTWARE_ENGINEERING AI route
→ existing authorization-gated AI runtime
→ non-authoritative EngineeringAIDraftResult
→ existing EngineeringAIDraftResponse.

The AI still does not choose:

- workspace;
- conversation;
- repository root;
- target path;
- provider;
- model;
- proposal;
- approval;
- Apply;
- tool;
- module;
- connector;
- credential;
- shell command;
- Git command.


## 13. No D107 / D108 authority

D122 must not:

- create a D107 proposal automatically;
- approve or deny a proposal;
- create an Apply payload;
- invoke D108;
- mutate repository files;
- call filesystem write adapters directly;
- treat D110 draft metadata as proposal authority.

The existing explicit owner action:

`Create Proposal from Draft`

remains separate from both the direct D110 route and the new D122 Skill route.


## 14. Frontend remains unchanged

D122 is API-only.

Frontend production must remain unchanged.

The existing direct D110 drafting control continues to call:

`POST /api/v1/engineering/ai-drafts`

The existing D117 Skill invocation control remains fixed to:

`engineering.investigation_change_plan`

D122 must not add:

- an `engineering.ai_draft` Skill invoke button;
- Skill picker;
- catalog-driven invocation;
- dynamic Skill URL construction;
- arbitrary `skill_id` input;
- `selectedSkillId`;
- `activeSkillId`;
- auto-select-first-Skill behavior;
- multi-Skill launcher.

A later separately frozen milestone may choose whether to expose the D122 static
route through owner UI.


## 15. D118 / D119 / D120 catalog behavior remains unchanged

D122 adds no Skill descriptors and changes no catalog metadata.

The trusted catalog remains exactly:

1. `engineering.ai_draft`
2. `engineering.investigation_change_plan`

D118 remains read-only.

D119 remains metadata-only UI.

Catalog visibility still does not itself grant execution authority.


## 16. No generic Skill runtime

D122 must not create:

- generic Skill request dispatch;
- generic Skill response dispatch;
- generic handler registration;
- handler dictionary;
- dynamic callable registry;
- reflection-based handler lookup;
- import-by-string;
- plugin dispatch;
- Tool dispatch;
- Module dispatch;
- connector dispatch;
- credential dispatch;
- Skill chaining;
- Skill orchestration;
- recursive Skill invocation;
- autonomous Skill selection;
- AI-selected Skill IDs.

D122 adds one exact static owner API surface only.


## 17. No provider/model/runtime authority

D122 adds no:

- provider selector;
- adapter selector;
- model selector;
- endpoint selector;
- credential selector;
- runtime selector;
- fallback selector;
- retry policy;
- capability selector;
- Tool target kind;
- Module target kind;
- Skill execution target kind.

D110/D111 and D35/D36/D49 remain authoritative.


## 18. Persistence

D122 adds no:

- database table;
- Alembic migration;
- invocation persistence;
- Skill enablement state;
- dispatch registry state;
- browser Skill selection state;
- localStorage/sessionStorage Skill authority.


## 19. Expected production scope

Expected D122 production change is exactly one file:

1. `backend/app/api/v1/engineering.py`

Expected unchanged production includes:

- `backend/app/api/dependencies.py`
- `backend/app/services/skill_invocation_bridge.py`
- `backend/app/services/builtin_skills.py`
- `backend/app/contracts/skill.py`
- `backend/app/services/skill_catalog.py`
- `backend/app/contracts/engineering_ai_draft.py`
- `backend/app/schemas/engineering_ai_draft.py`
- `backend/app/services/engineering_ai_draft.py`
- D106 repository reader
- D107 proposal services/contracts
- D108 Apply services/contracts
- `frontend/**`
- `backend/alembic/**`

If implementation requires another production file, D122 must stop and be
re-frozen before modification.


## 20. Intentionally superseded historical assertions

D122 intentionally supersedes only historical assertions that encoded the
pre-D122 rule that:

`POST /engineering/skills/engineering.ai_draft/invoke`

must be unusable because the D116 dynamic route is investigation-specific.

Those assertions may exist in D120/D121 security or regression tests.

They may be updated only to reflect the new exact static D122 route while
preserving the security property that:

- investigation-shaped input must not become a valid D110 draft request;
- malformed D110 input must fail before D110 side effects;
- D116 investigation behavior remains unchanged;
- no generic multi-contract runtime is introduced.

Historical tests must not be weakened merely to make D122 pass.


## 21. Expected new D122 tests

Expected new focused tests:

- `backend/tests/test_d122_engineering_ai_draft_skill_owner_api.py`
- `backend/tests/test_d122_engineering_ai_draft_skill_owner_api_security.py`

Exact filenames may change only if repository naming evidence requires it before
implementation commit.


## 22. Automated acceptance requirements

Automated acceptance must prove at minimum:

1. exact static route
   `/engineering/skills/engineering.ai_draft/invoke` exists;
2. static D122 route is registered before the D116 dynamic Skill route;
3. route requires the existing local Engineering owner request marker;
4. route request schema is exactly `EngineeringAIDraftCreateRequest`;
5. route response schema is exactly `EngineeringAIDraftResponse`;
6. route constructs exactly one `EngineeringAIDraftRequest`;
7. route invokes `SkillInvocationBridge`;
8. route passes exact `ENGINEERING_AI_DRAFT_SKILL_ID`;
9. route does not call D110 `.draft()` directly;
10. exact valid D110 Skill request delegates through the bridge exactly once;
11. exact valid request returns the existing D110 response fields;
12. wrong/malformed request fails before bridge/D110 side effects as appropriate;
13. bridge descriptor mismatch preserves existing Skill error mapping;
14. bridge unsupported/not-found/request-invalid mappings remain unchanged;
15. D110 workflow errors preserve existing `_ai_draft_error` HTTP mapping;
16. existing `/engineering/ai-drafts` route remains unchanged;
17. existing D116 investigation Skill route contract remains unchanged;
18. `engineering.investigation_change_plan` D116 invocation remains functional;
19. investigation-shaped input to the static D110 Skill route does not become a
    valid D110 request;
20. exact workspace binding remains server-side;
21. exact conversation binding remains enforced by D110 workflow;
22. no D107 proposal is created automatically;
23. no D108 Apply call occurs;
24. no filesystem write authority is added;
25. no provider/model/tool/module/connector/credential authority is added;
26. no generic handler/runtime/registry is added;
27. no frontend production file changes;
28. no database migration is added;
29. exact one-file production scope is preserved.


## 23. Regression requirements

Acceptance must include at minimum:

- D110 drafting contract/service/API/security regression;
- D114 Skill catalog/security regression;
- D115 bridge/security regression;
- D116 API/security regression;
- D117 frontend/security regression;
- D118 catalog API/security regression;
- D119 catalog frontend/security regression;
- D120 metadata/security regression with only intentionally superseded assertions
  updated;
- D121 bridge/security regression with only intentionally superseded pre-D122
  route assertions updated;
- D35/D36/D49 authority regression;
- relevant D91-D100 workspace/client regression;
- full backend regression;
- frontend TypeScript no-emit typecheck;
- frontend lint;
- frontend production build;
- `git diff --check`.

Use isolated writable `D:\O-AI-test-temp` pytest temp roots if Windows temp
permissions require it.


## 24. Guided UI acceptance

D122 requires no new Guided UI acceptance because frontend production is frozen
unchanged.

If implementation changes visible UI behavior, D122 must stop and be re-frozen.


## 25. Batch plan

### Batch 01 — exact static D110 Skill owner API

- add exact static D110 Skill route before D116 dynamic route;
- use existing D110 request/response schemas;
- invoke exact D121 bridge Skill identity;
- preserve direct D110 owner route unchanged;
- preserve D116 investigation route unchanged;
- update only intentionally superseded D120/D121 assertions;
- add primary D122 API tests;
- run targeted D110/D114-D122 regression.

### Batch 02 — security and full regression

- add dedicated D122 security acceptance;
- prove static-route ordering;
- prove no direct workflow bypass;
- prove exact local-owner marker requirement;
- prove exact D110 request/response contract;
- prove no D107/D108 authority;
- prove no generic Skill multi-contract runtime;
- prove frontend unchanged;
- run targeted D110-D122 regression;
- run D35/D36/D49 authority regression;
- run relevant D91-D100 regression;
- run full backend regression;
- run frontend typecheck/lint/build;
- run `git diff --check`.


## 26. Out of scope

D122 explicitly excludes:

- redesign of `/skills/{skill_id}/invoke` into a generic multi-contract API;
- discriminated multi-Skill request envelope;
- discriminated multi-Skill response envelope;
- runtime-selected request schemas;
- runtime-selected response schemas;
- frontend AI Draft Skill button;
- Skill picker;
- catalog-driven invocation;
- arbitrary owner-provided `skill_id`;
- generic Skill runtime;
- handler registry;
- third-party Skill execution;
- Skill chaining/orchestration;
- autonomous Skill selection;
- owner-created Skills;
- dynamic registration/installation;
- provider/model selection;
- Tool/Module/connector/credential-bearing Skills;
- automatic D107 proposal creation;
- automatic approval;
- automatic Apply;
- persistence;
- migrations.


## 27. Completion boundary

D122 is complete only when:

- the exact static owner-facing D110 Skill route is implemented;
- it invokes the exact D121 bridge mapping;
- existing direct D110 and D116 routes remain within their frozen contracts;
- automated security/regression acceptance passes;
- frontend production remains unchanged;
- exact one-file production scope is proven;
- final closeout passes;
- owner explicitly authorizes push.

No implementation work is authorized beyond this frozen design.
