# D181 — Owner-Approved Governed Execution Integration V1

## Status

Implementation candidate specification frozen from the owner-approved D181
Design Reconciliation A–P, Design Freeze V1, and Implementation
Reconciliation / Test Matrix V1.

Baseline:

`b4deb3c63b5b04eb75d7ecbe6184917f80e6332e`

## Exact implementation scope

**EXACT 4 MODIFIED + 7 ADDED = 11 PATHS**

Modified:

1. `backend/app/api/dependencies.py`
2. `backend/app/api/v1/chat.py`
3. `backend/app/api/v1/execution_approvals.py`
4. `backend/app/api/exception_handlers.py`

Added:

5. `backend/app/contracts/owner_approved_governed_execution.py`
6. `backend/app/services/owner_approved_governed_execution.py`
7. `backend/tests/test_d181_owner_approved_governed_execution.py`
8. `backend/tests/test_d181_owner_approved_governed_execution_api.py`
9. `backend/tests/test_d181_owner_approved_governed_execution_security.py`
10. `backend/tests/test_d181_owner_approved_governed_execution_reproducibility.py`
11. `docs/specs/D181_OWNER_APPROVED_GOVERNED_EXECUTION_INTEGRATION_V1.md`

## Frozen authority model

`Brain thinks != may execute`

`Proposal != approval`

`Approval != authorization bypass`

The cognitive stack may prepare an existing D45 pending approval and D181 may
record immutable correlation evidence for that approval. Only an explicit
owner decision at the existing execution-approval API may begin the decision
lane.

D181 provides **no direct ToolRuntime / ModuleRuntime dispatch** and owns no
execution adapter. After validation it delegates to the exact existing D45
`ExecutionApprovalService`, which consumes the one-time ticket and passes the
exact stored `CommandRequest` to the existing D40 coordinator. D40 must re-plan
and `ExecutionGuard` must re-authorize under current policy before dispatch.

## Cognitive binding

The process-local bounded sidecar binding records workspace, conversation,
source turn, source publication artifact digest, governed intent digest,
approval identity, execution request identity, reviewed plan digest, target,
capability, adapter, operation, effect, risk class, and expiry.

The binding is correlation evidence only and grants no permission, approval,
authorization, retry, rollback, or execution authority.

The binding is created only after D180 returns `pending_approval` with coherent
D179 -> D177 -> D175 -> D173 -> D170 -> D167 -> D166 -> D45 lineage, and
before that pending approval is exposed in the Chat API response.

## V1 risk ceiling

Approve is permitted through the cognitive-governed lane only for **R0**:

- effect `none`
- effect `read`

R1, R2 and R3 cognitive approvals fail closed with
`cognitive_execution_risk_not_permitted` and make zero Tool/Module runtime
calls. The owner may still Deny the ticket.

## Owner decision lane

A bound cognitive approval:

1. requires the existing local-request guard;
2. requires the exact workspace;
3. requires D181 R0 eligibility for Approve;
4. delegates the exact approval ID and supplied plan digest to D45;
5. relies on D45 single-use consumption / expiry / digest integrity;
6. relies on D40 mandatory re-planning and re-authorization;
7. returns the existing structured execution decision response;
8. creates no second cognitive turn or assistant reply;
9. stops at the execution result — **STOP**.

Deny is allowed after workspace validation and still delegates to D45, which
yields the existing `owner_approval_denied` blocked execution outcome.

## Legacy compatibility

An execution approval that has no D181 cognitive binding follows the pre-D181
D45 path exactly. **legacy D45 behavior remains unchanged**.

D46, plugin approvals and other non-cognitive execution approvals therefore do
not require a D181 binding.

## Fail closed

D181 rejects malformed/mismatched cognitive lineage, workspace mismatch,
approval/proposal mismatch, reviewed plan-integrity mismatch, binding
conflict/capacity failure, and non-R0 Approve.

There is no cognitive -> legacy fallback for a bound approval, no automatic
retry, no automatic re-proposal, no auto-approval, no parameter reconstruction,
and no direct adapter invocation.

## Explicit non-goals

D181 V1 does not add free-text autonomous execution, multi-step execution,
write/external/process cognitive execution, Calendar/Gmail mutation migration,
retry/rollback orchestration, execution-result -> Brain feedback, learning
authority, database migrations, or frontend redesign.
