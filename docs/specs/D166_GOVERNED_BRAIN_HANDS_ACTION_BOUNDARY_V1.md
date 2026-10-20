# D166 — Governed Brain → Hands Action Boundary V1

**Source baseline:** `e3462745d3f35f0823eca0d3f5049757fe8bb69f`
**DB baseline:** `0016_cognitive_quality_observability`
**D166 DB revision:** none

## Purpose

D166 is the first bounded Arms / Hands implementation milestone after Brain V1 Source Complete.

It adds the smallest governed boundary required to accept a non-authoritative Brain action intent, resolve only an existing exact execution capability, classify the action risk deterministically, and prepare the existing structured owner-approval flow.

D166 does **not** add a new execution engine. Existing D35–D47 planning, permission, approval, authorization, runtime, audit, workspace, and connector execution boundaries remain authoritative.

`DECISION != PERMISSION != EXECUTION`

## Frozen reuse rule

D166 must reuse `ExecutionPlanner`, `ExecutionGuard`, `ExecutionApprovalService`, `CapabilityPermissionPolicy`, `CommandExecutionCoordinator`, `ToolRuntime`, `ModuleRuntime`, `ExecutionAuditTrail`, existing workspace isolation, and existing connector-specific execution/security lanes.

D166 must not duplicate those systems.

## Exact implementation scope

D166 is limited to exactly six paths:

1. this specification;
2. `backend/app/contracts/governed_action.py`;
3. `backend/app/services/governed_action.py`;
4. `backend/tests/test_d166_governed_action.py`;
5. `backend/tests/test_d166_governed_action_security.py`;
6. `backend/tests/test_d166_governed_action_reproducibility.py`.

No existing production path is modified.

## Action intent boundary

`ActionIntent` is non-authoritative data only. It may identify source Brain turn, source artifact digest, target kind, adapter, operation, and bounded parameters.

It must not carry owner approval, permission decision, execution authorization, execution-ready plan, confirmation bypass, tool/runtime authority, retry authority, or rollback authority.

Creating an `ActionIntent` performs no tool/module execution and grants no permission.

## Risk classification

D166 defines four frozen classes:

- `R0`: no side effect / read-only;
- `R1`: reversible write, but only when the exact capability is explicitly allowlisted as reversible;
- `R2`: external side effect;
- `R3`: process execution, high-impact write, irreversible write, or a write whose reversibility is not explicitly established.

Mapping is conservative:

- `none` or `read` → `R0`;
- `write` + exact reversible-capability allowlist → `R1`;
- `write` without explicit reversible proof → `R3`;
- `external_side_effect` → `R2`;
- `process_execution` → `R3`;
- unknown / malformed input → fail closed.

Risk classification is not permission.

## Confirmation

D166 never creates owner approval from Brain text, model output, retrieved content, webpage content, or tool output.

The existing `ExecutionApprovalService` remains the only D166 path for creating a structured approval proposal.

If the exact capability policy says owner approval is not required, D166 V1 stops before creating any approval ticket and returns `structured_confirmation_not_required`. D166 V1 does not auto-execute no-confirmation actions.

The existing exact plan digest, expiry, workspace scope, and single-use approval semantics remain unchanged.

## Verification

Execution success and result verification are distinct:

`execution_succeeded != result_verified`

A `VerificationResult` may be `not_attempted`, `failed`, `unverified`, or `verified`.

`verified` requires explicit verification evidence. A successful execution alone may only be `unverified`.

D166 does not invent verification evidence.

## Recovery

D166 records recovery semantics only. It performs no retry and no automatic rollback.

`RecoveryState` distinguishes `no_side_effect`, `partial_or_unknown_side_effect`, and `completed_side_effect`.

Recovery disposition is one of `not_required`, `rollback_available`, or `manual_recovery_required`.

Unknown side-effect state never authorizes blind retry.

## Brain / Hands authority separation

Brain V1 remains unable to authorize execution, approve its own action, call `ToolRuntime` or `ModuleRuntime` through D166, broaden capability permission, bypass structured confirmation, or create execution authority through prompt or retrieved text.

`GovernedActionBoundary` may only validate, classify, and prepare the existing approval proposal. It has no `execute`, `approve`, `deny`, `retry`, `rollback`, or provider-call method.

## Persistence / provider / runtime boundary

D166 adds no DB table, no model, no repository, no Alembic revision, no API endpoint, no frontend, no provider/LLM call, no connector call, no browser, no scheduler/background worker, no autonomous loop, no new tool/module runtime, and no composition-root wiring.

D166 therefore grants no new live execution authority.

## Test matrix

D166 tests must establish:

A. exact D161 source baseline identity;
B. Brain / execution separation remains intact;
C. ActionIntent is non-authoritative;
D. intent preparation performs no execution;
E. R0/R1/R2/R3 classification is deterministic and fail-closed;
F. exact existing capability permission is required;
G. Brain intent cannot create owner approval;
H. structured approval remains exact-plan-bound;
I. route/capability changes cannot inherit authority;
J. existing single-use approval / replay protection remains available;
K. successful execution is not automatically verified;
L. recovery is descriptive and never retries automatically;
M. audit remains the existing execution audit surface;
N. untrusted content grants no authority;
O. representative D35–D47 / Brain / workspace security regressions remain valid;
P. D166 creates no execution path of its own.

## Exit rule

D166 passes only when the exact six-path implementation is deterministic, no existing production file is modified, no migration/provider/live-call surface is added, and Brain action intent can reach only a governed approval proposal — never execution authority.

Passing D166 does not authorize broader Hands implementation, browser control, background autonomy, or unrestricted tool use.
