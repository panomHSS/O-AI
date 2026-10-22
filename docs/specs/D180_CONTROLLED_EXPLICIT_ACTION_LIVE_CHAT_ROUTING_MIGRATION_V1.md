# D180 — Controlled Explicit Action Live Chat Routing Migration V1

**Source baseline:** `c67dea151d26517e24ff63fb35b1a9aaa918614a`
**Parent milestone:** D179 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D180 migrates only explicit `/action` Chat turns behind an owner-controlled
server route mode while preserving the D46 legacy route as the rollback path.

`default = legacy`

Allowed route modes are exactly `legacy` and `cognitive`.

D180 does not migrate Plugin, Calendar, Gmail, clarification, or structured
approval decision routes.

## Routing rule

One `/action` turn selects exactly one authority path.

Legacy:

`/action -> D46`

Cognitive:

`/action -> CommandInputPipeline -> CommandOrchestrator -> D179 -> D177 -> governed action stack -> at most Owner Review -> STOP`

Dual-run, shadow invocation, and comparison invocation are forbidden because
both authority paths may create real pending approval proposals.

## Local request boundary

The local-request marker is checked before D46 proposal creation, command
normalization, AI/Cognitive invocation, or D179 handoff.

An untrusted explicit `/action` request stops with HTTP 403.

## Same-turn lineage

The exact `CommandRequest` object passed to `CommandOrchestrator.process_chat`
is handed to D180 and D179 unchanged.

The D178 `CommandOrchestrationOutcome` from that same call is handed to D179
unchanged.

This preserves the current D174/D167 same-turn lineage rule.

No second CognitiveExecutive invocation is allowed.

## Cognitive control-lane behavior

D180 does not bypass D144.

If production orchestration yields no cognitive outcome, D179 returns
`cognitive_outcome_unavailable`; D180 projects `unavailable` and stops.

`no cognitive -> legacy fallback`

No synthetic cognitive outcome, lineage, action intent, or approval is created.

## Projection

D179 statuses project to the existing Chat action schema:

- `prepared_for_owner_review` -> `pending_approval`
- `cognitive_outcome_unavailable` -> `unavailable`
- `lineage_unavailable` -> `unavailable`
- `approval_unavailable` -> `unavailable`
- `not_applicable` -> `rejected`
- `invalid` -> `rejected`
- `needs_clarification` -> `rejected`
- `unsupported` -> `rejected`
- `intent_rejected` -> `rejected`

The exact downstream reason code is preserved.

## Owner Review approval identity

Only `prepared_for_owner_review` may expose approval metadata.

D180 reads the already-created approval through the exact nested outcome chain:

`D179 -> D177 -> D175 -> D173 -> D170 -> D167 -> D166 preparation -> approval`

Every layer must be the expected contract type and preserve
`prepared_for_owner_review` plus the exact reason code.

The approval must already be pending and contain a proposal.

D180 never calls `propose()`, never rebuilds an approval, and never creates a
second pending proposal.

Malformed owner-review chains fail closed.

## Conversation persistence

For cognitive explicit-action turns:

- API reply is the exact `CommandOrchestrationOutcome.chat_turn.reply`;
- conversation ID is the exact `chat_turn.conversation_id`;
- D180 does not call `complete_turn()` a second time;
- D180 does not replace the persisted cognitive reply with synthetic action text.

The route returns immediately after action projection and does not invoke
`ProjectUpdateTurnOrchestrator`.

## AI mode

If `ChatRequest.ai_mode` is present, D180 uses the same
`CommandOrchestrator.process_chat(..., ai_mode=...)` semantics as normal Chat.

D180 creates no new AI routing policy.

## Plugin compatibility

`ChatActionBridge.is_plugin_action_request()` remains on D46 in both D180 route
modes.

Calendar, Gmail, and existing structured approval/clarification paths are
unchanged.

## Authority ceiling

D180 grants no permission, approval, authorization, or execution authority.

D180 does not execute tools/modules, dispatch work, consume an Owner decision,
or alter capability policy.

The maximum state remains Owner Review and STOP.

## Exact implementation scope

`EXACT 4 MODIFIED + 7 ADDED = 11 PATHS`

Modified:

1. `backend/app/core/config.py`
2. `backend/app/api/dependencies.py`
3. `backend/app/api/v1/chat.py`
4. `backend/tests/test_d179_explicit_action_cognitive_handoff_security.py`

Added:

5. `backend/app/contracts/explicit_action_live_chat_routing.py`
6. `backend/app/services/explicit_action_live_chat_routing.py`
7. `backend/tests/test_d180_explicit_action_live_chat_routing.py`
8. `backend/tests/test_d180_explicit_action_live_chat_routing_api.py`
9. `backend/tests/test_d180_explicit_action_live_chat_routing_security.py`
10. `backend/tests/test_d180_explicit_action_live_chat_routing_reproducibility.py`
11. `docs/specs/D180_CONTROLLED_EXPLICIT_ACTION_LIVE_CHAT_ROUTING_MIGRATION_V1.md`

No Chat schema, frontend, DB model/repository, migration, D166-D179 production,
CommandOrchestrator, CognitiveExecutive, or ChatActionBridge production file is
modified.

## Acceptance matrix

A. route configuration defaults to legacy and accepts only legacy/cognitive;
B. D180 projection contract is immutable and authority-free;
C. local guard occurs before both live routes;
D. legacy `/action` invokes D46 only;
E. cognitive `/action` invokes command normalization/orchestration then D179;
F. exact command/orchestration identity is preserved;
G. no second cognitive invocation or cognitive-to-legacy fallback exists;
H. exact D179 status/reason projection is deterministic;
I. Owner Review exposes only the exact existing approval;
J. malformed approval chains fail closed;
K. cognitive reply/conversation identity is preserved without duplicate completion;
L. ProjectUpdate is not invoked for explicit `/action`;
M. Plugin/Calendar/Gmail legacy routes remain unchanged;
N. D180 adds no execution authority or side-effect runtime;
O. D166-D179, D46, and cognitive-routing regressions remain green;
P. full backend regression remains green.

## Exit rule

D180 passes only when explicit `/action` can be switched by Owner configuration
between the exact legacy D46 route and the exact D179 cognitive governed route
without dual invocation, fallback authority, duplicate approval, duplicate
conversation completion, schema expansion, or execution authority.

The milestone ends at Owner Review and **STOP**.
