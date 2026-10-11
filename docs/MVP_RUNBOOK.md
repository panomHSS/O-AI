# O-AI MVP Runbook (D30)

The official MVP path is a trusted, single-owner native Windows machine. Backend and frontend bind only to `127.0.0.1`; use either `http://localhost:3000/chat` or `http://127.0.0.1:3000/chat`. Both loopback origins are explicitly allowed; do not expose this MVP to LAN or the public Internet.

## 1. Bootstrap

From the repository root in PowerShell, run:

```powershell
.\scripts\bootstrap.ps1
```

Bootstrap preserves existing `.env` and `frontend/.env.local`, creates missing files from their examples, creates `data/` and `knowledge/`, installs the existing backend/frontend dependencies, and migrates the configured SQLite database to Alembic head. It never creates credentials.

## 2. Configure

Review `.env`. OpenAI is optional; leave `OPENAI_API_KEY` blank when not using it. Local AI is off by default. To enable the verified Ollama deployment:

```text
OAI_LOCAL_AI_ENABLED=true
OAI_LOCAL_AI_BASE_URL=http://127.0.0.1:11434
OAI_LOCAL_AI_MODEL=qwen3.5:9b
```

Verify Ollama is running and has `qwen3.5:9b` before starting. Model storage is deployment-local; O-AI never hard-codes its path. Explicit Local AI requests never fall back to cloud AI.

`frontend/.env.local` defaults to the local API and gives chat a bounded 130-second timeout for Local AI. Other API calls retain their standard timeout.

### D125 Local AI task profiles

The backend resolves exactly two immutable profiles from server deployment settings after routing selects Local AI:

| Server-derived task | Profile ID | Used by | Reasoning when override is absent |
| --- | --- | --- | --- |
| General Chat (`general_chat`) | `local_ai.general_chat.v1` | Normal Chat routed to Local AI, including explicit Local AI mode | Runtime default (`None`) |
| Software Engineering (`software_engineering`) | `local_ai.software_engineering.v1` | D110 AI Draft, D113 Investigation, and D121/D123 fixed Engineering Skill delegation | `false` |

Common-only deployments remain valid. Both profiles inherit `OAI_LOCAL_AI_MODEL`, `OAI_LOCAL_AI_TIMEOUT_SECONDS`, and `OAI_LOCAL_AI_CONTEXT_LENGTH` unless their own override for that field is present. An absent model override inherits only the common model, an absent timeout only the common timeout, and an absent context length only the common context length. Neither profile inherits from the other profile.

The optional settings are:

| Field | General Chat override | Software Engineering override |
| --- | --- | --- |
| Model | `OAI_LOCAL_AI_GENERAL_CHAT_MODEL` | `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_MODEL` |
| Timeout seconds | `OAI_LOCAL_AI_GENERAL_CHAT_TIMEOUT_SECONDS` | `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_TIMEOUT_SECONDS` |
| Context length | `OAI_LOCAL_AI_GENERAL_CHAT_CONTEXT_LENGTH` | `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_CONTEXT_LENGTH` |
| Reasoning | `OAI_LOCAL_AI_GENERAL_CHAT_REASONING_ENABLED` | `OAI_LOCAL_AI_SOFTWARE_ENGINEERING_REASONING_ENABLED` |

Leave optional assignments absent or commented out to retain defaults; an empty assignment is not an instruction to inherit. Use literal `true` or `false` for explicit reasoning overrides. Timeout must be greater than zero and at most 600 seconds; context length must be an integer from 256 to 32768. Restart the backend after deployment configuration changes. Increasing a backend timeout does not increase the browser's bounded Chat timeout.

Each effective model must be installed and available under its exact configured name. For distinct Chat and Engineering models, set each model override to its intended installed model and verify both exact names in Ollama. The common model is only a configuration default, not an execution retry target. Missing models, runtime failures, rejected generation options, timeouts, and empty responses fail the selected request without automatic alternate-model, profile, or Cloud fallback. O-AI does not download or delete models to repair availability.

The browser, owner prompt, retrieved content, AI output, and Skill metadata cannot select arbitrary profile IDs or model IDs. D102 visibility and D103 configured-model load/unload controls remain unchanged; they are not D125 profile selectors or per-profile administration controls. Engineering drafts and investigations gain no proposal, Apply, or repository mutation authority.

### D125 troubleshooting

- **Runtime unavailable:** verify the configured Local AI runtime is running and reachable at `OAI_LOCAL_AI_BASE_URL`; restart the existing service as appropriate, then rerun smoke. Do not change network exposure or route to Cloud to bypass the failure.
- **Exact profile model missing:** compare the profile's effective model name with Ollama's installed names, including its tag and case. An installed model for the other profile does not satisfy this check. Model provisioning remains a separate owner operation.
- **Reasoning-policy conflict:** D113 supplies `reasoning_enabled=false` with its structured schema and temperature `0.0`. An explicit Engineering reasoning policy of `true` conflicts and fails before generation. Keep Engineering's default `false` for these paths; a prompt cannot override the policy. A runtime that rejects the configured options must also fail closed.
- **Common-only deployment:** omit all eight task-specific overrides. Both profiles use the common model/timeout/context while retaining their different reasoning defaults (`None` for Chat, `false` for Engineering).
- **Distinct models:** check both model overrides independently and verify both are installed. Smoke checks both models but exercises only General Chat inference. Test D110 and D123 through owner-guided acceptance to confirm Engineering output.

## 3. Start and verify

```powershell
.\scripts\start_mvp.ps1
.\scripts\smoke_mvp.ps1
```

The smoke script checks backend health/database revision, frontend reachability, safe API errors, request-ID behavior, and the public chat envelope. When Local AI is enabled it resolves each D125 effective model independently from `.env`, checks Ollama and both exact profile models, and sends its existing explicit Local AI normal Chat request through the General Chat profile, then reads the persisted conversation. Run smoke against backend processes restarted with the same deployment settings; shell/service environment overrides must agree with `.env`. Engineering inference is not exercised by this script. It performs no model download/delete or `.env` mutation. When only OpenAI is configured it runs the corresponding ChatGPT smoke. It reports a skip rather than inventing credentials when neither provider is configured.

Open [http://localhost:3000/chat](http://localhost:3000/chat) after smoke passes.

## 4. Stop

```powershell
.\scripts\stop_mvp.ps1
```

The stop script uses O-AI-owned PID files and command-line checks. It does not broadly terminate Python/Node processes and never stops Ollama.

## Deployment boundary

Docker and O-SERVER/production deployment are deferred. Docker support is retained, but it is not the D30 MVP quick start because its verification and Local AI host assumptions are not the official native-Windows path.
