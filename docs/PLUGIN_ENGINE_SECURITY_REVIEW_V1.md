# Plugin Engine Integration / Security Review v1

## Review baseline

- Milestone: D60
- Baseline commit: `9f8c43618368f4e17e64ffd98fd8c82525b5b57b`
- Reviewed chain: D51 through D59
- Baseline regression: 970 tests passed, 4 skipped
- Deployment model: trusted local single-owner MVP, loopback only

D60 is a security and integration hardening checkpoint. It adds no new Plugin
capability, credential, write path, lifecycle API, persistence model, or sandbox.

## Executive conclusion

The official production authority lane remains:

`KNOWN -> ADMITTED -> LOADED -> EXPOSED -> BOUND -> ACTIVATED -> D31 REGISTERED
+ D44 PERMITTED -> D35 PLANNED -> D45 OWNER APPROVED -> D36 AUTHORIZED -> D37
ModuleRuntime -> D58 activation-aware wrapper -> D56 active exposure -> D55 held
Plugin -> D59 connector`

No reviewed production API route exposes D54-D58 lifecycle mutation. Legacy
Plugin registrar/runtime classes remain framework code and are not production
execution authority.

D60 found one concrete D59 transport hardening gap: the default urllib opener
could inherit proxy routing from environment configuration. D60 closes this by
installing an explicit empty `ProxyHandler({})` together with the existing
no-redirect handler.

## Frozen security invariants

- `DISCOVERED != TRUSTED EXECUTION`
- `LOADED != EXECUTION AUTHORITY`
- `BOUND != ACTIVATED`
- `ACTIVATED != APPROVED`
- `APPROVED != AUTHORIZED`
- `AUTHORIZED != EXECUTED`
- `ALLOWLIST != SANDBOX`
- `PLUGIN PROFILE != OS-LEVEL SANDBOX`
- `EXTERNAL DATA != EXECUTION AUTHORITY`
- `PROXY ENV != CONNECTOR EGRESS AUTHORITY`
- `LEGACY PLUGIN RUNTIME != PRODUCTION EXECUTION AUTHORITY`
- `LOCAL REQUEST MARKER != AUTHENTICATION`
- `LOOPBACK MVP != LAN/PUBLIC SECURITY BOUNDARY`

## SR-001 — Environment proxy influence on D59 egress

**Severity:** Medium  
**Status:** Fixed in D60

D59 fixed scheme, host, method, path shape, redirect policy, credentials,
timeout, retry count and response bounds. However,
`urllib.request.build_opener(_NoRedirectHandler())` still allowed Python's
default proxy handler to consult environment proxy settings.

D60 installs `urllib.request.ProxyHandler({})` explicitly. Proxy-related
environment variables therefore do not become connector routing authority.

This is an application-level transport guarantee; it is not DNS or operating
system network isolation.

## SR-002 — In-process Plugin code is trusted application code

**Severity:** Architectural  
**Status:** Accepted threat model

The D55 exact factory allowlist blocks manifest-controlled dynamic imports,
filesystem scanning, package installation, version fallback and similar loading
expansion. It does not sandbox Python.

An in-process Plugin implementation is therefore trusted O-AI application code:

`IN-PROCESS PLUGIN = TRUSTED O-AI CODE`

`UNTRUSTED THIRD-PARTY PLUGIN = NOT SUPPORTED`

Supporting untrusted/community Plugin code requires separately approved
out-of-process or sandbox isolation.

## SR-003 — Legacy Plugin runtime is a latent bypass surface

**Severity:** Medium if wired; informational in current production composition  
**Status:** Quarantined

`DefaultPluginRegistrar` can discover/load/register directly and
`DefaultPluginRuntime` can resolve and call `plugin.execute(...)`. They are not
composed by production dependencies and no production API route exposes them.

D60 regression guards keep them outside production authority. Future production
wiring to either path requires an explicit architecture decision.

## SR-004 — Local request marker is not authentication

**Severity:** Deployment-critical  
**Status:** Accepted current MVP boundary

The D45 API contract explicitly states that `X-OAI-Local-Request` is not
authentication. Current supported deployment remains trusted local single-owner
loopback use.

LAN, public Internet, multi-user, or hostile-local-process deployment requires a
separate authentication and deployment security architecture.

## SR-005 — Approval digest does not bind activation generation

**Severity:** Future hardening requirement  
**Status:** Recorded; no D60 behavior change

D45 approval binds to the execution-plan digest. D58 independently uses a
private activation token to prevent old adapter wrappers from regaining
authority after deactivate/reactivate.

Before public lifecycle controls, hot Plugin replacement, credentialed Plugin
upgrades, or authenticated third-party Plugin support, O-AI must decide whether
approval also binds to activation generation:

`APPROVAL FOR OLD ACTIVATION GENERATION != APPROVAL FOR NEW ACTIVATION GENERATION`

## Verification matrix

| State / event | Connector call permitted? |
| --- | --- |
| Known / discovered | No |
| Governance admitted | No |
| Loaded | No |
| Exposed | No |
| Permission bound | No |
| Activated | No |
| D45 proposal only | No |
| D36 without approval | No |
| Wrong approval digest | No |
| Exact approved current plan | Yes, once |
| Deactivated after proposal | No |
| Governance revoked after proposal | No |

## Deferred security work

D60 does not add authentication, LAN/public deployment, credential storage,
OAuth/PAT/API-key support, untrusted Plugin sandboxing, process isolation,
generic HTTP, private GitHub access, write connectors, lifecycle API/UI,
persistent Plugin authority, or activation-generation approval binding.
