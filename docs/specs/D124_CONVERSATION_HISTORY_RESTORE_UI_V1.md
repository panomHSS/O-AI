# D124 — Conversation History / Restore UI V1

Status: DESIGN FROZEN
Baseline: D123 remote-frozen main at `d46ae3638d8615bf6c4aef1a718e3d826645d72a`

## Purpose

Add one bounded owner-facing Conversation History / Restore UI to Chat so an
existing persisted conversation in the currently selected workspace can be
explicitly restored without manually editing browser localStorage.

D124 is a frontend usability milestone. It grants no new AI, execution,
mutation, credential, Plugin, Tool, Module, Skill, approval, Apply, or
cross-workspace authority.

## Existing server surfaces reused

D124 reuses the existing workspace-scoped APIs:

- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`

No new backend route, schema, service, repository operation, database column,
migration, or persistence model is authorized by D124.

## Exact production scope

D124 production changes are limited to exactly:

- `frontend/components/chat/chat.tsx`
- `frontend/lib/api-client.ts`
- `frontend/types/conversation.ts`

Tests and this design specification are not production scope.

Any additional production file requires a separately reviewed D124 design
amendment before implementation.

## Conversation summary contract

Frontend may define a Conversation summary type matching the existing server
summary fields only:

- `workspace_id`
- `id`
- `title`
- `created_at`
- `updated_at`
- `project_id`

No execution, provider, adapter, model, credential, Tool, Module, Plugin,
Skill, approval, or Apply field may be added to the history contract.

## Workspace-scoped history loading

The frontend may add one `listConversations(workspaceId)` client helper using
the existing workspace request boundary.

Every returned Conversation summary must belong to the requested workspace.
A mismatched workspace item fails closed.

The frontend must preserve the server-provided ordering. D124 does not create
a second client-side authority for conversation ordering.

History state is cleared/remounted on workspace switch and may never fall back
to another workspace or implicit default workspace.

## Conversation History UI

Chat gains one owner-facing `Conversation history` surface.

The surface may display bounded read-only summary information including:

- title
- updated time
- active/restored state

Selecting a conversation must require one explicit owner click.

D124 does not authorize automatic selection of a different conversation.

## Exact restore behavior

On explicit owner selection:

1. Capture the selected workspace and conversation ID.
2. Request the existing Conversation detail through the workspace-scoped API.
3. Validate the returned workspace.
4. Validate the returned conversation ID exactly matches the requested ID.
5. If the Conversation has a Project, resolve that Project through the same
   exact workspace before adopting the restored state.
6. Only after all required reads and validation succeed:
   - set the active conversation ID;
   - restore persisted Chat messages;
   - restore the associated Project presentation when applicable;
   - persist the exact workspace-scoped active Conversation key.
7. Clear pending-new-Project state when restoring an existing conversation.
8. Clear unsent Chat draft text and stale presentation errors/state that could
   otherwise be carried into a different conversation.

Failed validation or failed required reads must not replace the currently
active conversation and must not overwrite its saved active Conversation key.

## Exact ID binding

`getConversation(workspaceId, conversationId)` must fail closed if the server
response does not match both:

- the requested workspace; and
- the requested conversation ID.

Browser summary metadata is not sufficient authority to restore a
conversation without the exact detail read.

## Selection concurrency

A restore already in progress must be duplicate/concurrency guarded.

D124 must not allow multiple overlapping owner selections to race and allow a
stale earlier result to overwrite a later Conversation context.

## New Conversation behavior

Existing `New Conversation` remains an explicit client-state action.

It may:

- clear the workspace-scoped active Conversation key;
- clear current Chat messages and Conversation state;
- reset Chat AI mode according to existing behavior;
- clear current Project presentation.

It must not:

- delete the persisted Conversation;
- mutate previous Conversation history;
- call the Conversation DELETE API;
- auto-create a new Conversation before the next explicit Chat turn.

The Conversation History UI remains available so the owner can explicitly
return to a persisted Conversation.

## History refresh

History may be refreshed from the existing read-only list API after a
successful Chat turn so newly created/updated Conversations become visible.

A history refresh is presentation-only and grants no authority over the Chat
turn that created or updated the Conversation.

## AI mode boundary

Conversation restoration does not persist or infer a Conversation-specific AI
provider/model setting.

Restore must not silently convert previous Chat history into new AI execution.

D124 may reset transient Chat AI mode to the existing safe/default UI behavior
when changing active Conversation, but may not introduce new routing rules.

## Engineering boundary

The Engineering owner panel remains keyed to the exact workspace and active
Conversation.

Changing the active Conversation must remount Conversation-bound Engineering
presentation state.

Live process-local Engineering workflow presentation/correlation state may be
re-read through existing Engineering APIs while the backend process remains
alive. D124 does not add durability to that state, and a backend restart may
legitimately clear it.

Transient non-authoritative AI drafts and investigation presentation state
must not be transferred from one Conversation to another.

Conversation history selection must never invoke:

- D110 Engineering AI Draft;
- D117 investigation Skill;
- D123 Engineering AI Draft Skill;
- D107 proposal creation;
- approval;
- D108 Apply.

## No action replay

Restoring stored Chat messages is display/history restoration only.

D124 must not replay, retry, or automatically execute any historical:

- AI request;
- Action;
- Calendar operation;
- Gmail operation;
- Tool;
- Module;
- Plugin;
- Skill;
- proposal;
- approval;
- Apply operation.

Display-only data that was intentionally not persisted does not gain new
persistence through D124.

## Security invariants

D124 must preserve all existing D91-D123 workspace and execution boundaries.

In particular:

- no implicit Personal or Company fallback;
- no cross-workspace Conversation lookup fallback;
- no browser-supplied workspace authority beyond the existing exact
  `X-OAI-Workspace` routing boundary;
- no new localStorage key containing execution authority;
- no arbitrary route construction from Conversation metadata;
- no retry against another workspace;
- no automatic AI/Skill invocation from `useEffect`;
- no persisted browser-side approval or execution authority.

## Explicitly out of scope

D124 does not add:

- Conversation delete UI;
- Conversation rename;
- search;
- filtering;
- pin/favorite;
- folders;
- pagination;
- bulk actions;
- conversation import/export;
- backend Conversation APIs;
- database changes or migrations;
- authentication or authorization;
- LAN/public deployment;
- generic Skill launcher;
- Local AI model/profile selection;
- AI-generated conversation selection;
- automatic restore of a different conversation.

These require separately frozen milestones.

## Dedicated tests

D124 implementation must add dedicated tests covering at least:

1. exact workspace-scoped Conversation list client;
2. fail-closed workspace mismatch in list results;
3. fail-closed detail Conversation ID mismatch;
4. explicit owner-click restoration only;
5. no AI/Skill/action invocation from history loading or selection;
6. New Conversation does not delete history;
7. failed restore preserves current active Conversation;
8. Project association restores only from the selected exact Conversation;
9. workspace switch does not leak Conversation summaries or selected state;
10. selection concurrency/stale-result protection;
11. Engineering Conversation remount remains isolated;
12. no backend production/database/migration change.

Historical D91-D123 security and frontend regression tests remain required.

## Guided UI acceptance

D124 Guided UI Acceptance must demonstrate:

1. at least two persisted Conversations are visible in Personal history;
2. `New Conversation` clears active Chat state but does not remove history;
3. selecting an old Conversation restores its persisted messages;
4. refreshing the browser restores the newly selected active Conversation;
5. Project-bound Conversation presentation restores correctly when applicable;
6. switching Personal -> Company shows only Company history;
7. switching back does not cross-contaminate active Conversation state;
8. history loading/selection causes no AI, Skill, Action, proposal, approval, or
   Apply execution;
9. a live process-local Engineering workflow remains bound to its original
   Conversation while the backend process remains alive; a backend restart may
   legitimately clear that presentation/correlation state;
10. transient Engineering draft/investigation state does not leak across
    Conversation switches;
11. Git repository remains unchanged by UI restore operations.

## Implementation staging

D124 implementation is expected to proceed only after this design freeze.

Suggested controlled batches:

- Batch 01: Conversation summary type, workspace list client, exact restore
  helper/state, owner-facing history UI.
- Batch 02: dedicated D124 security acceptance, historical regression,
  frontend typecheck/lint/build, and Guided UI Acceptance.

No implementation batch may push until its required gates are complete and the
owner explicitly authorizes push.

## Frozen boundary

D124 is specifically Conversation History / Restore UI V1.

It is not a generic conversation-management milestone and does not expand
O-AI execution authority.
## Amendment A — Engineering workflow lifetime clarification

Guided UI acceptance exposed an existing D109 lifetime boundary that D124 does
not change.

`EngineeringOwnerBindingStore` is bounded process-local
presentation/correlation state. It is not durable database persistence and
does not survive a backend process restart.

Therefore D124 Conversation History restoration must preserve exact
conversation/workspace binding for any live Engineering workflow, but D124
does not require a workflow that existed before a backend restart to
reappear afterward.

This amendment changes no D124 production scope, API, database, migration,
execution authority, or implementation requirement.
