# D120 — Second Built-in Engineering AI Draft Skill Metadata V1

Status: FROZEN DESIGN

## 1. Purpose

D120 adds exactly one second trusted built-in Skill descriptor to the existing
server-owned Skill catalog.

The new descriptor maps the already-completed D110 non-authoritative
AI-assisted Engineering drafting capability as metadata only.

D120 does not make the D110 capability invokable through the Skill invocation
bridge or Skill invocation API.

The frozen D120 rule is:

VISIBLE SKILL METADATA != INVOCATION SUPPORT != EXECUTION AUTHORITY

D120 exists to prove that the catalog can contain more than one trusted
descriptor while invocation authority remains independently and explicitly
bounded.

## 2. Reused boundaries

D120 must preserve:

- D35 ExecutionPlanner
- D36 ExecutionGuard
- D49 AIRuntime
- D106 Engineering repository observation boundary
- D107 immutable Engineering proposal boundary
- D108 controlled Engineering Apply boundary
- D109 owner workspace / conversation binding
- D110 AI-assisted Engineering drafting boundary
- D111 task-aware AI provider routing
- D113 Engineering Investigation semantics
- D114 SkillDescriptor / SkillCatalog foundation
- D115 bounded SkillInvocationBridge
- D116 owner-facing Skill invocation API
- D117 fixed-Skill frontend invocation control
- D118 read-only Skill catalog API
- D119 read-only Skill catalog frontend view.

D120 must not duplicate or weaken those systems.

## 3. Exact new Skill identity

D120 adds exactly one new built-in Skill identity:

`engineering.ai_draft`

Expected trusted constant name:

`ENGINEERING_AI_DRAFT_SKILL_ID`

Expected trusted descriptor name:

`ENGINEERING_AI_DRAFT_SKILL`

The existing built-in Skill remains unchanged:

`engineering.investigation_change_plan`

No alias, normalization, owner-supplied identity, AI-supplied identity, dynamic
registration, installation, activation, or discovery is introduced.

## 4. Exact D110 metadata mapping

The D120 descriptor is exactly:

- skill_id = `engineering.ai_draft`
- version = `1`
- display_name = `Engineering AI Draft`
- description = `Describe the bounded D110 non-authoritative AI-assisted Engineering drafting capability.`
- task_kind = `SOFTWARE_ENGINEERING`
- required_ai_capability_ids = (`text_generation`,)
- input_kind = `engineering_ai_draft_request`
- context_kind = `bounded_repository_observation`
- output_kind = `engineering_ai_draft_result`

These values are descriptive metadata only.

`input_kind`, `context_kind`, and `output_kind` identify contract families and
do not themselves validate, serialize, invoke, authorize, or execute D110.

## 5. Catalog membership and deterministic order

After D120, `BUILTIN_SKILL_DESCRIPTORS` contains exactly:

1. `ENGINEERING_AI_DRAFT_SKILL`
2. `ENGINEERING_INVESTIGATION_CHANGE_PLAN_SKILL`

The authoritative catalog listing remains the deterministic
`SkillCatalog.list()` order by `skill_id`.

Therefore the owner-facing D118/D119 listing order is exactly:

1. `engineering.ai_draft`
2. `engineering.investigation_change_plan`

D120 does not add catalog mutation, persistence, registration, installation,
enable/disable state, or network/filesystem discovery.

## 6. Metadata-only authority rule

The new descriptor must not contain or import authority for:

- provider
- adapter
- model
- endpoint
- credentials
- Tool
- Module
- connector
- handler
- callable
- service
- route
- repository root
- shell
- process
- Git
- network execution
- proposal
- approval
- Apply
- execution plan.

The D114 `SkillDescriptor` field set remains unchanged.

The D114 `SkillCatalog` remains read-only metadata.

No `skill` ExecutionTargetKind is introduced.

## 7. D110 runtime remains unchanged

D120 does not modify the D110 runtime path.

The existing D110 owner workflow remains authoritative for actual drafting:

owner
→ exact current workspace + conversation
→ exact owner-selected relative path
→ D106 bounded repository observation
→ SOFTWARE_ENGINEERING AI route
→ existing authorization-gated AI runtime
→ non-authoritative EngineeringAIDraftResult
→ owner review/edit/discard
→ optional separate explicit D107 proposal action
→ separate D108 approval/apply boundaries.

The D120 descriptor is not inserted into that runtime path.

D120 must not make D110 depend on Skill catalog resolution.

## 8. Invocation bridge remains fixed

D115 SkillInvocationBridge remains fixed to the existing supported Skill:

`engineering.investigation_change_plan`

D120 must not add D110 dispatch to the bridge.

No production change is permitted in:

- `backend/app/services/skill_invocation_bridge.py`

For `engineering.ai_draft`, catalog resolution succeeds, but bridge invocation
must fail closed as unsupported before any delegated workflow or AI side effect.

The expected existing error concept is:

`skill_invocation_skill_unsupported`

D120 must not change that error concept.

## 9. Owner-facing invocation API behavior

The existing D116 route remains unchanged:

`POST /api/v1/engineering/skills/{skill_id}/invoke`

D120 adds no route.

For:

`POST /api/v1/engineering/skills/engineering.ai_draft/invoke`

the route may resolve the catalog identity, but D115 remains authoritative and
must reject the Skill as unsupported.

Expected HTTP behavior remains the existing D116 mapping for
`skill_invocation_skill_unsupported`:

HTTP 422.

This request must not call:

- D110 AI draft service
- D113 Engineering Investigation workflow
- D35/D36/D49 directly
- D107 proposal creation
- D108 Apply
- Tool / Module / connector / credential runtime.

## 10. D117 fixed invocation remains unchanged

D117 remains fixed to:

`engineering.investigation_change_plan`

The existing frontend invocation URL remains exactly:

`/engineering/skills/engineering.investigation_change_plan/invoke`

D120 must not change D117 into:

- a Skill picker
- catalog-driven invocation
- dynamic Skill URL construction
- arbitrary skill_id input
- first-Skill auto-selection
- selectedSkillId / activeSkillId state
- multi-Skill launcher.

## 11. D118 catalog API behavior

D118 remains a read-only metadata API.

D120 intentionally changes only catalog membership from one trusted built-in
descriptor to two trusted built-in descriptors.

The D118 public schema remains unchanged.

The exact public fields remain:

- skill_id
- version
- display_name
- description
- task_kind
- required_ai_capability_ids
- input_kind
- context_kind
- output_kind.

The response remains exactly:

- `skills`

No invoke URL, handler, callable, provider, model, workspace, conversation,
credential, approval, proposal, or Apply field is added.

Historical D118 tests that assert the previous one-item built-in catalog must be
updated only to reflect the newly frozen two-item catalog. D118 authority
semantics must not be weakened.

## 12. D119 frontend behavior

D119 production frontend files are expected to remain unchanged.

The existing explicit `Load Skill catalog` action should render both server
metadata items using the existing server-provided order.

The new `engineering.ai_draft` catalog item remains metadata-only.

It must expose no Invoke / Run / Execute action.

It must not become selected or active.

It must not alter the independent D117 fixed-Skill invocation control.

D120 does not add a picker or generic multiple-Skill execution UX.

D120 only permits read-only visibility of the second trusted descriptor through
the existing generic D119 metadata rendering.

## 13. No provider/model/runtime authority

D120 adds no:

- provider selection
- model selection
- adapter selection
- Tool selection
- Module selection
- connector selection
- credential selection
- runtime selection
- fallback
- retry
- chaining
- orchestration
- autonomous Skill selection.

D110/D111 routing remains authoritative.

## 14. No D107 / D108 integration

The new descriptor must not:

- create D107 proposals
- convert draft metadata into proposals
- approve or deny proposals
- create Apply payloads
- call D108
- mutate repository files.

D110's existing explicit `Create Proposal from Draft` owner action remains
separate and unchanged.

## 15. Persistence

D120 adds no:

- database table
- Alembic migration
- Skill installation record
- Skill enable/disable state
- invocation history
- browser Skill selection persistence
- localStorage/sessionStorage authority.

The built-in catalog remains process-local, deterministic trusted server
configuration.

## 16. Exact expected production scope

Expected D120 production change is exactly:

1. `backend/app/services/builtin_skills.py`

Expected unchanged production includes:

- `backend/app/contracts/skill.py`
- `backend/app/services/skill_catalog.py`
- `backend/app/services/skill_invocation_bridge.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/v1/engineering.py`
- `backend/app/contracts/engineering_ai_draft.py`
- D110 drafting services
- D113 investigation services
- D35/D36/D49 authority files
- `frontend/**`
- `backend/alembic/**`

If implementation evidence requires another production file, D120 must be
re-frozen before modification.

## 17. Expected test scope

Historical tests with intentionally superseded exact one-item catalog assertions
may be updated only as required for the new two-item catalog:

- `backend/tests/test_d114_skill_catalog.py`
- `backend/tests/test_d114_skill_security.py`
- `backend/tests/test_d118_skill_catalog_api.py`
- `backend/tests/test_d118_skill_catalog_api_security.py`

Expected new D120 tests:

- `backend/tests/test_d120_second_builtin_skill_metadata.py`
- `backend/tests/test_d120_second_builtin_skill_security.py`

No historical security assertion may be removed merely to make D120 pass.

Tests should replace obsolete one-item membership expectations with exact
two-item expectations while retaining all metadata-only and no-authority
assertions.

## 18. Automated acceptance requirements

Automated acceptance must prove:

1. exactly two built-in descriptors exist
2. deterministic order is `engineering.ai_draft` then
   `engineering.investigation_change_plan`
3. the D110 descriptor exactly matches the frozen D120 metadata mapping
4. the existing D113 descriptor remains unchanged
5. both descriptors remain immutable metadata only
6. SkillDescriptor fields remain unchanged
7. SkillCatalog remains read-only
8. D118 response schema remains unchanged
9. D118 returns both descriptors in deterministic order
10. D119 source remains catalog-metadata-only
11. D117 fixed invocation URL remains unchanged
12. D115 bridge remains unchanged in production
13. `engineering.ai_draft` invocation fails as unsupported
14. unsupported D110 Skill invocation causes zero D110 side effect
15. unsupported D110 Skill invocation causes zero D113 side effect
16. no provider/model/tool/module/connector/credential authority is introduced
17. no D107/D108 authority is introduced
18. no Skill execution target is introduced
19. no frontend production change is introduced
20. no database migration is introduced.

## 19. Regression requirements

Acceptance must include at minimum:

- D110 relevant drafting contract/runtime/API/security regression
- D114 Skill foundation/catalog/security regression
- D115 bridge/security regression
- D116 API/security regression
- D117 frontend/security regression
- D118 catalog API/security regression
- D119 catalog frontend/security regression
- D35/D36/D49 authority regression
- relevant D91-D100 workspace/client regression
- full backend regression
- frontend TypeScript no-emit typecheck
- frontend lint
- frontend production build
- `git diff --check`.

Use the validated isolated writable `D:` pytest temp strategy if Windows Local
Temp permission errors recur.

## 20. Guided UI acceptance

Guided UI acceptance is required because the existing owner-facing D119 catalog
will visibly show a second metadata item even though no frontend production file
changes.

Owner observations must verify:

1. Engineering panel opens normally.
2. Catalog remains unloaded until explicit `Load Skill catalog`.
3. One explicit load shows exactly two trusted metadata cards.
4. `engineering.ai_draft` appears before
   `engineering.investigation_change_plan`.
5. The AI Draft card shows the frozen D120 metadata.
6. Neither catalog card exposes Invoke / Run / Execute.
7. Existing `Invoke Engineering Skill` remains fixed and separate for
   `engineering.investigation_change_plan`.
8. Workspace/conversation switching does not auto-load, select, or invoke either
   Skill.

## 21. Batch plan

### Batch 01 — second trusted descriptor

- add exact D120 descriptor to `builtin_skills.py`
- update only superseded exact catalog-membership assertions
- add D120 primary metadata acceptance
- run targeted D110/D114/D118/D119 regression
- run frontend typecheck/lint.

### Batch 02 — security and full regression

- add dedicated D120 security acceptance
- prove D110 Skill is visible but unsupported for invocation
- prove D115/D116/D117 authority remains fixed
- prove no frontend/backend authority widening outside exact production scope
- run targeted D110-D120 regression
- run relevant D91-D100 workspace/client regression
- run full backend
- run frontend typecheck/lint/build
- run `git diff --check`
- perform Guided UI acceptance.

## 22. Out of scope

D120 explicitly excludes:

- D110 Skill invocation support
- second Skill dispatch in D115
- generic Skill runtime
- generic Skill invocation API
- Skill picker
- selectable catalog rows
- arbitrary skill_id input
- dynamic invocation URL
- multiple-Skill execution UX
- Skill chaining/orchestration
- autonomous/AI-selected Skills
- owner-created Skills
- third-party Skills
- dynamic registration/installation/activation
- Tool/Module/connector/credential-bearing Skills
- provider/model selection
- workspace-specific Skill policy
- D107/D108 integration
- database persistence
- migrations.

Any of those requires a separately approved and frozen milestone.

## 23. Completion criteria

D120 is complete only when:

- frozen D120 design exists
- exactly one second built-in D110 metadata descriptor exists
- catalog contains exactly two trusted descriptors
- catalog ordering is deterministic
- D110 descriptor exactly matches the frozen metadata mapping
- D113 descriptor remains unchanged
- D118 read API exposes both descriptors without authority fields
- D119 read-only frontend displays both after explicit load
- D115 bridge does not dispatch the D110 Skill
- D116 invocation of the D110 Skill fails closed as unsupported
- D117 fixed invocation remains unchanged
- no provider/model/tool/module/connector/credential authority is added
- no D107/D108 authority is added
- no Skill execution target is added
- exact one-file production scope is preserved
- backend migrations remain unchanged
- automated regression passes
- Guided UI acceptance passes
- working tree is clean
- closeout evidence is recorded.

## 24. Next milestone boundary

D120 does not pre-authorize invocation support for the second Skill.

A future milestone may separately freeze an explicit D110 Skill invocation bridge
mapping and owner API/control behavior.

That future milestone must preserve D110 exact target-path ownership, D106
observation, workspace/conversation binding, D35/D36/D49 authorization, and
D107/D108 separation.
