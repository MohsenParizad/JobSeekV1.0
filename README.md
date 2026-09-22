# JobSeek — AI-Powered Job Application Assistant

[![CI](https://github.com/MohsenParizad/JobSeek/actions/workflows/ci.yml/badge.svg)](https://github.com/MohsenParizad/JobSeek/actions/workflows/ci.yml)

A job-application assistant that builds a **verified evidence profile**
from a candidate's CV and employment references, matches it against
vacancies, and generates application material that never claims more than
the evidence supports.

> Every claim generated about the candidate must be traceable to verified
> evidence. See `docs/requirements.md` for the full product vision and
> `docs/architecture.md` for the system design.

## Status

**V1.0 — Production-style release.** All prior functionality is unchanged
— evidence extraction (V0.1), job matching (V0.2), evidence-grounded
generation with an independent claim validator (V0.3), automated job
discovery across Arbeitnow/Adzuna (V0.4), and the FastAPI + React
productization (V0.5). V1.0 adds the scaffolding around that same
`backend/services/`: CI (GitHub Actions — lint + test on every push/PR for
both backend and frontend), Docker images for both services plus a
`docker-compose.yml` to run the full stack, request logging and an
exception handler that never leaks internals, configurable CORS, and
`docs/deployment.md` covering real deployment options. Still SQLite, still
no authentication — both remain deliberate, documented scope decisions,
not gaps (see `docs/requirements.md`'s roadmap).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY to use real extraction/matching/generation.
# Without a key, the app falls back to a deterministic fake provider so you
# can still exercise the full workflow.
#
# Job search works with zero setup (Arbeitnow needs no credentials). To also
# search Adzuna, set ADZUNA_APP_ID / ADZUNA_APP_KEY (register at
# https://developer.adzuna.com) — it's simply skipped otherwise.
```

For the React frontend, you'll also need [Node.js](https://nodejs.org) 18+:

```bash
cd frontend/react-app
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
```

## Run

**Option A — Streamlit** (single process, no Node needed):

```bash
streamlit run app/streamlit_app.py
```

**Option B — FastAPI + React, run directly** (two processes, in separate terminals):

```bash
# terminal 1 — backend, from the repo root
uvicorn backend.api.main:app --reload

# terminal 2 — frontend
cd frontend/react-app
npm run dev
```

Then open the URL Vite prints (typically http://localhost:5173). The API
itself is at http://localhost:8000 — interactive docs at
http://localhost:8000/docs.

**Option C — Docker** (both services, one command — see `docs/deployment.md`):

```bash
docker compose up --build
```
Frontend at http://localhost:8080, backend at http://localhost:8000.

All three options talk to the same SQLite database (`data/jobseek.db`, or
a Docker volume for option C) and the same `backend/services/`, so you can
freely switch between them.

## Test

```bash
pytest                                # backend: unit + API integration tests
ruff check .                           # backend: lint

cd frontend/react-app
npm test                                # frontend: unit tests (Vitest)
npm run lint                             # frontend: lint
npm run build                             # frontend: type-check + production build
```
All of the above run in CI on every push/PR — see `.github/workflows/ci.yml`.

## Project layout

```
app/                    Streamlit UI
backend/
  api/                   FastAPI app, routers, request/response DTOs, middleware
  models/                SQLAlchemy models (evidence, job/requirement, matching, generation)
  schemas/                Pydantic schemas (LLM I/O contracts)
  services/
    documents/             parsing + extraction
    evidence/               persistence layer
    jobs/                   requirement extraction, search orchestration, dedup, persistence
    matching/                deterministic MatchingEngine + scoring + persistence
    generation/              application generation, claim validator, persistence
    text_matching.py         shared keyword/synonym grounding logic (matching + validator)
  providers/
    llm/                    LLMProvider interface + Anthropic/fake implementations
    jobs/                    JobProvider interface + Arbeitnow/Adzuna implementations
  Dockerfile               backend image (FastAPI only, no streamlit)
frontend/react-app/      React + TypeScript UI (Vite), talks to the FastAPI backend over HTTP
  Dockerfile               frontend image (node build -> nginx)
tests/
  unit/                  backend unit tests (fake LLM provider, no API key needed)
  api/                   FastAPI integration tests (in-memory DB, TestClient)
docs/                    requirements, architecture, privacy, deployment notes
.github/workflows/       CI (lint + test, backend and frontend)
docker-compose.yml       runs backend + frontend together locally
data/                    uploaded documents + local sqlite db (git-ignored)
```
