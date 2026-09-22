# JobSeek — AI-Powered Job Application Assistant

A job-application assistant that builds a **verified evidence profile**
from a candidate's CV and employment references, matches it against
vacancies, and generates application material that never claims more than
the evidence supports.

> Every claim generated about the candidate must be traceable to verified
> evidence. See `docs/requirements.md` for the full product vision and
> `docs/architecture.md` for the system design.

## Status

**V0.5 — Productization.** The same backend now has two front doors: the
original Streamlit app (still works, unchanged, useful for quick manual
testing) and a FastAPI REST API (`backend/api/`) that a new React +
TypeScript frontend (`frontend/react-app/`) talks to. Neither UI contains
business logic — both call the exact same `backend/services/` functions
(`analyze_and_match`, `generate_application_material`, the `*Store`
classes) that power document evidence extraction (V0.1), job matching
(V0.2), evidence-grounded generation with an independent claim validator
(V0.3), and automated job discovery across Arbeitnow/Adzuna with
deduplication (V0.4). Still SQLite (Postgres is a `DATABASE_URL` change
whenever it's actually needed), still no authentication (still single-user
locally). Fuller application-tracking (save/status/dates) lands in a later
release — see the roadmap in `docs/requirements.md`.

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

**Option B — FastAPI + React** (two processes, in separate terminals):

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

Both options talk to the same SQLite database (`data/jobseek.db`) and the
same `backend/services/`, so you can freely switch between them.

## Test

```bash
pytest                              # backend: unit + API integration tests
cd frontend/react-app && npm run build   # frontend: type-checks and builds
```

## Project layout

```
app/                    Streamlit UI
backend/
  api/                   FastAPI app, routers, request/response DTOs
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
frontend/react-app/      React + TypeScript UI (Vite), talks to the FastAPI backend over HTTP
tests/
  unit/                  backend unit tests (fake LLM provider, no API key needed)
  api/                   FastAPI integration tests (in-memory DB, TestClient)
docs/                    requirements, architecture, privacy notes
data/                    uploaded documents + local sqlite db (git-ignored)
```
