# D121 — Engineering AI Draft Skill Invocation Bridge V1

Status: FROZEN DESIGN

## 1. Purpose

D121 adds one explicit second trusted dispatch mapping to the existing bounded
SkillInvocationBridge.

The exact newly supported bridge Skill is:

`engineering.ai_draft`

D121 reuses the already-completed D110 owner-bound Engineering AI Draft workflow.

D121 does not add a new AI drafting runtime, generic Skill runtime, generic
multi-contract API, Skill picker, catalog-driven frontend launcher, proposal
authority, approval authority, Apply authority, provider/model selection, Tool,
Module, connector, credential, shell, Git, or database authority.

The frozen D121 rule is:

TRUSTED CATALOG IDENTITY + EXACT DESCRIPTOR + EXACT REQUEST TYPE
→ ONE EXISTING OWNER-BOUND WORKFLOW

and never:

SKILL METADATA → GENERIC EXECUTION AUTHORITY

## 2. Reused boundaries

D121 must preserve:

- D35 ExecutionPlanner
- D36 ExecutionGuard
- D49 AIRuntime
- D106 Engineering repository observation
- D107 immutable Engineering proposal authority
- D108 controlled Engineering Apply authority
- D109 owner workspace/conversation workflow
- D110 AI-assisted Engineering drafting
- D111 task-aware AI routing
- D113 Engineering Investigation workflow
- D114 SkillDescriptor / SkillCatalog
- D115 bounded SkillInvocationBridge semantics
- D116 owner-facing Skill invocation API behavior
- D117 fixed investigation Skill frontend invocation control
- D118 read-only Skill catalog API
- D119 read-only Skill catalog frontend
- D120 second built-in Skill metadata.

D121 must not duplicate or weaken any of these systems.

## 3. Exact supported Skill identities after D121

The bridge supports exactly two trusted built-in Skill identities:

1. `engineering.ai_draft`
2. `engineering.investigation_change_plan`

No aliases, normalization, owner-supplied registration, dynamic loading,
installation, activation, discovery, handler registry, callable registry, or
third-party Skill dispatch is introduced.

A catalog-known Skill other than these exact identities must still fail closed as
unsupported.

An unknown Skill identity must still fail closed as not found.

## 4. Exact D110 bridge mapping

For:

`engineering.ai_draft`

the bridge must require all of the following:

1. the Skill exists in the trusted SkillCatalog;
2. the resolved descriptor is exactly `ENGINEERING_AI_DRAFT_SKILL`;
3. the request object is exactly an `EngineeringAIDraftRequest`;
4. the bridge was composed with an owner-bound
   `EngineeringAIDraftWorkflowService`.

Only then may the bridge delegate exactly once to:

`EngineeringAIDraftWorkflowService.draft(request)`

The bridge result is the existing:

`EngineeringAIDraftResult`

No transformation into an EngineeringInvestigationResult, D107 proposal, approval
artifact, Apply request, generic execution result, tool result, or module result is
permitted.

## 5. Existing investigation mapping remains unchanged

For:

`engineering.investigation_change_plan`

the bridge must retain the existing D115 behavior:

1. catalog identity resolves;
2. descriptor equals
   `ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL`;
3. request is exactly `EngineeringInvestigationRequest`;
4. delegate exactly once to
   `EngineeringInvestigationWorkflowService.investigate(request)`;
5. return `EngineeringInvestigationResult`.

D121 must not change D113 investigation semantics.

## 6. Bridge dispatch structure

The bridge may use explicit trusted branching over the two exact Skill IDs.

It must not introduce:

- a handler dictionary supplied externally;
- dynamic callable registration;
- reflection-based method lookup;
- import-by-string;
- plugin dispatch;
- Tool dispatch;
- Module dispatch;
- connector dispatch;
- generic operation names;
- arbitrary workflow selection;
- AI-selected Skill dispatch.

The bridge remains a small explicit trusted adapter over existing owner-bound
workflows.

## 7. Constructor and dependency composition

`SkillInvocationBridge` must require both exact owner-bound workflow service types:

- `EngineeringAIDraftWorkflowService`
- `EngineeringInvestigationWorkflowService`

Construction must fail closed on the wrong service type.

Production dependency wiring must compose the bridge with the existing:

- trusted built-in SkillCatalog;
- current exact-workspace D110 EngineeringAIDraftWorkflowService;
- current exact-workspace D113 EngineeringInvestigationWorkflowService.

D121 must reuse existing dependency providers.

It must not create a second D110 service composition path or bypass workspace
binding.

## 8. Exact request typing

Request contracts are Skill-specific and non-interchangeable.

For `engineering.ai_draft`:

- only `EngineeringAIDraftRequest` is accepted.

For `engineering.investigation_change_plan`:

- only `EngineeringInvestigationRequest` is accepted.

Passing the wrong request type for a supported Skill must fail closed as:

`skill_invocation_request_invalid`

before the target workflow is delegated.

The bridge must not infer, coerce, parse, deserialize, normalize, or mutate request
objects.

## 9. Exact descriptor validation

For each supported Skill, the bridge must compare the catalog-resolved descriptor
to the exact trusted built-in descriptor constant before delegation.

For D110:

`ENGINEERING_AI_DRAFT_SKILL`

For D113:

`ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL`

A same-ID descriptor with changed metadata must fail closed as:

`skill_invocation_descriptor_mismatch`

before any workflow side effect.

## 10. Existing error concepts remain

D121 reuses the existing D115 error concepts:

- `skill_invocation_request_invalid`
- `skill_invocation_skill_not_found`
- `skill_invocation_skill_unsupported`
- `skill_invocation_descriptor_mismatch`

D121 adds no new bridge error vocabulary unless implementation evidence proves it
is necessary and the design is re-frozen first.

Workflow-specific D110/D113 safe errors propagate from their existing owner-bound
workflow boundaries and are not normalized into execution authority.

## 11. D110 authority remains unchanged

D121 does not alter D110 behavior.

A D110 Skill invocation still means only:

owner-bound exact workspace + exact conversation
→ exact owner-provided D110 relative_path + instruction
→ D106 observation
→ SOFTWARE_ENGINEERING route
→ existing authorization-gated AI runtime
→ non-authoritative EngineeringAIDraftResult.

The AI still does not choose:

- workspace;
- conversation;
- repository root;
- target path;
- operation;
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

## 12. No D107 / D108 authority

D121 Skill invocation of `engineering.ai_draft` returns candidate draft text only.

It must not:

- create a D107 proposal;
- approve a proposal;
- deny a proposal;
- create an Apply payload;
- call D108;
- mutate repository files;
- call filesystem write adapters directly;
- treat D110 source metadata as D107 authority.

The existing explicit owner action `Create Proposal from Draft` remains separate.

## 13. D116 API remains intentionally unchanged

D121 does not redesign the existing route:

`POST /api/v1/engineering/skills/{skill_id}/invoke`

That D116 route currently owns an investigation-specific request and response
contract.

D121 must not change production code in:

`backend/app/api/v1/engineering.py`

Therefore D121 does not expose `engineering.ai_draft` as a usable owner HTTP Skill
invocation.

A request to:

`POST /api/v1/engineering/skills/engineering.ai_draft/invoke`

still enters the existing D116 investigation-shaped route.

Because D121 requires exact request typing, the bridge must reject the
EngineeringInvestigationRequest passed for the D110 Skill as:

`skill_invocation_request_invalid`

with the existing D116 HTTP 422 mapping.

This must happen before D110 drafting side effects.

A later separately frozen milestone may decide whether to add a dedicated D110
Skill route or a safe discriminated multi-contract Skill API.

D121 does not pre-authorize that decision.

## 14. Existing D110 owner API remains unchanged

The existing D110 route remains authoritative for owner-facing AI drafting:

`POST /api/v1/engineering/ai-drafts`

D121 does not change its request, response, error mapping, local owner marker,
workspace binding, or frontend control.

## 15. D117 frontend remains unchanged

The existing `Invoke Engineering Skill` control remains fixed to:

`engineering.investigation_change_plan`

D121 must not add:

- `engineering.ai_draft` invoke button;
- Skill picker;
- catalog-driven invocation;
- dynamic Skill URL construction;
- arbitrary skill_id input;
- selectedSkillId;
- activeSkillId;
- auto-select-first-Skill behavior;
- multi-Skill launcher.

Frontend production remains unchanged.

## 16. D118 / D119 / D120 catalog behavior remains unchanged

The catalog remains exactly the D120 two-item trusted metadata catalog:

1. `engineering.ai_draft`
2. `engineering.investigation_change_plan`

D121 does not add or remove Skill descriptors.

D118 remains read-only.

D119 remains explicit-load metadata-only UI.

Catalog visibility still does not itself grant execution authority.

## 17. No generic Skill runtime

D121 must not create a generic Skill execution system.

Forbidden new authority includes:

- generic handler registration;
- generic executor;
- generic runtime;
- generic context loader;
- generic tool bridge;
- generic module bridge;
- generic connector bridge;
- generic credential broker;
- Skill chaining;
- Skill orchestration;
- autonomous Skill choice;
- AI-selected Skill IDs;
- recursive Skill invocation.

The bridge continues to enumerate exact trusted supported identities in code.

## 18. No provider/model/runtime selection authority

D121 adds no provider, adapter, model, endpoint, credential, fallback, retry,
routing, runtime, or capability selection fields.

D110/D111 and D35/D36/D49 remain authoritative for AI routing and authorization.

## 19. Persistence

D121 adds no:

- database table;
- Alembic migration;
- Skill invocation record;
- Skill enablement state;
- dispatch registry persistence;
- browser Skill selection persistence;
- localStorage/sessionStorage Skill authority.

## 20. Expected production scope

Expected D121 production changes are exactly:

1. `backend/app/services/skill_invocation_bridge.py`
2. `backend/app/api/dependencies.py`

Expected unchanged production includes:

- `backend/app/services/builtin_skills.py`
- `backend/app/contracts/skill.py`
- `backend/app/services/skill_catalog.py`
- `backend/app/contracts/engineering_ai_draft.py`
- `backend/app/services/engineering_ai_draft.py`
- D106 repository reader
- D107 proposal services/contracts
- D108 Apply services/contracts
- `backend/app/api/v1/engineering.py`
- `backend/app/schemas/**`
- `frontend/**`
- `backend/alembic/**`.

If implementation requires another production file, D121 must stop and be
re-frozen before modification.

## 21. Expected historical test updates

D121 intentionally supersedes tests that assert the D120 D110 Skill is unsupported
by the bridge.

Historical tests may be updated only as required in:

- D115 bridge tests/security tests that encode one supported Skill;
- D120 security tests that explicitly require
  `engineering.ai_draft` to fail as unsupported.

No historical security assertion may be deleted merely to make D121 pass.

D120 metadata/catalog/read-only UI assertions remain valid.

D116 tests may be updated only if needed to assert the newly frozen request-type
mismatch behavior for the D110 Skill while preserving the existing route shape.

## 22. Expected new D121 tests

Expected new focused tests:

- `backend/tests/test_d121_engineering_ai_draft_skill_bridge.py`
- `backend/tests/test_d121_engineering_ai_draft_skill_bridge_security.py`

Exact filenames may only change if repository naming evidence requires it before
implementation commit.

## 23. Automated acceptance requirements

Automated acceptance must prove at minimum:

1. bridge supports exactly two built-in Skill identities;
2. D110 catalog descriptor resolves and matches exact trusted descriptor;
3. D113 descriptor mapping remains unchanged;
4. `engineering.ai_draft` + exact EngineeringAIDraftRequest delegates exactly once
   to the D110 owner-bound workflow;
5. D110 Skill invocation returns exact EngineeringAIDraftResult;
6. wrong request type for D110 fails as request invalid before delegation;
7. wrong request type for investigation fails as request invalid before delegation;
8. same-ID mismatched D110 descriptor fails before delegation;
9. same-ID mismatched investigation descriptor still fails before delegation;
10. unknown Skill still fails not-found;
11. catalog-known third Skill still fails unsupported;
12. malformed Skill identity still fails request-invalid;
13. bridge constructor requires real SkillCatalog;
14. bridge constructor requires real D110 workflow service type;
15. bridge constructor requires real D113 workflow service type;
16. bridge has no generic registration/handler surface;
17. D110 workflow errors propagate without bridge retry;
18. D113 workflow errors continue to propagate without bridge retry;
19. production dependency wiring supplies the same exact workspace-bound D110 and
    D113 workflow providers;
20. D116 engineering route production source remains unchanged;
21. D116 D110 Skill path remains unusable with investigation request and fails 422
    request-invalid before D110 side effect;
22. D110 existing `/engineering/ai-drafts` route remains unchanged;
23. D117 fixed investigation Skill URL remains unchanged;
24. no D110 Skill frontend control is added;
25. D118/D119 catalog behavior remains unchanged;
26. no provider/model/tool/module/connector/credential authority is added;
27. no D107/D108 integration is added;
28. no Skill execution target kind is added;
29. no database migration is added;
30. exact two-file production scope is preserved.

## 24. Regression requirements

Acceptance must include at minimum:

- D110 drafting contract/service/API/security regression;
- D114 Skill catalog/security regression;
- D115 bridge/security regression;
- D116 API/security regression;
- D117 frontend/security regression;
- D118 catalog API/security regression;
- D119 catalog frontend/security regression;
- D120 second Skill metadata/security regression updated only for the intentionally
  superseded unsupported-bridge rule;
- D35/D36/D49 authority regression;
- relevant D91-D100 workspace/client regression;
- full backend regression;
- frontend TypeScript no-emit typecheck;
- frontend lint;
- frontend production build;
- `git diff --check`.

Use isolated writable `D:\O-AI-test-temp` pytest temp roots if Windows temp
permissions require it.

## 25. Guided UI acceptance

D121 requires no new Guided UI acceptance because it intentionally changes no
frontend production behavior and exposes no new owner-facing route/control.

Existing D117 fixed investigation invocation UI and D119 read-only catalog UI must
remain unchanged through automated static/regression checks.

If implementation changes visible UI behavior, D121 must stop and be re-frozen.

## 26. Batch plan

### Batch 01 — explicit second bridge mapping

- extend SkillInvocationBridge constructor with exact D110 workflow dependency;
- add exact D110 descriptor/request/result mapping;
- preserve investigation mapping;
- update production dependency composition;
- update only intentionally superseded D115/D120 assertions;
- add primary D121 bridge tests;
- run targeted D110/D114/D115/D120 regression.

### Batch 02 — security and full regression

- add dedicated D121 security acceptance;
- prove exact request type and descriptor checks;
- prove zero D110 delegation on mismatch;
- prove D116 remains investigation-specific and does not expose D110 Skill invoke;
- prove frontend remains unchanged;
- prove no generic execution registry/runtime is introduced;
- run targeted D110-D121 regression;
- run D35/D36/D49 authority regression;
- run relevant D91-D100 regression;
- run full backend;
- run frontend typecheck/lint/build;
- run `git diff --check`.

## 27. Out of scope

D121 explicitly excludes:

- D110 owner-facing Skill invoke API;
- discriminated multi-Skill API;
- generic Skill request envelope;
- generic Skill response envelope;
- frontend D110 Skill invoke button;
- Skill picker;
- catalog-driven invocation;
- dynamic invocation URL;
- arbitrary skill_id input;
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
- database persistence;
- migrations.

Any of these requires a separately approved frozen milestone.

## 28. Completion criteria

D121 is complete only when:

- frozen design exists;
- bridge explicitly supports exactly the two trusted built-in Skills;
- D110 Skill requires exact trusted descriptor;
- D110 Skill requires exact EngineeringAIDraftRequest;
- D110 delegates once to the existing owner-bound D110 workflow;
- D110 returns existing EngineeringAIDraftResult only;
- D113 bridge behavior remains unchanged;
- wrong request types fail closed before workflow side effects;
- descriptor mismatch fails closed before workflow side effects;
- unknown/unsupported/malformed identity semantics remain;
- dependency composition preserves exact-workspace owner-bound workflows;
- D116 route remains unchanged and does not become a D110 Skill API;
- D117 frontend remains unchanged;
- D118/D119/D120 catalog behavior remains unchanged;
- no generic Skill runtime is introduced;
- no provider/model/tool/module/connector/credential authority is added;
- no D107/D108 authority is added;
- exact two-file production scope is preserved;
- no migration is added;
- automated regression passes;
- working tree is clean;
- closeout evidence is recorded.

## 29. Next milestone boundary

D121 does not pre-authorize owner-facing D110 Skill invocation.

A future milestone may separately freeze one safe owner-facing API/control design
for invoking `engineering.ai_draft` through the Skill surface.

That future design must resolve the current D116 investigation-specific
request/response contract without weakening D110 exact target ownership,
workspace/conversation binding, D106 observation, D35/D36/D49 authorization, or
D107/D108 separation.
