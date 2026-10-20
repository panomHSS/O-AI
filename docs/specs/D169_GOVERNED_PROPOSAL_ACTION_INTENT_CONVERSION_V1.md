# D169 â€” Governed Proposal â†’ ActionIntent Conversion V1

**Source baseline:** `faf2f12742e5ec2adab18174444ba978664691c6`
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D169 adds the smallest deterministic, non-authoritative conversion boundary
between D168 `StructuredActionIntentProposal` and the existing D166
`ActionIntent`.

`Conversion != Permission`

`Conversion != Approval`

`Conversion != Execution`

`ActionIntent creation != authority`

## Frozen flow

`D168 StructuredActionIntentProposal`
-> D169 governed deterministic conversion
-> D166 `ActionIntent`
-> **STOP**

D169 does not invoke D167. A later separately governed integration milestone
may pass the converted intent to D167 for current-turn/workspace/final-artifact
lineage validation.

## Input and status boundary

D169 accepts only `StructuredActionIntentProposal`; it does no free-text-to-tool
inference. Exactly two statuses exist:

- `not_convertible`
- `converted_for_lineage_validation`

The reason mapping is fixed:

- `not_applicable` -> `proposal_not_applicable`
- `needs_clarification` -> `proposal_needs_clarification`
- `unsupported` -> `proposal_unsupported`
- `proposal_ready` -> `proposal_converted_for_lineage_validation`

Only `proposal_ready` may create the existing D166 `ActionIntent`.

## Exact mapping and lineage

D169 copies exactly:

- `source_turn_id`
- `source_artifact_digest`
- `target_kind`
- `adapter_id`
- `operation`
- `parameters`

D169 preserves lineage but does not validate whether the turn, workspace,
cognitive outcome, publication event, or artifact is current.

`Lineage preservation != Lineage validation`

Those checks remain D167 authority.

## Capability and governance boundary

D169 performs no capability discovery or permission resolution.

`Semantic completeness != Capability permission`

A complete proposal may convert even when its adapter or operation is not
permitted. Downstream governance remains responsible for rejection.

D168 governance requirements remain future requirements only. D169 does not
create owner approval, permission, risk decisions, execution authorization, or
execution authority.

## Determinism and forbidden surfaces

D169 is deterministic and uses no clock, randomness, provider, connector,
network, persistence, database, API, frontend, scheduler, or state mutation.

It has:

- no D167 invocation;
- no `GovernedActionBoundary.prepare()` call;
- no `CapabilityPermissionPolicy` call;
- no `ExecutionApprovalService` call;
- no tool/module runtime call;
- no production composition-root wiring.

## Exact implementation scope

D169 consists of **exactly six added paths** and zero modified paths:

1. `docs/specs/D169_GOVERNED_PROPOSAL_ACTION_INTENT_CONVERSION_V1.md`
2. `backend/app/contracts/governed_action_intent_conversion.py`
3. `backend/app/services/governed_action_intent_conversion.py`
4. `backend/tests/test_d169_governed_action_intent_conversion.py`
5. `backend/tests/test_d169_governed_action_intent_conversion_security.py`
6. `backend/tests/test_d169_governed_action_intent_conversion_reproducibility.py`

## Acceptance matrix

A. exact D168 source baseline;
B. immutable bounded outcome with exactly two statuses;
C. only `proposal_ready` creates D166 `ActionIntent`;
D. `not_applicable` fails closed;
E. `needs_clarification` fails closed;
F. `unsupported` fails closed;
G. lineage copied exactly;
H. route copied exactly;
I. parameters preserve exact semantics and D166 immutability;
J. deterministic equivalent input/output;
K. governance requirements never become approval evidence;
L. no capability/permission lookup;
M. no D167 or governed-boundary invocation;
N. no approval/authorization/execution;
O. no provider/connector/persistence/scheduler/production wiring;
P. D166-D168 and representative regressions remain valid.

## Exit rule

D169 passes only when:

`proposal_ready` -> D169 -> D166 `ActionIntent` -> **STOP**

Passing D169 authorizes no D167 production wiring, permission, approval,
execution, autonomous tool selection, or background autonomy.