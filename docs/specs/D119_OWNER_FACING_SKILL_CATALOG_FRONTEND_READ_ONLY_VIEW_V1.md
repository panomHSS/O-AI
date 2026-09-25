# D119 — Owner-Facing Skill Catalog Frontend Read-Only View V1

Status: FROZEN DESIGN

## 1. Purpose

D119 adds a bounded read-only Skill Catalog view to the existing Engineering owner panel.

D119 consumes D118 metadata only. It does not create a Skill picker, generic launcher,
catalog-driven invocation path, registration flow, installation flow, or execution authority.

The existing D117 fixed Skill invocation remains independent and fixed to:
`engineering.investigation_change_plan`.

## 2. Reused boundaries

D119 must preserve D109 Engineering owner boundaries, D113 Engineering Investigation
semantics, D114 Skill metadata, D115 bounded invocation bridge, D116 invocation API,
D117 fixed-Skill frontend control, D118 read-only catalog API, and the existing local
owner request marker.

Visibility is not execution authority.

## 3. Exact frontend placement and endpoint

Production UI placement:
- `frontend/components/chat/engineering-owner-panel.tsx`

Catalog endpoint:
- `GET /api/v1/engineering/skills`
- frontend path `/engineering/skills`

The request must use the existing generic `apiRequest`, not `workspaceApiRequest`.

Request:
- method `GET`
- header `X-OAI-Local-Request: 1`
- no request body
- no workspace id/header requirement
- no conversation id
- no skill id argument.

D119 adds no backend endpoint and no backend production change.

## 4. Explicit load rule

Catalog metadata is loaded only after an explicit owner action.

No automatic catalog fetch may occur on:
- app/component mount
- Engineering panel open
- Chat send/assistant response
- workspace switch
- conversation switch
- D117 invocation
- investigation rendering.

While the GET is pending, duplicate load is disabled. There is no automatic retry
or fallback. A later explicit owner action may load again after completion.

## 5. Public frontend types

Frontend catalog item fields are exactly:
- `skill_id`
- `version`
- `display_name`
- `description`
- `task_kind`
- `required_ai_capability_ids`
- `input_kind`
- `context_kind`
- `output_kind`

Catalog response contains exactly:
- `skills`

No provider, adapter, model, credential, handler, callable, Tool, Module, connector,
invoke URL, execution target, workspace id, conversation id, proposal, approval, or
Apply field is added.

## 6. Presentation-only rule

The owner panel may display the returned metadata and empty/error/loading states.

Catalog order must remain the server-provided D118 order.

The UI must identify the catalog as read-only metadata and must not imply that
visibility grants permission or execution capability.

## 7. No picker / no catalog-driven invocation

D119 must not add:
- Skill dropdown
- selectable Skill rows
- arbitrary `skill_id` input
- `selectedSkillId` / `activeSkillId`
- first-Skill auto-selection
- Invoke / Run / Execute control on catalog items
- dynamic invoke URL or HTTP method
- callback from a catalog item into D116/D117
- automatic selection of the D117 fixed Skill.

D117 invocation request construction must remain unchanged in authority.

## 8. Authority exclusions

D119 adds no:
- provider/model selection
- Tool/Module/connector/credential authority
- shell/process/Git/network authority
- D107 proposal generation
- approval/deny authority
- D108 Apply authority
- database table or Alembic migration
- localStorage/sessionStorage Skill authority
- catalog or selection persistence.

Transient in-memory catalog/loading/error state is allowed.

## 9. Exact expected production scope

Expected D119 production files are exactly:
1. `frontend/types/chat.ts`
2. `frontend/lib/api-client.ts`
3. `frontend/components/chat/engineering-owner-panel.tsx`

Expected unchanged production includes:
- `backend/app/**`
- `backend/alembic/**`
- `frontend/app/chat/page.tsx`
- `frontend/components/chat/chat.tsx`
- `frontend/components/chat/engineering-proposal-card.tsx`
- `frontend/components/workspace/workspace-provider.tsx`

If implementation requires another production file, D119 must be re-frozen first.

## 10. Expected tests

Expected tests:
- `backend/tests/test_d119_skill_catalog_frontend.py`
- `backend/tests/test_d119_skill_catalog_frontend_security.py`

Tests may inspect frontend source in the established D109-D118 acceptance style.
No new frontend test framework is introduced.

## 11. Acceptance requirements

Automated acceptance must prove:
- read-only catalog section exists
- explicit owner load action exists
- exact GET `/engineering/skills` is used
- `X-OAI-Local-Request: 1` is sent
- generic `apiRequest` is used
- `workspaceApiRequest` is not used for catalog read
- no request body/workspace/conversation/skill parameter is sent
- exact D118 public fields are typed
- server ordering is preserved
- duplicate pending load is prevented
- no automatic catalog fetch exists
- no picker/arbitrary Skill selection exists
- catalog items cannot invoke D116
- D117 fixed Skill invocation remains unchanged
- backend production and migrations remain unchanged.

Regression includes targeted D109-D119, relevant D91-D100 client/workspace tests,
full backend, frontend TypeScript no-emit typecheck, lint, production build, and
`git diff --check`.

Use the validated isolated writable `D:` pytest temp strategy if Windows Local Temp
permission errors recur.

## 12. Guided UI acceptance

Because D119 changes owner-facing UI, Guided UI acceptance is required.

Owner observations:
1. Engineering owner panel opens normally.
2. Read-only Skill catalog section is visible.
3. Catalog is not fetched before explicit owner load.
4. One explicit load displays trusted catalog metadata.
5. Catalog items expose no Invoke/Run/Execute action.
6. Existing D117 fixed Skill invocation still behaves independently.
7. Workspace/conversation switching does not invoke or select a Skill.
8. Catalog loading/error state never appears as execution authority.

## 13. Batch plan

Batch 01:
- add exact public catalog frontend types
- add bounded GET helper
- add read-only catalog section
- add primary D119 acceptance test
- run frontend typecheck/lint.

Batch 02:
- add D119 security test
- verify no picker/selection/invocation authority
- verify backend/migrations unchanged
- run targeted D109-D119 + relevant D91-D100
- run full backend
- run frontend typecheck/lint/build
- run `git diff --check`
- perform Guided UI acceptance.

## 14. Out of scope

D119 excludes Skill picker, generic catalog invocation, multiple-Skill UX,
Skill detail routing, Skill chaining/orchestration, autonomous/AI-selected Skills,
owner-created/third-party Skills, dynamic registration/installation/activation,
provider/model selection, Tool/Module/connector/credential-bearing Skills,
workspace-specific Skill policy, backend changes, database migrations, and
D107/D108 integration.

## 15. Completion criteria

D119 is complete only when the frozen design exists, the read-only catalog frontend
is implemented within the exact frozen production scope, no catalog-driven execution
authority exists, D117 remains fixed and independent, backend/migrations remain
unchanged, automated regression passes, Guided UI acceptance passes, working tree is
clean, and closeout evidence is recorded.
