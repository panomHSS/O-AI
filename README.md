# O-AI

O-AI is the foundation for a Personal AI Operating System. This repository intentionally contains no AI implementation yet.

## Stack

- Backend: Python 3.14, FastAPI, Pydantic, Uvicorn
- Frontend: Next.js, React, TypeScript, Tailwind CSS

## Quick start

1. Run the bootstrap script for your shell. It installs dependencies and creates local environment files when needed.
2. Start the full stack with `docker compose up --build`.
3. Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/api/v1/health`.

Docker Compose has safe development defaults and does not require a root `.env` file. To override them, copy `.env.example` to `.env`. For local Next.js development, copy `frontend/.env.example` to `frontend/.env.local`.

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

## Layout

`backend/app` separates API handlers, core infrastructure, data models, services, and Pydantic schemas. `frontend/app` uses the Next.js App Router. `docs` and `scripts` are reserved for project documentation and automation.
