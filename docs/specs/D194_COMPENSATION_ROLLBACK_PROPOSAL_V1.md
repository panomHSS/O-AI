# D194 Compensation / Rollback Proposal — V1.1 Contract, Candidate V2

Baseline: `9de700e4dea5d9182f79d249090a8a603fbcfb83`.
This standalone candidate is not installed, production-accepted, or runtime-wired.

## Design authority and traceability

Owner's isolated-remediation instruction approves this precedence: Design Amendment
V1.1 overrides conflicting Design Freeze V1 clauses; Candidate V2 Implementation
Reconciliation V1 translates the amended design; Exact 6-Path Scope remains binding.
Historical draft/pending labels in supplied documents do not override that instruction.

| Requirement | Implementation |
| --- | --- |
| Amendment 2; reconciliation B | Closed five-pair status/reason mapping below |
| Amendment 3; reconciliation C-D | Exact scope/binding validation; one private query and snapshot; validate every receipt before deduplication |
| Amendment 4; reconciliation E | No cache, TTL, clock, or claim of race freedom |
| Amendment 5; reconciliation F-G | Immutable minimal projection, null recovery kind, hard-false flags, canonical versioned fingerprint |
| Amendment 6-7; reconciliation A,H | Exactly six candidate files and real evaluator/security/fixed-vector tests |

## Classification

| Evidence | Status | Reason |
| --- | --- | --- |
| One valid blocked/rejected receipt | not_required | execution_not_attempted |
| One valid completed receipt, any valid result | manual_recovery_required | completed_execution_postcondition_unverified |
| Multiple distinct valid matching receipts | conflict | contradictory_execution_evidence |
| Missing source, empty/None snapshot, retrieval exception, single unavailable execution | unavailable | recovery_evidence_unavailable |
| Invalid binding/source shape, non-tuple history, any invalid/unmatched receipt | unavailable | recovery_evidence_invalid |

`execution_not_attempted` describes recorded non-completion only, never physical
absence of effects. Invalid evidence takes precedence over conflicts. More than one
distinct matching receipt is conflict even when results agree; no receipt wins.
No rollback_candidate, compensation_candidate, or executable recovery payload exists.

## Server-only evidence boundary

`GovernedCompensationRollbackProposalEvaluator(workspace_scope=..., history_source=...)`
requires exact validated WorkspaceScope. The source is a server-injected read-only
`retrieve(query)` dependency. `evaluate(*, binding)` accepts only the current exact
D181 binding. Extra receipt/history/recovery/attestation/authority arguments are rejected
by the Python interface before any retrieval.

The private frozen query contains workspace, intent digest, target kind, capability,
adapter, operation, effect and risk. It exposes no approval/request/plan identifiers.
Every returned exact D191 recorded receipt is revalidated, including its fingerprint,
internal owner-decision/authorization/result consistency, safe identity, and exact
approval/request/plan lineage against the binding. These private lineage values never
enter the public projection or direct proposal hash fields. D181 has no independent
owner-decision field; D194 does not manufacture one or reauthorize old approvals.

The exact tuple is one coherent snapshot. Duplicate fingerprints collapse only after
all entries pass validation. A missing source/None snapshot is unavailable; malformed
source shape or non-tuple snapshot is invalid. Exceptions expose no private detail.
No network, database, provider, runtime or persistence implementation is introduced.

**Required production acceptance gate:** server composition must demonstrate source
provenance, workspace access control, and coherent-snapshot behavior. A callable,
Python type, or unkeyed SHA-256 cannot authenticate a source. No caller trust flag is
accepted. Unit-test fixtures are not production attestations. This standalone artifact
cannot detect a malicious but interface-compatible source; do not install/expose it
with an untrusted source. Production trust is NOT VERIFIED by candidate tests.

## Freshness and mutation

Each evaluation retrieves once, without caching caller-held receipts. Binding values
are captured before retrieval and compared after retrieval; receipts are validated
and copied for projection. Later evaluations revalidate new snapshots and changed
bindings. No guarantee of freshness, immutable physical objects, concurrent atomicity,
or post-read validity is inferred. D181 expires_at is not treated as a history TTL.
An apparently coherent stale tuple cannot be distinguished from a current tuple by
this interface. Source coherence/currentness remains a deployment prerequisite.
Future execution requires an independent governed lane and fresh state/authority checks.

## Projection and canonical bytes

`GovernedCompensationRollbackProposal` is a frozen slots dataclass. Required fields
include status/reason, scoped workspace, contract/baseline/policy, manual-review flag,
null recovery_kind and all hard-false authority, reuse and automatic-action gates.
Fresh owner approval and new request requirement flags are also false: D194 offers
no executable action, and this never permits old authority reuse.

Coherent single-receipt outcomes include safe identity fields source_intent_digest,
target_kind, capability_id, adapter_id, operation, effect, risk_class, plus prior receipt
fingerprint, execution_status, postcondition_status and bounded result_status.
Unavailable and conflict suppress all identity/receipt fields and set fingerprint None.
Manual review is true only for manual_recovery_required and conflict.
Raw parameters, result output/error, provider payload, approval ID, execution request ID,
plan digest, conversation IDs, credentials and private errors are not projected.
Safe identity labels must themselves be governed, non-secret identifiers at composition.

Contract version: `o-ai.compensation-rollback-proposal.v1.1`.
Policy: `trusted_snapshot_nonexecuting_recovery_v1.1`.
Fingerprint includes every dataclass field except proposal_fingerprint, with WorkspaceId
serialized as its enum value. JSON uses sorted keys, compact separators, UTF-8,
ensure_ascii=False, allow_nan=False. It includes null recovery_kind and all false gates.
No timestamps/randomness/private lineage fields. The indirect D191 receipt digest binds
the verified receipt without exposing its private fields. The hash is evidence identity,
not a credential. The test module publishes five literal known vectors independently
serialized from the schema, not derived dynamically from the evaluator under test.

## Verification and scope

Only the two new production modules, three new test modules, and this spec are candidate
source. Baseline regression files remain untouched. Functional tests cover the mapping,
source failures, strict tuple contract, duplicate/conflict/invalid precedence, query
isolation and risk preservation. Security tests cover exact types, tampering, private
lineage, cross-workspace inputs, every false gate, forbidden inputs, projection privacy,
and production imports/calls. Reproducibility tests cover literal vectors, independent
canonical serialization, rereads, changed snapshots/bindings and order invariance.

Run D194 and D193/D192/D191/D181/D166/D45 suites in the isolated baseline overlay.
The D166 global ban on any 0017 migration is NOT waived; any failure must be disclosed
and separately reviewed for D194. See the external verification report for actual
counts, limitations and candidate recommendation. Tests do not constitute production
acceptance. Installation, staging, commit, push and rollout remain unauthorized.
