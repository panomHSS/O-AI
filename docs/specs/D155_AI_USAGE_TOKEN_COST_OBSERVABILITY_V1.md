# D155 — AI Usage / Token & Cost Observability V1

Status: implementation authorized
Baseline: `dc6f67387e49ebcbc35ad51092587e804719624f` (D154 closed)
Scope: backend usage metering, durable accounting, pricing, aggregation, and read-only API only. Frontend/UI is deferred.

## Objective

D155 makes O-AI able to measure provider-reported AI token usage and estimate standard token cost without changing routing, model selection, Cognitive behavior, Memory, Trusted Experience, or execution authority.

The implementation does not invoke an AI provider to calculate usage. It consumes usage attached to the provider response that O-AI already receives.

## Provider usage contract

OpenAI Responses usage is normalized to the provider-neutral `AIUsageMeasurement` contract:

- input tokens
- cached input tokens
- cache-write tokens
- output tokens
- reasoning tokens
- total tokens
- provider pricing mode / service tier

The OpenAI production usage-aware path requests `service_tier="auto"`, which is the API default behavior, so the provider can report the tier actually used without D155 changing routing or model behavior. D155 V1 prices only confirmed standard/default-tier token usage. Other or missing pricing modes remain measured but `billing_status=unknown` rather than receiving a guessed cost.

`cached_input_tokens` and `cache_write_tokens` are partitions of input usage. `reasoning_tokens` is a diagnostic subset of output usage and is never billed a second time by D155.

Missing or malformed usage is `unavailable`; it is never silently converted to zero.

## Durable ledger

Each successful authorized AI invocation produces at most one `ai_usage_events` row. Invocation identity is a SHA-256 digest over the authorized request ID, execution-plan digest, adapter ID, authorized model ID, and the D155 identity-domain label. The request ID itself is also reduced to a domain-separated SHA-256 digest before persistence; raw request IDs are not stored in the D155 ledger.

The ledger is append-only on the supported SQLite and PostgreSQL migration paths and has database triggers blocking update/delete. Duplicate recording of the same invocation is idempotent. The ledger stores no prompt, completion, Context text, Memory text, API key, OAuth secret, or chain-of-thought.

Local AI invocations are recorded with usage/billing `not_applicable`; O-AI does not claim that local compute has an OpenAI API price.

## Pricing snapshot

Pricing version: `openai-standard-2026-10-19-v1`.

D155 uses an immutable server-owned snapshot and integer nano-USD arithmetic. It does not fetch pricing at runtime and does not use binary floating point as authoritative accounting.

Supported V1 price identities include current standard token rates for GPT-5.5 and the GPT-5.6 Sol/Terra/Luna/Cyber family. Unknown model identities or non-default/unknown pricing modes remain measurable with `billing_status=unknown` and `estimated_cost=null`.

For supported long-context models, requests with more than 272,000 input tokens apply the current full-request input/cache multiplier and output multiplier encoded in the snapshot. Tool-call fees and other non-token charges are outside D155 V1.

## Runtime semantics

Usage metering runs only after `AIRuntime` has validated and completed an authorized AI invocation successfully. Metering persistence uses an isolated short-lived transaction. Any metering failure is best-effort observability failure and must not turn a successful AI response into an AI/chat failure.

D155 adds no retry, fallback, provider call, model call, route decision, or autonomous cost optimization.

## Read-only API

`GET /api/v1/ai-usage/summary`

Optional filters:

- `since`: timezone-aware lower bound
- `until`: timezone-aware exclusive upper bound
- `model_id`: exact model identity

The response is aggregate-only and includes request counts, cloud/local counts, measured/unmetered counts, priced/unknown-cost counts, token totals, estimated priced cost, pricing versions, and deterministic per-model aggregates.

No per-invocation identifiers or prompt/completion data are exposed by the D155 API.

## Acceptance invariants

1. Provider success + metering failure remains provider success.
2. Provider failure creates no fabricated token/cost ledger row.
3. Missing usage is not zero usage.
4. Unknown pricing is not zero cost.
5. Cached input is not billed again as uncached input.
6. Reasoning tokens are not added on top of output tokens.
7. Local AI has no OpenAI API billing estimate.
8. Duplicate metering for one invocation does not duplicate cost.
9. The ledger remains append-only across database reopen.
10. Usage/cost has no route, policy, Cognitive, Memory, or Trusted Experience authority.
11. D155 performs no frontend/UI work.
