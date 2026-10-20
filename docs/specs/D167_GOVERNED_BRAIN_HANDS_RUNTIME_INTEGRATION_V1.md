# D167 — Governed Brain → Hands Runtime Integration V1

**Source baseline:** `524d7cb332525aaacb632e2bf8e2d5ef5c52d05d`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose
D167 adds the smallest canonical production composition seam that can take an
already-structured, non-authoritative `ActionIntent`, prove that it belongs to
the current eligible server-owned cognitive turn, and delegate only to D166
`GovernedActionBoundary`.

`DECISION != PERMISSION != EXECUTION`

D167 does not make normal Chat infer tools from free text and adds no new hand/tool/module/connector capability.

## Frozen flow
`ActionIntent`
→ current `CommandRequest`
→ current `CognitiveExecutiveOutcome`
→ turn/workspace/final-artifact lineage validation
→ D166 `GovernedActionBoundary`
→ existing `CapabilityPermissionPolicy`
→ existing `ExecutionApprovalService`
→ at most `prepared_for_owner_review`.

D167 never reaches `ToolRuntime` or `ModuleRuntime` directly.

## Lineage
Before D166 preparation:
1. command is `chat.message`;
2. intent source turn equals current request id;
3. cognitive outcome turn equals current request id;
4. outcome workspace equals current `WorkspaceScope`;
5. outcome is `COMPLETED` + `eligible`;
6. exactly one `publication_accepted` event exists;
7. it is `FINALIZING`, `READY`, and has a digest;
8. intent source artifact digest exactly matches that finalized digest.

Mismatch fails closed before approval creation. Lineage is not permission,
owner approval, or execution authorization.

## Runtime outcomes
- `no_action_intent`
- `intent_rejected`
- `prepared_for_owner_review`
- `approval_unavailable`

`prepared_for_owner_review` is not authorization or execution.
If D166 returns `structured_confirmation_not_required`, D167 preserves the
rejection and does not auto-execute.

## Exact scope
Exactly 1 modified + 5 added:
- modified `backend/app/api/dependencies.py`
- added this spec
- added `backend/app/contracts/governed_action_runtime.py`
- added `backend/app/services/governed_action_runtime.py`
- added `backend/tests/test_d167_governed_action_runtime.py`
- added `backend/tests/test_d167_governed_action_runtime_security.py`

No CognitiveExecutive, CommandOrchestrator, planner, guard, runtime, connector,
provider, model, repository, Alembic, frontend, Docker, dependency, or env
modification.

## Production composition
`dependencies.py` composes D166 from the existing production
`CapabilityPermissionPolicy`, workspace-scoped `ExecutionApprovalService`, and
current `WorkspaceScope`, then composes D167 over it.

D167 V1 does not automatically invoke the seam from normal Chat because no
approved structured Brain action producer exists yet.

## Security
Prompt text, retrieved context, Trusted Experience, webpage/tool/provider output,
and Brain natural-language replies cannot create an ActionIntent, owner approval,
permission, ExecutionAuthorization, or execution.

Passing D167 does not mean that Brain can autonomously select tools.
