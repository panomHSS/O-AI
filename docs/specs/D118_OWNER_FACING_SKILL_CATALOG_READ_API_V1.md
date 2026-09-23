# D118 — Owner-Facing Skill Catalog Read API V1

Status: FROZEN DESIGN

## 1. Purpose

D118 exposes the trusted server-defined Skill Catalog as bounded read-only
owner-facing API metadata.

D118 does not add a new Skill execution path.

D118 does not change D115 invocation semantics, D116 owner-facing invocation
authority, or D117 fixed-Skill frontend behavior.

The catalog remains declarative metadata only.

## 2. Existing boundaries reused

D118 reuses and must not weaken:

- D114 immutable SkillDescriptor contract
- D114 deterministic read-only SkillCatalog
- D114 trusted built-in Skill definitions
- D115 bounded SkillInvocationBridge
- D116 owner-facing Skill invocation API
- D117 fixed owner-facing Skill invocation frontend control
- existing local owner request marker.

D118 adds visibility only.

Visibility is not execution authority.

## 3. Core rule

OWNER-FACING SKILL CATALOG API =
TRUSTED SERVER METADATA + READ-ONLY PROJECTION + DETERMINISTIC ORDER

The catalog API is not:

- an execution registry
- authorization
- invocation authority
- a dynamic plugin registry
- Skill installation
- Skill activation
- provider/model selection
- Tool/Module/connector/credential exposure
- repository mutation authority
- proposal authority
- approval authority
- Apply authority.

## 4. Exact endpoint

D118 V1 adds exactly one endpoint:

GET /api/v1/engineering/skills

Router-relative path:

GET /engineering/skills

No additional Skill catalog routes are introduced.

D118 V1 does not add:

- GET /engineering/skills/{skill_id}
- POST /engineering/skills
- PUT/PATCH/DELETE Skill routes
- registration routes
- activation routes
- discovery-from-network routes.

The existing D116 invocation route remains unchanged:

POST /api/v1/engineering/skills/{skill_id}/invoke

## 5. Owner-facing request boundary

The catalog endpoint requires the existing local Engineering owner request
marker:

X-OAI-Local-Request: 1

The marker remains explicit local owner-browser intent and is not promoted to
authentication.

D118 introduces no new credential, token, session, cookie, or authentication
mechanism.

## 6. Workspace rule

The D118 catalog is trusted server-global metadata, not workspace-owned state.

The D118 catalog endpoint does not require a workspace id in the request body.

The D118 catalog response does not contain workspace_id.

D118 must not create workspace-specific Skill availability or policy.

Future workspace-specific Skill policy, if ever needed, requires a separately
frozen milestone.

## 7. Conversation rule

The catalog endpoint is metadata-only and has no conversation binding.

It accepts no conversation_id.

It reads no conversation state.

It creates no conversation state.

It must not invoke a Skill as a side effect of catalog read.

## 8. Authoritative catalog source

D118 must project from the existing D114 trusted built-in SkillCatalog.

The authoritative source remains:

build_builtin_skill_catalog()

and the deterministic immutable metadata returned by:

SkillCatalog.list()

D118 must not duplicate the built-in descriptor definitions in the API layer.

D118 must not create a second mutable catalog.

## 9. Deterministic ordering

The API returns Skills in the order provided by SkillCatalog.list().

The API layer performs no owner-controlled sorting or arbitrary reordering.

No query parameter changes catalog membership or ordering in D118 V1.

## 10. Public descriptor projection

Each catalog item exposes only these D114 declarative fields:

- skill_id
- version
- display_name
- description
- task_kind
- required_ai_capability_ids
- input_kind
- context_kind
- output_kind

task_kind is serialized from the existing trusted AITaskKind value.

required_ai_capability_ids preserves the trusted descriptor ordering.

No additional internal field is exposed.

## 11. Fields explicitly excluded

The catalog response must not expose:

- Python module paths
- Python class names
- callables
- handler references
- service instances
- dependency names
- filesystem paths
- repository roots
- invoke URLs
- HTTP methods for invocation
- provider ids
- adapter ids
- model ids
- credentials
- credential references
- Tool ids
- Module ids
- connector ids
- runtime objects
- approval evidence
- proposal payloads
- Apply payloads
- execution target kinds.

## 12. Response envelope

D118 uses the existing API success envelope.

Conceptual response shape:

ApiSuccess[SkillCatalogResponse]

SkillCatalogResponse contains exactly:

- skills

skills is the deterministic list of public descriptor projections.

D118 V1 adds no pagination, cursor, owner filter, search query, or arbitrary
catalog selector.

## 13. Current expected catalog content

At the D118 frozen baseline, the trusted built-in catalog contains exactly one
Skill:

engineering.investigation_change_plan

Expected trusted metadata remains owned by D114.

D118 tests may assert the exact current built-in Skill identity and descriptor
projection.

D118 does not make "exactly one Skill forever" a platform invariant.

Adding future built-in Skills requires their own approved milestone and tests.

## 14. Read-only guarantee

Calling GET /engineering/skills must not:

- invoke any Skill
- call SkillInvocationBridge.invoke()
- call EngineeringInvestigationWorkflowService.investigate()
- call an AI provider
- call Local AI
- call Cloud AI
- read repository evidence
- write repository content
- create proposal state
- create approval state
- Apply a proposal
- mutate database state
- persist catalog-read history
- mutate SkillCatalog.

## 15. D115 / D116 / D117 rule

D115 remains the only bounded Skill invocation bridge.

D116 remains the owner-facing Skill invocation API.

D117 remains the fixed owner-facing Skill invocation frontend control.

D118 catalog output must not automatically feed or trigger D115, D116, or D117.

Catalog visibility does not authorize invocation.

No automatic "select first Skill and invoke" behavior is introduced.

## 16. Provider / model rule

D118 exposes no provider or model selection.

D118 response does not reveal configured providers, configured models,
provider credentials, Local AI runtime configuration, Cloud configuration, or
routing internals.

The existing D111 task-aware routing policy remains unchanged.

## 17. Tool / Module / connector / credential rule

D118 exposes no Tool, Module, connector, credential, shell, process, Git,
network, or executable capability authority.

A required_ai_capability_id is declarative AI capability metadata only.

It is not an execution permission.

## 18. D107 / D108 rule

D118 does not:

- create Engineering Change Proposals
- approve or deny proposals
- Apply proposals
- expose approval evidence
- expose proposal/apply endpoints through catalog metadata
- convert catalog metadata into an executable request.

## 19. Persistence rule

D118 adds no database table.

D118 adds no Alembic migration.

D118 adds no catalog-read history.

D118 adds no mutable Skill registry persistence.

D118 adds no browser persistence.

## 20. Frontend rule

D118 V1 adds no frontend production change.

D117 continues to use its fixed trusted Skill identity.

D118 does not add:

- Skill picker
- catalog page
- catalog panel
- arbitrary Skill selection
- multi-Skill UX
- auto-generated Skill controls.

Any frontend catalog consumption requires a separately frozen milestone.

## 21. Expected production scope

Expected D118 production files:

- backend/app/schemas/skill_catalog.py
- backend/app/api/dependencies.py
- backend/app/api/v1/engineering.py

Expected unchanged production:

- backend/app/contracts/skill.py
- backend/app/services/skill_catalog.py
- backend/app/services/builtin_skills.py
- backend/app/services/skill_invocation_bridge.py
- backend/app/services/engineering_investigation_workflow.py
- backend/app/services/execution_planner.py
- backend/app/services/execution_guard.py
- frontend/**
- backend/alembic/**

If implementation requires another production file, D118 must be re-frozen
before that production change.

## 22. Dependency rule

D118 may expose a dependency that returns the existing trusted built-in
SkillCatalog.

The dependency must return metadata authority only.

It must not return an execution registry.

Existing SkillInvocationBridge construction may reuse that same catalog
dependency only if D115 behavior remains exactly unchanged.

No mutable singleton or dynamic registration API is introduced.

## 23. Expected tests

D118 expects:

- backend/tests/test_d118_skill_catalog_api.py
- backend/tests/test_d118_skill_catalog_api_security.py

No frontend test is required because D118 V1 has no frontend production change.

## 24. API acceptance requirements

Automated acceptance must prove at minimum:

- GET /engineering/skills exists
- existing local owner marker is required
- response uses ApiSuccess
- response has deterministic skills ordering
- response contains the exact current built-in Skill
- descriptor public fields match D114 metadata
- response excludes implementation/runtime authority
- no conversation_id is required
- no request body is required
- no invocation occurs
- existing POST /engineering/skills/{skill_id}/invoke remains unchanged.

## 25. Security acceptance requirements

Security acceptance must prove at minimum:

- no POST/PUT/PATCH/DELETE catalog mutation route exists
- no arbitrary Skill registration exists
- no dynamic loading exists
- no provider/model fields are exposed
- no Tool/Module/connector/credential fields are exposed
- no handler/callable/service reference is exposed
- no invoke URL is exposed in catalog items
- no D107/D108 payload or authority is exposed
- no Skill execution target kind is introduced
- D115 bridge remains unchanged
- D117 frontend production remains unchanged
- backend migrations remain unchanged.

## 26. Regression requirements

D118 acceptance includes:

- D114 Skill descriptor/catalog/security regressions
- D115 Skill invocation bridge/security regressions
- D116 Skill invocation API/security regressions
- D117 Skill frontend/security regressions
- relevant D109-D113 Engineering owner/security regressions
- full backend regression
- frontend TypeScript no-emit typecheck
- frontend lint
- frontend production build
- git diff --check.

No network package installation is authorized.

## 27. Guided UI rule

D118 V1 has no owner-facing frontend production change.

Therefore D118 does not require a new Guided UI acceptance solely for this API
milestone.

Existing D117 Guided UI evidence remains historical evidence only and is not
reclassified as D118 UI acceptance.

## 28. Batch plan

### Batch 01 — catalog response + GET endpoint

Implement:

- bounded public Skill catalog response schema
- existing built-in SkillCatalog dependency
- GET /engineering/skills
- primary D118 API test.

Acceptance:

- exact response projection
- deterministic ordering
- owner marker
- no workspace/conversation/request-body requirement
- no Skill invocation side effect.

### Batch 02 — security + regression

Add dedicated D118 API security acceptance.

Verify:

- catalog mutation routes absent
- runtime/internal fields absent
- D115/D116/D117 authority unchanged
- no backend migration
- no frontend change
- targeted D109-D118 regression
- full backend
- frontend typecheck/lint/build
- git diff --check.

## 29. Out of scope

D118 V1 excludes:

- frontend catalog consumption
- Skill picker
- Skill search UI
- Skill detail page
- arbitrary Skill selection
- invocation from catalog response
- multi-Skill orchestration
- Skill chaining
- autonomous Skill selection
- owner-created Skills
- dynamic Skill registration
- third-party Skill loading
- Skill installation/activation
- provider/model selection
- Tool/Module/connector/credential-bearing Skills
- workspace-specific Skill policy
- catalog persistence
- database migrations
- catalog-read audit persistence
- D107/D108 integration.

## 30. Completion criteria

D118 is complete only when:

- this frozen design exists
- exact GET catalog endpoint exists
- public descriptor projection is bounded
- catalog order remains deterministic
- local owner marker is required
- no invocation side effect exists
- no execution/runtime authority is exposed
- no mutation route exists
- D115/D116/D117 boundaries remain intact
- backend migration scope remains unchanged
- frontend production remains unchanged
- targeted security/regression passes
- full backend regression passes
- frontend typecheck/lint/build pass
- working tree is clean
- closeout evidence is recorded.

## 31. Next milestone direction

D118 does not pre-authorize frontend catalog usage.

Any owner-facing catalog UI, Skill picker, multiple Skill controls, Skill detail
view, or catalog-driven invocation requires a separately approved and frozen
milestone.
