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

## 3. Start and verify

```powershell
.\scripts\start_mvp.ps1
.\scripts\smoke_mvp.ps1
```

The smoke script checks backend health/database revision, frontend reachability, safe API errors, request-ID behavior, and the public chat envelope. When Local AI is enabled it checks Ollama/model availability and sends an explicit Local AI request through O-AI, then reads the persisted conversation. When only OpenAI is configured it runs the corresponding ChatGPT smoke. It reports a skip rather than inventing credentials when neither provider is configured.

Open [http://localhost:3000/chat](http://localhost:3000/chat) after smoke passes.

## 4. Stop

```powershell
.\scripts\stop_mvp.ps1
```

The stop script uses O-AI-owned PID files and command-line checks. It does not broadly terminate Python/Node processes and never stops Ollama.

## Deployment boundary

Docker and O-SERVER/production deployment are deferred. Docker support is retained, but it is not the D30 MVP quick start because its verification and Local AI host assumptions are not the official native-Windows path.
