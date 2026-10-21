# D176 — Explicit Action Directive Semantic Draft Producer V1

**Source baseline:** `8f4fc26d92abb8fa70cdda38c0dee3a854fb594b`
**Parent milestone:** D175 — CLOSED / ACCEPTED
**DB baseline:** `0016_cognitive_quality_observability`
**Migration:** none

## Purpose

D176 deterministically converts only the existing explicit `/action` grammar
into the existing D174 `StructuredActionSemanticDraft`.

`Explicit syntax != lineage`

`Semantic draft != semantic input`

`D176 = explicit syntax -> semantic meaning`

`D172 = semantic meaning -> candidate route`

`semantic production != owner approval`

D167 remains authoritative for current-lineage validation later in the existing
governed-action chain.

D176 performs **no free-text -> semantic action inference**.

## Frozen input

The producer accepts only `message: str` and `project_id: UUID | None`.
The project ID is server-owned context supplied by the caller. D176 does not
query conversation, Project, repository, database, provider, connector, or
network state.

## Frozen explicit boundary

Only normalized text equal to `/action`, or beginning with `/action` followed
by whitespace, enters the grammar. Embedded, example, `/actionable`, and
ordinary-chat text are not applicable.

## Frozen grammar and semantics

Exactly these historical D46 directives are supported:

- `/action system info` -> `system_info`;
- `/action system health` -> `system_health`;
- `/action workspace overview` -> `workspace_overview`;
- `/action project snapshot` -> `project_snapshot`;
- `/action echo <value>` -> `echo`;
- `/action list <path>` -> `workspace_list`;
- `/action stat <path>` -> `workspace_stat`;
- `/action read <path>` -> `workspace_read_text`.

Matching is exact and case-sensitive. There is no synonym, fuzzy, prefix,
nearest-match, case-folding, or AI fallback.

D176 emits no `target_kind`, adapter ID, operation, capability, permission,
approval, or execution metadata. D172 remains responsible for semantic meaning
-> candidate route mapping.

## Project snapshot

With `project_id`, the draft carries
`{"project_id": str(project_id)}` and no missing information.

Without `project_id`, parameters are empty and
`missing_information=("project_id",)`.

D176 never invents or looks up a project ID.

## Outcome

`ExplicitActionSemanticDraftProductionOutcome` contains exactly:

- `status`;
- `reason_code`;
- `draft`;
- `contract_version`.

Contract version:
`o-ai.explicit-action-semantic-draft-producer.v1`.

Statuses and reasons are exact:

- `not_applicable` -> `no_explicit_action_directive`;
- `invalid` -> `explicit_action_directive_invalid`;
- `semantic_ready` -> `structured_action_semantic_draft_ready`.

Only `semantic_ready` carries an existing D174 semantic draft.

## Fail-closed and authority boundary

Wrong input types fail with `TypeError`. Malformed explicit commands are
`invalid` and are never repaired or delegated to AI.

Natural-language Gmail, Calendar, GitHub, or plugin classification is outside
D176. Plaintext approval words carry no D176 authority.

D176 grants no authentication, lineage, mapping authority, permission,
approval, authorization, owner decision, persistence, or execution.

The service has no dependency on D172/D173/D174 binder/D175/D168/D170/D169/
D167/D166, D46, permission policy, approval service, runtime, provider,
connector, repository, model, database, scheduler, or worker.

## Production boundary

D176 is implemented in isolation and **composition is deferred**.

D176 is not composed or invoked from dependencies, normal Chat,
command orchestrator, cognitive executive, or D46 ChatActionBridge.

Successful D176 flow:

explicit `/action` syntax
-> D176
-> existing `StructuredActionSemanticDraft`
-> **STOP**.

## Exact implementation scope

`EXACT 0 MODIFIED + 6 ADDED = 6 PATHS`

1. `backend/app/contracts/explicit_action_semantic_draft_producer.py`
2. `backend/app/services/explicit_action_semantic_draft_producer.py`
3. `backend/tests/test_d176_explicit_action_semantic_draft_producer.py`
4. `backend/tests/test_d176_explicit_action_semantic_draft_producer_security.py`
5. `backend/tests/test_d176_explicit_action_semantic_draft_producer_reproducibility.py`
6. `docs/specs/D176_EXPLICIT_ACTION_SEMANTIC_DRAFT_PRODUCER_V1.md`

No existing source or test path is modified.

## Acceptance

D176 requires targeted functional/security/reproducibility tests, historical
D46 regression, D172-D175 structured-action regression, D166-D175 governed
regression, and full backend regression. No new skip/xfail debt is permitted.

D176 successful output remains non-authoritative semantic meaning and **STOP**.
