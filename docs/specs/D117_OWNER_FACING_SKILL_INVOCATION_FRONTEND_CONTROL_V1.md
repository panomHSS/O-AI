# D117 — Owner-Facing Skill Invocation Frontend Control V1

Status: FROZEN DESIGN

## 1. Purpose

D117 adds the first explicit owner-facing frontend control for invoking the exact
bounded Skill exposed by D116.

D117 does not create a generic Skill user interface.

D117 V1 supports exactly one fixed Skill identity:

engineering.investigation_change_plan

The frontend remains presentation + explicit owner intent + request transport.

It grants no new execution authority.

## 2. Existing boundaries reused

D117 reuses and must not weaken:

- D91-D100 exact workspace and client-state isolation boundaries
- D106 Engineering repository read boundary
- D107 immutable Engineering proposal boundary
- D108 controlled Engineering Apply boundary
- D109 Engineering owner panel / conversation binding
- D111 task-aware AI routing
- D113 Engineering Investigation request/result UI semantics
- D114 SkillDescriptor / SkillCatalog
- D115 bounded SkillInvocationBridge
- D116 owner-facing Skill invocation API
- existing local owner request marker
- existing exact workspace request header
- existing Chat-selected conversation state

D117 must not duplicate backend Skill dispatch or authority.

## 3. Core rule

OWNER-FACING SKILL FRONTEND =
EXPLICIT OWNER CONTROL + FIXED SKILL ID + BOUNDED REQUEST/RESULT UI

The frontend is not:

- Skill authority
- Skill discovery authority
- execution authority
- authorization
- planning authority
- proposal authority
- approval authority
- Apply authority
- provider/model selection authority
- Tool/Module/connector/credential authority
- repository mutation authority.

A visible button does not grant authority.

A successful HTTP response does not grant additional authority.

## 4. Frontend placement

D117 V1 places the control in the existing:

frontend/components/chat/engineering-owner-panel.tsx

No new top-level page is introduced.

No separate Skill center, catalog page, modal registry, or picker is introduced.

The existing Chat composition remains authoritative for selected workspace and
conversation state.

## 5. Fixed Skill identity

The frontend must use exactly:

engineering.investigation_change_plan

The owner does not type, select, alias, normalize, or discover skill_id.

No Skill dropdown is added.

No catalog/listing API is added.

No arbitrary Skill identifier from user input is allowed.

## 6. Exact endpoint

The frontend calls the existing D116 route:

POST /api/v1/engineering/skills/engineering.investigation_change_plan/invoke

No second endpoint is introduced.

No direct call to /engineering/investigations may be substituted for the D117
Skill control.

The existing D113 investigation UI may remain available separately.

## 7. Request headers

The D117 request must preserve the existing Engineering frontend request
boundary:

- X-OAI-Local-Request: 1
- X-OAI-Workspace: exact currently selected workspace
- Content-Type: application/json

The workspace header remains routing metadata only.

The frontend must not invent a default workspace.

The backend remains authoritative for workspace validation and binding.

## 8. Request body

D117 reuses the D116/D113 request shape:

- conversation_id
- instruction
- focus_paths

The request body must not carry:

- workspace_id
- skill_id
- provider
- adapter
- model
- credential
- Tool
- Module
- connector
- handler
- approval evidence
- proposal request
- Apply instruction.

skill_id remains fixed in the URL by trusted frontend code.

## 9. Conversation rule

The D117 control operates only against the conversation already selected in
Chat.

It must not create, manufacture, substitute, or silently switch
conversation_id.

If no current conversation exists, the Skill control must not invoke D116.

Backend D113/D115/D116 conversation/workspace binding remains authoritative.

## 10. Instruction rule

D117 reuses the existing Engineering Investigation instruction semantics.

The owner explicitly supplies the instruction.

The frontend must not auto-generate a Skill instruction from unrelated Chat
messages.

Blank/whitespace-only instruction must not be submitted.

Backend validation remains authoritative.

## 11. Focus paths rule

D117 reuses the existing Engineering Investigation focus-path semantics.

Existing frontend parsing/presentation may be reused.

The request sends only focus_paths accepted by the existing frontend flow.

Backend D113 validation remains authoritative for path safety and limits.

D117 must not broaden repository path authority.

## 12. Explicit invocation rule

D117 invocation occurs only after one explicit owner action on the Skill
control.

D117 must not invoke automatically on:

- component mount
- Chat message send
- assistant response
- workspace switch
- conversation switch
- instruction edit
- focus-path edit
- result rendering.

One owner action causes at most one D116 HTTP request.

## 13. Pending / duplicate-submit rule

While one Skill invocation request is pending, the D117 Skill control must be
disabled.

D117 adds no retry loop.

D117 adds no fallback request.

D117 adds no alternate Skill.

D117 adds no duplicate dispatch.

## 14. Response rule

D117 reuses the existing EngineeringInvestigationResponse-shaped data returned
by D116.

The Skill result must be presented as read-only, non-authoritative Engineering
analysis.

The UI may reuse existing D113 investigation result presentation semantics.

The result must remain visibly distinct from D107 proposal / D108 Apply
authority.

A Change Plan item must not become an executable action merely because it is
shown in the UI.

## 15. Error rule

D117 presents bounded safe HTTP/API errors from D116.

The frontend must not surface stack traces, arbitrary exception internals,
credentials, model configuration, absolute server paths, or internal callables.

D117 does not reinterpret an error into retry/fallback behavior.

## 16. Workspace transition rule

D117 must not carry a pending or completed Skill result across an incompatible
workspace/conversation selection.

The panel must follow the existing D91-D100 client-state isolation behavior.

Workspace switching must not trigger Skill invocation.

Conversation switching must not trigger Skill invocation.

## 17. Provider / model rule

D117 adds no provider selector.

D117 adds no model selector.

D117 cannot request Cloud AI.

Existing D111/D113 SOFTWARE_ENGINEERING Local-AI-only policy remains
authoritative behind D116.

## 18. D107 / D108 rule

D117 must not:

- create an Engineering Change Proposal
- approve a proposal
- deny a proposal
- Apply a proposal
- convert Change Plan items into D107 payloads
- convert Skill output into D108 execution input
- automatically invoke existing proposal/approval/apply controls.

Any future conversion from investigation output to proposal intent requires a
separately frozen milestone.

## 19. Tool / Module / connector / credential rule

D117 exposes no Tool, Module, connector, credential, shell, process, Git, or
network selection/control.

The frontend contains no generic execution target for Skills.

## 20. Backend rule

D117 V1 requires no backend production change.

The following D116 backend route remains unchanged:

POST /engineering/skills/{skill_id}/invoke

D114, D115, and D116 remain authoritative for Skill identity and invocation.

If implementation evidence requires backend production changes, D117 must be
re-frozen before those changes.

## 21. Persistence rule

D117 adds no database table.

D117 adds no Alembic migration.

D117 adds no Skill invocation history persistence.

D117 adds no browser-persisted Skill authority or queued autonomous invocation.

Transient frontend pending/error/result state is allowed.

## 22. Expected production scope

Expected D117 production change:

- frontend/components/chat/engineering-owner-panel.tsx

Expected unchanged production:

- backend/app/**
- backend/alembic/**
- frontend/app/chat/page.tsx
- frontend/components/chat/chat.tsx
- frontend/lib/api-client.ts
- frontend/components/workspace/workspace-provider.tsx
- D114/D115/D116 production files

The existing shared frontend files may be read/reused but are not expected to
require modification.

If production implementation needs another file, freeze the widened scope
before changing it.

## 23. Expected tests

D117 expects:

- backend/tests/test_d117_skill_invocation_frontend.py
- backend/tests/test_d117_skill_invocation_frontend_security.py

Tests may inspect the frontend source and exact request/control semantics in the
same style as existing D110-D113 frontend acceptance tests.

No new frontend test framework is introduced in D117 V1.

## 24. Frontend acceptance requirements

Automated acceptance must prove at minimum:

- fixed Skill id is engineering.investigation_change_plan
- exact D116 invocation URL is used
- request includes X-OAI-Local-Request: 1
- request includes exact selected X-OAI-Workspace
- request body carries current conversation_id
- request body carries instruction and focus_paths
- request body does not carry workspace_id or skill_id
- no provider/model selection is added
- no catalog/picker is added
- no automatic invocation exists
- pending invocation disables duplicate submit
- at most one request is issued per explicit action
- no retry/fallback exists
- D116 result is rendered as non-authoritative investigation output
- no D107 proposal or D108 Apply action is automatically created.

## 25. Security acceptance requirements

D117 security tests must additionally prove:

- backend production files are unchanged
- no Skill execution target kind is introduced
- no Tool/Module/connector/credential authority is introduced
- no arbitrary skill_id input is introduced
- no workspace default or workspace override is introduced
- no direct provider/model request field is introduced
- no direct proposal/approval/apply call is made by the Skill control
- existing D110-D113 frontend authority boundaries remain intact
- D114-D116 backend authority boundaries remain intact.

## 26. Regression requirements

Acceptance includes:

- D109 Engineering owner frontend/security regressions
- D110 AI Draft frontend/security regressions
- D111 AI mode frontend regressions
- D112 cloud-egress frontend regressions
- D113 Engineering Investigation frontend/runtime/API regressions
- D114 Skill foundation regressions
- D115 Skill bridge/security regressions
- D116 Skill API/security regressions
- relevant D91-D100 workspace/client-state regressions
- full backend regression
- frontend TypeScript no-emit typecheck
- frontend lint
- frontend production build
- git diff --check.

No network package installation is authorized by D117 acceptance.

## 27. Guided UI acceptance

Because D117 changes owner-facing UI, Guided UI acceptance is required after
automated acceptance.

The owner must verify in the browser:

1. an existing workspace/conversation is selected,
2. the bounded Skill control is visible in the Engineering owner panel,
3. the owner enters an instruction and optionally bounded focus paths,
4. one explicit click invokes the fixed Skill,
5. pending UI prevents duplicate invocation,
6. the returned investigation result is displayed as read-only/non-authoritative,
7. switching workspace/conversation does not auto-invoke the Skill,
8. stale incompatible Skill result state is not presented as belonging to the
   newly selected workspace/conversation.

No browser automation is introduced solely for this acceptance.

## 28. Batch plan

### Batch 01 — fixed Skill frontend control

Implement only the expected production frontend file and the primary D117
frontend acceptance test.

Acceptance:

- exact fixed Skill URL
- existing workspace/local-owner headers
- exact conversation binding
- explicit owner action only
- one-request pending guard
- bounded result/error UI
- TypeScript typecheck
- frontend lint.

### Batch 02 — security + regression

Add dedicated D117 frontend security acceptance.

Run:

- D109-D116 targeted frontend/security regression
- relevant D91-D100 workspace/client-state regression
- full backend regression
- frontend typecheck
- frontend lint
- frontend production build
- git diff --check.

Then perform Guided UI acceptance.

## 29. Out of scope

D117 V1 excludes:

- Skill catalog UI
- Skill picker
- arbitrary skill_id entry
- multiple Skills
- Skill chaining
- agent loops
- AI-selected Skills
- automatic Skill invocation
- owner-created Skills
- third-party Skills
- provider/model selection
- Tool/Module/connector/credential-bearing Skills
- Cloud fallback
- D107 proposal generation from Skill output
- D108 Apply from Skill output
- Skill invocation persistence
- backend changes
- database migration
- new frontend framework or test framework.

## 30. Completion criteria

D117 is complete only when:

- this frozen design exists
- fixed owner-facing Skill control exists
- exact D116 Skill URL is used
- selected workspace/conversation state is preserved
- local-owner marker is preserved
- no automatic invocation exists
- duplicate pending invocation is prevented
- output remains non-authoritative
- D107/D108 authority remains separate
- provider/model/tool/module/connector/credential authority is unchanged
- backend production remains unchanged
- targeted security/regression passes
- full backend regression passes
- frontend typecheck/lint/build pass
- Guided UI acceptance passes
- working tree is clean
- closeout evidence is recorded.

## 31. Next milestone direction

D117 does not pre-authorize any future generic Skill UX.

Any catalog/listing UI, multiple Skill support, Skill composition, autonomous
selection, proposal generation, or execution integration requires a separately
approved and frozen milestone.
