# D123 — Engineering AI Draft Fixed Skill Frontend Invocation Control V1

Status: FROZEN DESIGN

## 1. Purpose

D123 adds one explicit owner-facing frontend control for invoking the exact static
Engineering AI Draft Skill route completed by D122:

`engineering.ai_draft`

D123 does not create a generic Skill launcher.

D123 reuses the completed D110 AI Draft owner inputs/result UX, the completed D117
fixed-Skill frontend invocation pattern, and the completed D122 exact static Skill
owner API.

The frozen D123 rule is:

EXPLICIT OWNER ACTION
+ EXACT CURRENT WORKSPACE
+ EXACT CURRENT CONVERSATION
+ EXACT OWNER PATH
+ EXACT OWNER INSTRUCTION
+ FIXED TRUSTED SKILL URL
→ D122 STATIC OWNER SKILL ROUTE
→ EXISTING D121 BRIDGE
→ EXISTING OWNER-BOUND D110 WORKFLOW
→ EXISTING D110 NON-AUTHORITATIVE DRAFT RESULT

and never:

CATALOG ITEM → DYNAMIC SKILL SELECTION → GENERIC EXECUTION

A visible control adds transport and presentation only. It grants no new backend
authority.

## 2. Reused completed boundaries

D123 must preserve and reuse:

- D91-D100 workspace/client-state isolation;
- D106 Engineering repository observation;
- D107 immutable Engineering proposal authority;
- D108 controlled Engineering Apply authority;
- D109 Engineering owner panel and exact conversation binding;
- D110 AI-assisted Engineering drafting UX and non-authoritative draft state;
- D111 task-aware AI routing;
- D114 SkillDescriptor / SkillCatalog;
- D115 bounded SkillInvocationBridge;
- D116 investigation-specific owner-facing Skill invocation API;
- D117 fixed investigation Skill frontend control;
- D118 read-only Skill catalog API;
- D119 metadata-only Skill catalog frontend;
- D120 second built-in Skill metadata;
- D121 explicit `engineering.ai_draft` bridge mapping;
- D122 exact static `engineering.ai_draft` owner API.

D123 must not duplicate or weaken those boundaries.

## 3. Exact fixed Skill identity

D123 V1 supports exactly one new fixed frontend Skill identity:

`engineering.ai_draft`

The owner does not type, select, alias, normalize, discover, or derive the Skill ID.

The frontend must not read the Skill ID from D119 catalog state.

No Skill dropdown or Skill picker is added.

No arbitrary `skill_id` field is added.

## 4. Exact endpoint

The D123 control calls exactly:

`POST /api/v1/engineering/skills/engineering.ai_draft/invoke`

The URL is fixed in trusted frontend source.

D123 must not:

- construct an invoke URL from catalog metadata;
- interpolate `skill.skill_id`;
- accept a Skill ID from browser input;
- route through `/engineering/skills/{skill_id}/invoke` dynamically;
- substitute the direct D110 route for the D123 Skill control.

The existing direct D110 control remains separately available and continues to call:

`POST /api/v1/engineering/ai-drafts`

## 5. Frontend placement

D123 V1 extends the existing:

`frontend/components/chat/engineering-owner-panel.tsx`

No new page, Skill center, catalog detail page, modal registry, picker, or navigation
surface is introduced.

The existing Chat composition remains authoritative for selected workspace and
conversation state.

## 6. Existing D110 draft inputs are reused

D123 reuses the existing owner-controlled D110 inputs already present in the
Engineering owner panel:

- `draftPath`
- `draftInstruction`
- exact current `conversationId`.

D123 must not introduce a second path authority or second instruction source merely
for the Skill route.

The owner still chooses the exact repository-relative path and exact instruction.

Blank/whitespace-only path or instruction must not dispatch.

If no current conversation exists, the D123 control must not dispatch.

## 7. Exact request contract

The D123 request body is exactly the existing D110 logical request:

- `conversation_id`
- `relative_path`
- `instruction`

D123 adds no owner-supplied:

- `workspace_id`
- `skill_id`
- repository root
- operation selector
- provider ID
- adapter ID
- model ID
- tool ID
- module ID
- connector ID
- credential reference
- proposal selector
- approval selector
- Apply selector.

Backend D122/D110 validation remains authoritative.

## 8. Request headers and transport

D123 must preserve the existing Engineering frontend request boundary:

- `X-OAI-Local-Request: 1`
- exact current `X-OAI-Workspace`
- `Content-Type: application/json`.

The D123 control must use the existing workspace-aware frontend transport:

`workspaceApiRequest<EngineeringAIDraftResponse>`

No default workspace is invented.

No workspace override is accepted from owner input.

The server remains authoritative for workspace/conversation validation.

## 9. Explicit invocation rule

D123 invocation occurs only after one explicit owner action on the fixed AI Draft
Skill control.

The control label is frozen as:

`Draft via Engineering Skill`

D123 must not invoke automatically on:

- component mount;
- Chat message send;
- assistant response;
- workspace switch;
- conversation switch;
- path edit;
- instruction edit;
- D119 catalog load;
- catalog item render;
- D110 draft result render;
- proposal creation;
- proposal approval;
- Apply.

One owner action causes at most one D122 HTTP request.

## 10. Pending / duplicate-submit rule

D123 must maintain a dedicated transient pending guard for the fixed AI Draft Skill
request.

While a D123 invocation is pending for the current workspace/conversation context,
the D123 control must be disabled.

D123 adds no:

- retry loop;
- fallback request;
- alternate Skill;
- second provider path;
- duplicate dispatch;
- queued autonomous invocation.

The existing direct D110 `Draft with Local AI` pending behavior remains distinct and
unchanged in authority.

## 11. Exact response contract

D123 reuses:

`EngineeringAIDraftResponse`

The response remains the existing D110 non-authoritative draft projection.

Before adopting a successful response into visible browser draft state, the frontend
must verify at minimum:

- `response.conversation_id === conversationId`
- `response.relative_path === draftPath.trim()`

A response that no longer matches the exact requested conversation or target must
fail closed in the frontend and must not replace the currently displayed draft.

D123 must not convert the response into:

- Engineering Investigation output;
- D107 proposal;
- approval artifact;
- Apply payload;
- generic Skill result;
- Tool result;
- Module result.

## 12. Existing D110 draft state and result UX are reused

A successful D123 response may populate the existing non-authoritative D110 browser
draft state:

- `aiDraft`
- `aiDraftContent`.

The existing D110 presentation remains authoritative for the draft UX:

- target;
- draft operation;
- AI adapter visibility;
- editable draft text;
- `Discard Draft`;
- `Create Proposal from Draft`.

D123 does not add a second authority-bearing draft store.

Browser draft state remains non-authoritative.

## 13. D110 direct drafting control remains available

D123 does not remove, rename, repurpose, or silently reroute the existing:

`Draft with Local AI`

control.

That direct D110 control continues to call:

`POST /api/v1/engineering/ai-drafts`

D123 adds a distinct fixed Skill transport path over the same bounded D110 capability.

The two controls must remain distinguishable in source and behavior.

D123 must not make the direct D110 helper call the D122 Skill endpoint.

## 14. Create Proposal from Draft remains separate

D123 must not automatically create a proposal after a Skill draft succeeds.

The existing explicit owner action:

`Create Proposal from Draft`

remains the only transition from displayed draft text into the existing D107/D109
proposal flow.

That action continues to submit only:

- `conversation_id`
- `operation`
- `relative_path`
- `proposed_content`

through the existing proposal path.

D107 still re-observes repository state and remains authoritative for base state and
proposal digest.

D123 response metadata does not become D107 authority.

## 15. No D107 / D108 authority

D123 must not:

- create a D107 proposal automatically;
- approve or deny a proposal;
- create an Apply payload;
- invoke D108;
- mutate repository files;
- call filesystem write adapters;
- convert Skill output directly into Apply authority;
- treat AI draft metadata as proposal authority.

D110 remains AI assistance, not mutation authority.

## 16. Existing D117 investigation Skill control remains independent

The completed D117 fixed control remains exactly for:

`engineering.investigation_change_plan`

Its exact URL remains:

`/engineering/skills/engineering.investigation_change_plan/invoke`

D123 must not:

- replace the D117 handler;
- parameterize D117 with a Skill ID;
- share a generic Skill dispatcher with D117;
- turn D117 and D123 into a Skill selector;
- derive either fixed URL from catalog metadata;
- change the D117 investigation request/response contract.

D117 remains an investigation-specific fixed control.

D123 remains an AI-draft-specific fixed control.

They are two explicit bounded controls, not a generic multi-Skill frontend.

## 17. D119 catalog remains metadata-only

The D119 read-only catalog section must remain metadata-only.

D123 must not add to catalog items:

- Invoke;
- Run;
- Execute;
- Select;
- Use Skill;
- radio controls;
- checkboxes;
- clickable execution rows;
- callbacks into D117 or D123;
- dynamic invoke URLs.

D123 must not add:

- `selectedSkillId`;
- `activeSkillId`;
- first-Skill auto-selection;
- catalog-driven invocation;
- catalog-derived HTTP method;
- catalog-derived request schema.

Catalog visibility remains separate from execution authority.

## 18. No generic Skill frontend runtime

D123 must not create:

- generic Skill request dispatch;
- generic response dispatch;
- Skill handler registry;
- handler dictionary;
- runtime-selected request schema;
- runtime-selected response schema;
- dynamic callable registry;
- reflection-based handler lookup;
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

D123 adds one exact fixed owner control only.

## 19. Provider / model / runtime authority remains unchanged

D123 adds no:

- provider selector;
- adapter selector;
- model selector;
- endpoint selector;
- credential selector;
- runtime selector;
- fallback selector;
- retry policy;
- Tool target;
- Module target;
- generic Skill execution target.

D110/D111 and D35/D36/D49 remain authoritative behind the API.

## 20. Backend remains unchanged

D123 is frontend-only.

Expected unchanged production includes:

- `backend/app/**`
- `backend/alembic/**`

D123 must not change:

- D122 static route;
- D116 dynamic route;
- D121 bridge mapping;
- D110 workflow;
- Engineering API dependencies;
- Skill catalog metadata.

If backend production changes are required, D123 must stop and be re-frozen before
modification.

## 21. Shared frontend API/types remain unchanged

D123 is expected to require no changes to:

- `frontend/lib/api-client.ts`
- `frontend/types/chat.ts`

The existing `EngineeringAIDraftResponse` type is reused.

The existing `workspaceApiRequest` transport is reused directly in the owner panel,
matching the established D117 fixed-Skill frontend pattern.

If D123 implementation evidence requires modifying shared frontend API/types, D123
must stop and be re-frozen before widening production scope.

## 22. Persistence

D123 adds no:

- database table;
- Alembic migration;
- Skill invocation persistence;
- durable AI draft store;
- browser-persisted Skill selection;
- localStorage Skill authority;
- sessionStorage Skill authority;
- queued invocation state.

Transient in-memory pending/error/result state is allowed.

## 23. Expected production scope

Expected D123 production change is exactly one file:

1. `frontend/components/chat/engineering-owner-panel.tsx`

Expected unchanged production includes:

- `backend/app/**`
- `backend/alembic/**`
- `frontend/lib/api-client.ts`
- `frontend/types/chat.ts`
- `frontend/components/chat/chat.tsx`
- `frontend/components/chat/engineering-proposal-card.tsx`
- `frontend/components/workspace/workspace-provider.tsx`

If implementation requires another production file, D123 must stop and be re-frozen
before modification.

## 24. Intentionally superseded historical assertion

D123 intentionally supersedes only the D122 security assertion that encoded the
D122 API-only rule:

`/engineering/skills/engineering.ai_draft/invoke`

must not appear in the frontend owner panel.

The historical test currently expressing that rule is:

`backend/tests/test_d122_engineering_ai_draft_skill_owner_api_security.py`

specifically:

`test_d122_frontend_does_not_gain_ai_draft_skill_launcher`

D123 may update only that intentionally superseded frontend-absence assertion as
needed to reflect the new exact fixed D123 control.

All remaining D122 security properties must remain intact, including:

- exact static backend route;
- exact route ordering;
- exact D110 request contract;
- exact fixed `ENGINEERING_AI_DRAFT_SKILL_ID` bridge invocation;
- no direct D110 workflow bypass;
- D116 investigation route unchanged;
- no D107/D108 authority;
- no generic execution/runtime authority.

Historical tests must not be weakened merely to make D123 pass.

## 25. Expected new D123 tests

Expected focused tests:

- `backend/tests/test_d123_engineering_ai_draft_skill_frontend.py`
- `backend/tests/test_d123_engineering_ai_draft_skill_frontend_security.py`

Tests may inspect frontend source in the established D110/D117/D119 acceptance style.

No new frontend test framework is introduced.

Exact filenames may change only if repository naming evidence requires it before
implementation commit.

## 26. Automated acceptance requirements

Automated acceptance must prove at minimum:

1. exact fixed D123 URL
   `/engineering/skills/engineering.ai_draft/invoke` exists in the owner panel;
2. exact fixed URL appears only in the intended D123 control path;
3. D123 uses `workspaceApiRequest<EngineeringAIDraftResponse>`;
4. request includes `X-OAI-Local-Request: 1`;
5. exact selected workspace is supplied through existing transport;
6. request body carries current `conversation_id`;
7. request body carries exact trimmed `relative_path`;
8. request body carries exact trimmed `instruction`;
9. request body carries no `workspace_id`;
10. request body carries no `skill_id`;
11. no provider/model/tool/module/connector/credential selector is added;
12. no generic dynamic Skill URL is constructed;
13. D123 invocation requires explicit owner action;
14. blank path/instruction prevents dispatch;
15. absent conversation prevents dispatch;
16. duplicate pending D123 invocation is prevented;
17. no retry/fallback exists;
18. successful response must match current conversation;
19. successful response must match requested relative path;
20. mismatched response does not replace draft state;
21. successful D123 result populates existing non-authoritative D110 draft state;
22. existing editable draft behavior remains;
23. existing `Discard Draft` remains;
24. existing `Create Proposal from Draft` remains explicit and separate;
25. D123 invocation itself creates zero D107 proposal;
26. D123 invocation itself creates zero approval;
27. D123 invocation itself creates zero D108 Apply;
28. existing direct D110 `Draft with Local AI` control remains functional and distinct;
29. existing direct D110 endpoint `/engineering/ai-drafts` remains unchanged;
30. D117 fixed `engineering.investigation_change_plan` control remains unchanged;
31. D119 catalog items remain metadata-only and non-invokable;
32. no Skill picker/arbitrary Skill selection exists;
33. no browser Skill authority persistence exists;
34. backend production remains unchanged;
35. migrations remain unchanged;
36. exact one-file D123 production scope is preserved.

## 27. Regression requirements

Acceptance must include at minimum:

- D109 Engineering owner frontend/security regression;
- D110 AI Draft frontend/API/security regression;
- D111 task-aware AI routing frontend regressions;
- D112 cloud-egress/frontend regressions;
- D113 Engineering Investigation frontend/runtime/API regression;
- D114 Skill catalog/security regression;
- D115 Skill bridge/security regression;
- D116 Skill API/security regression;
- D117 fixed Skill frontend/security regression;
- D118 catalog API/security regression;
- D119 catalog frontend/security regression;
- D120 metadata/security regression;
- D121 bridge/security regression;
- D122 API/security regression with only the intentionally superseded frontend
  absence assertion updated;
- D35/D36/D49 authority regression;
- relevant D91-D100 workspace/client-state regression;
- full backend regression;
- frontend TypeScript no-emit typecheck;
- frontend lint;
- frontend production build;
- `git diff --check`.

Use isolated writable `D:\O-AI-test-temp` pytest temp roots if Windows temp
permissions require it.

## 28. Guided UI acceptance

Because D123 changes visible owner-facing UI, Guided UI acceptance is required.

Owner observations must prove at minimum:

1. select an existing workspace and conversation;
2. open the Engineering owner panel;
3. existing `Draft with Local AI` control remains visible;
4. new `Draft via Engineering Skill` control is visible;
5. enter one exact safe relative path and instruction;
6. one explicit D123 action invokes only the fixed `engineering.ai_draft` Skill;
7. pending state prevents duplicate D123 invocation;
8. returned result appears in the existing non-authoritative AI Draft UI;
9. owner can edit the draft;
10. editing the draft performs no repository mutation;
11. `Discard Draft` performs no repository mutation;
12. D123 result does not create a proposal automatically;
13. `Create Proposal from Draft` remains a separate explicit action;
14. existing D117 investigation Skill control remains independent;
15. D119 catalog items still expose no Invoke/Run/Execute action;
16. workspace switch does not auto-invoke D123;
17. conversation switch does not auto-invoke D123;
18. stale/mismatched D123 result is not presented as belonging to a different
    workspace/conversation/target;
19. existing D109 manual proposal workflow still works.

No browser automation is introduced solely for this acceptance.

## 29. Batch plan

### Batch 01 — exact fixed AI Draft Skill frontend control

- modify only `frontend/components/chat/engineering-owner-panel.tsx`;
- add exact fixed D122 static Skill URL;
- reuse current D110 draft path/instruction/conversation inputs;
- use existing workspace transport and local owner marker;
- add dedicated D123 pending/error state as needed;
- validate response conversation and target before adopting it;
- populate existing non-authoritative D110 draft state;
- preserve direct D110 control unchanged;
- preserve D117 fixed investigation control unchanged;
- preserve D119 catalog metadata-only behavior;
- update only the intentionally superseded D122 frontend-absence assertion;
- add primary D123 frontend acceptance test;
- run targeted D109-D123 regression;
- run frontend TypeScript no-emit typecheck;
- run frontend lint.

### Batch 02 — security, full regression, Guided UI acceptance

- add dedicated D123 frontend security acceptance;
- prove exact fixed Skill identity and URL;
- prove no arbitrary Skill selection or catalog-driven invocation;
- prove no automatic invocation/retry/fallback;
- prove no proposal/approval/Apply authority;
- prove D110 direct control remains distinct;
- prove D117 fixed investigation control remains unchanged;
- prove D119 catalog remains metadata-only;
- prove backend/migrations unchanged;
- run D35/D36/D49 authority regression;
- run relevant D91-D100 client/workspace regression;
- run targeted D109-D123 regression;
- run full backend regression;
- run frontend typecheck/lint/build;
- run `git diff --check`;
- perform Guided UI acceptance.

## 30. Out of scope

D123 explicitly excludes:

- Skill picker;
- catalog-driven invocation;
- arbitrary owner-provided `skill_id`;
- generic multi-Skill launcher;
- dynamic invoke URL construction;
- runtime-selected request schema;
- runtime-selected response schema;
- Skill chaining/orchestration;
- autonomous/AI-selected Skills;
- owner-created Skills;
- third-party Skill execution;
- dynamic Skill registration/installation/activation;
- provider/model selection;
- Tool/Module/connector/credential-bearing Skills;
- automatic D107 proposal creation;
- automatic approval;
- automatic Apply;
- durable draft persistence;
- Skill invocation history persistence;
- backend production changes;
- database migrations;
- redesign of D110 direct drafting;
- redesign of D117 investigation Skill UX;
- redesign of D119 catalog UX.

## 31. Stop conditions requiring re-freeze

D123 implementation must stop and return to Design if evidence requires any of:

- backend production modification;
- modification of `frontend/lib/api-client.ts`;
- modification of `frontend/types/chat.ts`;
- more than one frontend production file;
- generic Skill selection;
- catalog-driven execution;
- arbitrary Skill IDs;
- provider/model/runtime selection;
- Tool/Module/connector/credential authority;
- automatic proposal generation;
- automatic approval or Apply;
- new persistence or migration;
- material redesign of D110, D117, D119, D121, or D122.

Those are scope or authority changes and require a separately approved re-freeze.

## 32. Completion boundary

D123 is complete only when:

- this frozen design exists;
- exact fixed `engineering.ai_draft` frontend control is implemented;
- exact D122 static route is used;
- current workspace/conversation/path/instruction boundaries are preserved;
- existing D110 non-authoritative draft UX is reused;
- direct D110 drafting remains distinct and functional;
- D117 fixed investigation Skill control remains unchanged;
- D119 catalog remains metadata-only;
- D107/D108 authority remains separate;
- backend production remains unchanged;
- exact one-file frontend production scope is proven;
- automated security/regression acceptance passes;
- frontend typecheck/lint/build pass;
- Guided UI acceptance passes;
- final closeout passes;
- owner explicitly authorizes push.

No implementation work is authorized beyond this frozen design.
---

## Amendment A — Historical D120/D121 frontend-absence assertions

Status: FROZEN DESIGN AMENDMENT

Batch 01 regression evidence proved that four additional historical tests encode the
same pre-D123 frontend-absence rule already identified in Section 24.

Those assertions are:

1. `backend/tests/test_d120_second_builtin_skill_metadata.py`
   - `test_d120_catalog_visibility_does_not_rewire_fixed_frontend_invocation`
2. `backend/tests/test_d120_second_builtin_skill_security.py`
   - `test_d120_security_frontend_does_not_gain_catalog_driven_invocation`
3. `backend/tests/test_d121_engineering_ai_draft_skill_bridge.py`
   - `test_d121_d116_and_frontend_production_surfaces_remain_unchanged`
4. `backend/tests/test_d121_engineering_ai_draft_skill_bridge_security.py`
   - `test_d121_frontend_remains_fixed_investigation_control_and_metadata_catalog`

D123 intentionally supersedes only the sub-assertion in each test that requires
`engineering.ai_draft/invoke` to be absent from the Engineering owner panel.

Those tests may be updated only to recognize the exact fixed D123 static path:

`/engineering/skills/engineering.ai_draft/invoke`

while preserving their existing security properties:

- the D117 investigation Skill path remains exact and fixed;
- the D123 AI Draft Skill path remains exact and fixed;
- no `selectedSkillId` exists;
- no `activeSkillId` exists;
- D119 catalog rendering remains metadata-only;
- no catalog item becomes an invocation control;
- no dynamic Skill URL is introduced;
- D116 remains investigation-specific;
- D121 bridge authority remains bounded.

No production scope is widened by this amendment.

Expected D123 production scope remains exactly:

`frontend/components/chat/engineering-owner-panel.tsx`

This amendment authorizes only the minimum historical-test updates required by the
new fixed D123 frontend control. Historical security assertions must not otherwise be
removed or weakened.
