# O-AI

O-AI is a local-first Personal AI Operating System foundation with chat, conversation memory, and local document knowledge.

O-AI currently supports a trusted local, single-owner deployment model. The official MVP path is native Windows with the backend and frontend bound only to loopback. Another LAN computer, phone/tablet over LAN, and public/Internet access are not currently supported as secured paths; they require a separately designed security boundary before exposure. The API has no authentication or authorization layer.

## Stack

- Backend: Python 3.14, FastAPI, Pydantic, Uvicorn
- Frontend: Next.js, React, TypeScript, Tailwind CSS

## Quick start

1. Run `./scripts/bootstrap.ps1` in Windows PowerShell.
2. Review `.env`; set `OAI_LOCAL_AI_ENABLED=true` to use the configured Ollama model. OpenAI is optional.
3. Run `./scripts/start_mvp.ps1`.
4. Run `./scripts/smoke_mvp.ps1`, then open `http://localhost:3000/chat` or `http://127.0.0.1:3000/chat`.
5. Run `./scripts/stop_mvp.ps1` when finished.

See [the MVP runbook](docs/MVP_RUNBOOK.md) for the complete local run path. Docker support is retained but is deferred/non-MVP deployment work; it is not the D30 quick-start path.

## Local development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Bootstrap

Windows PowerShell:

```powershell
.\scripts\bootstrap.ps1
```

macOS/Linux:

```sh
./scripts/bootstrap.sh
```

The scripts create missing environment files, create a Python virtual environment at `.venv`, install backend dependencies, and run `npm ci` in `frontend`.

## Local Knowledge Engine

Create a local knowledge folder and set `OAI_KNOWLEDGE_ROOT` to its path (the default is `./knowledge`). Open `/knowledge` and press **Scan Documents** to index supported files. O-AI does not upload files or provide file upload/browsing APIs.

Supported formats are PDF (`.pdf`), Word (`.docx`), Excel (`.xlsx`), CSV (`.csv`), PowerPoint (`.pptx`), text (`.txt`), Markdown (`.md`), HTML (`.html`, `.htm`), and email (`.eml`). Only text-based PDFs are supported; scanned or image-only PDFs are recorded safely without indexed text. OCR is planned for Release 0.6.1.

The scanner stores only root-relative paths in SQLite, skips hidden paths and symlinks, enforces the configured file-size limit, and never indexes email attachments in this release. Documents remain on the local machine; deleting an indexed document removes only its index entry, never its source file.

## Grounded knowledge answers

`POST /api/v1/knowledge/answer` retrieves local evidence before calling the configured chat provider. Answers return validated citations and an evidence-quality label. Citation snapshots are durably persisted with the assistant message as historical provenance. Retrieved documents are untrusted reference material; prompt injection is reduced through explicit boundaries but cannot be fully prevented while the provider uses a single-string input.

## Projects

Open `/projects` to create and review owner-controlled Projects. Every Project change requires an explicit owner change note and the revision currently under review; a conflict refreshes the displayed state and requires a new owner submission rather than an automatic retry. Revision history is read-only. Starting a new chat from a Project attaches it only to that conversation's first message; the association cannot later be switched. AI output never writes Project state.

## Layout

`backend/app` separates API handlers, core infrastructure, data models, services, and Pydantic schemas. `frontend/app` uses the Next.js App Router. `docs` and `scripts` are reserved for project documentation and automation.
