# Architecture

## Layering

```
                    ┌─────────────────┐    ┌──────────────────────┐
                    │  Streamlit UI   │    │   React UI (V0.5+)   │
                    │   (V0.1–V0.4,   │    │  talks to the API    │
                    │  still works)   │    │  over HTTP only       │
                    └────────┬────────┘    └───────────┬──────────┘
                             │                          │
                             │              ┌───────────▼──────────┐
                             │              │  FastAPI (V0.5+)      │
                             │              │  backend/api/         │
                             │              └───────────┬──────────┘
                             │                          │
                             └────────────┬─────────────┘
                                          │
          ┌───────────────────────┼──────────────────────┐
          │                       │                      │
          ▼                       ▼                      ▼
 Document Service          Job Service             AI / Generation Service
          │                       │                      │
          ▼                       ▼                      ▼
   Parsing                 Job Providers            LLMProvider interface
   Extraction               (Arbeitnow / Adzuna)      (Anthropic / fake)
   Validation               Normalization
                             Deduplication
          │                       │                      │
          └───────────────────────┼──────────────────────┘
                                  ▼
                            Matching Engine        (V0.2+, implemented)
                                  │
                                  ▼
                          Evidence / Job / Match Store
                        (SQLite now, Postgres later)
```

Neither UI talks to the LLM, the database, or any service directly. As of
V0.5 there are two front doors into the same `backend/services/`: the
original Streamlit app (kept working, useful for quick manual testing) and
a FastAPI HTTP API (`backend/api/`) that a React frontend talks to. Both
call the exact same orchestration functions (`analyze_and_match`,
`generate_application_material`, the various `*Store` classes) — no
business logic lives in either UI layer, and none was duplicated to add
the second one.

## V0.1 slice

Only the document ingestion pipeline is implemented:

```
CV / reference file
        ↓
DocumentParser (PDF/DOCX → raw text)
        ↓
EvidenceExtractionService (LLMProvider → structured, schema-validated evidence)
        ↓
EvidenceStore (persist as "pending")
        ↓
Human verification (Streamlit checklist: approve / edit / reject)
        ↓
EvidenceStore (persist as "verified")
```

## V0.2 slice

Manual job input, requirement extraction, and matching against the
candidate's *verified* evidence only:

```
Job description (pasted text)
        ↓
LLMProvider.extract_job_requirements (structured, schema-validated requirements)
        ↓
JobStore (persist Job + JobRequirement rows)
        ↓
MatchingEngine.match (per requirement, against EvidenceStore's verified evidence)
        │
        ├─ deterministic keyword/synonym pass → direct / related / missing
        └─ if still missing: optional LLMProvider.classify_transferable
                              upgrade to "transferable", citing specific evidence
        ↓
score_matches (deterministic, weighted, explainable — never LLM-invented)
        ↓
MatchStore (persist JobMatch + RequirementMatch rows)
        ↓
Streamlit "Job Analysis" tab: Direct / Related / Transferable / Gaps, with citations
```

The matching engine is deliberately **not** an LLM call for the direct/related
pass — it's cheap keyword/synonym matching that keeps working even if the AI
provider is down (see the Reliability NFR in `docs/requirements.md`), and its
decisions are trivially explainable. The LLM is only asked, per requirement,
about the one case the deterministic pass can't resolve — whether *other*
verified evidence transfers to a requirement with no direct/related hit — and
that verdict can never override a deterministic direct/related classification.

## V0.3 slice — evidence-grounded generation

Tailored application material, generated only from verified evidence and an
existing job match, then independently checked claim-by-claim:

```
Verified evidence + job requirement matches (from V0.2)
        ↓
LLMProvider.generate_application
        │   - instructed to reference ONLY the evidence it's given
        │   - self-reports every checkable claim it makes (statement + concept)
        ↓
GeneratedApplication (tailored summary, CV suggestions, cover letter, claims[])
        ↓
validate_claims (backend/services/generation/validator.py)
        │   - deterministic, reuses text_matching.py (the SAME grounding
        │     logic the MatchingEngine uses) — independent of the model
        │     that wrote the text, so it isn't grading its own homework
        ↓
ClaimValidation per claim: supported / unsupported, with the matched evidence cited
        ↓
GenerationStore (persist the draft + its self-reported claims)
        ↓
Streamlit "Generate Application" tab: draft + a claim-by-claim validation
panel that prominently flags anything unsupported before the user sends it
```

The system prompt tells the model never to assert a qualification the
evidence doesn't support — but that instruction is advisory, not the
safeguard. The actual guarantee is `validate_claims`: it runs regardless of
what the model did, checks each self-reported claim against the
candidate's verified evidence using the same keyword/synonym matcher as
job-requirement matching, and reports supported/unsupported so an
unsupported claim (e.g. a generated "experience with AWS" when nothing in
the evidence store mentions AWS) is always caught before the candidate
sends the material — this is the "Evidence-Grounded Generation" principle
from the product vision made concrete. Because validation is a pure
function of (claims, verified evidence) rather than baked into the stored
record, re-viewing a draft always re-checks it against the candidate's
*current* evidence (`revalidate` in `backend/services/generation/service.py`)
— so approving new evidence later can turn a previously-unsupported claim
into a supported one, and vice versa.

## V0.4 slice — automated job discovery

Search external providers, normalize, deduplicate, and let the candidate
turn any result into an analyzed job without re-pasting its description:

```
Search form (keywords, country, location, published-after, work model)
        ↓
search_all_providers (backend/services/jobs/search.py)
        │   - calls every configured JobProvider (ArbeitnowProvider always;
        │     AdzunaProvider once ADZUNA_APP_ID/APP_KEY are set)
        │   - a provider raising JobSearchError is caught and reported,
        │     never lets one provider's outage break the others' results
        │     (Reliability NFR)
        ↓
Each provider normalizes its raw response into the canonical JobListing
schema (schemas/job_listing.py) — the rest of the app never knows which
provider a listing came from
        ↓
deduplicate_listings (backend/services/jobs/deduplication.py)
        │   - deterministic: normalized company + title + location
        │   - explicitly NOT an LLM call, per docs/requirements.md's
        │     guidance to start deduplication with conventional algorithms
        ↓
Streamlit "Job Search" tab: results list, "Save & analyze" per listing
        ↓
JobStore.save_job_listing (persist as a Job row, source="arbeitnow"/"adzuna",
        idempotent per (source, external_id) — re-saving a listing already
        fetched in an earlier search returns the existing row)
        ↓
analyze_and_match(job_id=...) — the SAME V0.2 function, extended to accept
        an existing job as an alternative to description_text: extracts
        requirements from the listing's stored description, attaches them,
        then matches exactly as the manual-entry path already did
        ↓
Job Analysis / Generate Application tabs work unchanged — they don't know
or care whether a Job came from manual entry or a provider search
```

Adding Adzuna required zero changes to `MatchingEngine`, `validate_claims`,
or any of V0.2/V0.3's persistence — exactly the Extensibility NFR from
`docs/requirements.md` ("adding another job provider shouldn't require
changing the matching engine"). The only shared surface both providers
touch is the `JobProvider` interface and the canonical `JobListing` schema.

## V0.5 slice — productization (FastAPI + React)

The backend gets an HTTP front door, and a React app replaces Streamlit as
the primary UI, without either one touching `backend/services/` logic:

```
React (Vite + TypeScript, frontend/react-app/)
        │  fetch, JSON over HTTP, CORS-enabled for local dev
        ▼
FastAPI (backend/api/main.py + backend/api/routers/*.py)
        │  each router is a thin translation layer: HTTP request →
        │  backend/api/schemas.py DTO → the SAME service call the
        │  Streamlit tab already made → DTO → HTTP response
        ▼
backend/services/*  (unchanged — EvidenceStore, JobStore, MatchStore,
        GenerationStore, analyze_and_match, generate_application_material)
```

Concretely: `POST /jobs/analyze` in `backend/api/routers/jobs.py` calls the
exact same `analyze_and_match()` the Streamlit "Job Analysis" tab calls;
`POST /applications/generate` calls the exact same
`generate_application_material()`. The API layer's only job is HTTP
concerns — request parsing, status codes (404 for a missing job/candidate,
400 for "no match yet, run analysis first"), and DTOs
(`backend/api/schemas.py`) that are deliberately separate from both the LLM
I/O contracts (`backend/schemas/*`) and the ORM models, so a change to any
one of the three doesn't ripple through the others.

`backend/api/deps.py` provides a per-request DB session; tests
(`tests/api/`) override that dependency with an in-memory SQLite database
via `app.dependency_overrides`, so the API test suite runs without ever
touching the real `data/jobseek.db`.

The database stays SQLite for V0.5 (per the roadmap, switching to Postgres
is a `DATABASE_URL` change whenever it's actually needed — see "Why SQLite
now, Postgres later" below), and there's no authentication yet: the app is
still single-user, and the React app bootstraps a candidate by name exactly
like the Streamlit sidebar did.

## Key interfaces

- **`LLMProvider`** (`backend/providers/llm/base.py`) — abstracts the model
  calls behind `extract_evidence`, `extract_job_requirements`,
  `classify_transferable`, and `generate_application`. Two implementations
  exist from day one: `AnthropicProvider` (real calls, forced tool-use +
  grounding checks) and `FakeLLMProvider` (deterministic, used in tests and
  whenever no API key is configured), so the rest of the app never depends
  on a live key.
- **`backend/services/text_matching.py`** — the shared keyword/synonym
  grounding primitives used by both the MatchingEngine and the claim
  validator, so "does concept X appear in this evidence" is answered the
  same way everywhere.
- **`EvidenceStore`** (`backend/services/evidence/store.py`) — the only
  component that touches the database for evidence.
- **`JobStore`** (`backend/services/jobs/store.py`) — the only component
  that touches the database for jobs/requirements.
- **`MatchStore`** (`backend/services/matching/store.py`) — the only
  component that touches the database for matching runs.
- **`GenerationStore`** (`backend/services/generation/store.py`) — the only
  component that touches the database for generated application material.
- **`JobProvider`** (`backend/providers/jobs/base.py`) — abstracts one job
  source behind `search_jobs(...) -> list[JobListing]`. `ArbeitnowProvider`
  needs no credentials; `AdzunaProvider` is only registered (see
  `backend/providers/jobs/__init__.py`) once its API keys are configured.
- **`analyze_and_match`** (`backend/services/jobs/analysis.py`) /
  **`generate_application_material`** (`backend/services/generation/service.py`)
  — UI-agnostic orchestration of the V0.2/V0.3 slices; the Streamlit tabs
  and the FastAPI routers both call these same functions.
  `analyze_and_match` also backs V0.4: pass `job_id` instead of
  `description_text` to analyze a job saved from a search result.
- **`backend/api/main.py`** — the FastAPI app: CORS (origins from
  `ALLOWED_ORIGINS`, defaulting to the local Vite dev server), a lifespan
  hook that calls `init_db()`, and five routers (candidates, documents,
  evidence, jobs, applications), each a thin HTTP-to-service translation
  layer with no business logic of its own.
- **`backend/api/middleware.py`** — request logging (method, path, status,
  duration) and the global exception handler: any unhandled error is
  logged server-side with a full traceback and returned to the client as a
  generic `{"detail": "Internal server error"}`, never the exception text.
- **`backend/api/deps.py`** — `get_db()`, the per-request session
  dependency; `tests/api/conftest.py` overrides it with an in-memory
  SQLite engine so API tests never touch the real database file.
- **`frontend/react-app/src/api.ts`** — the typed fetch client every React
  component uses instead of calling `fetch` directly; mirrors
  `backend/api/schemas.py`'s shapes in `src/types.ts`.

## V1.0 slice — CI/CD, Docker, hardening

Turns the working prototype into something a stranger could clone, test,
and run without reading the source first:

```
git push
        ↓
GitHub Actions (.github/workflows/ci.yml)
        │   - backend job: ruff check . && pytest -q
        │   - frontend job: npm run lint && npm test && npm run build
        │   - both required to pass before merging to main
        ↓
docker compose up --build
        │   - backend/Dockerfile: FastAPI only, deliberately WITHOUT the
        │     streamlit extra (nothing under backend/ imports it — see
        │     pyproject.toml's optional-dependencies split)
        │   - frontend/react-app/Dockerfile: multi-stage, node build ->
        │     nginx serves the static bundle
        │   - SQLite + uploaded documents persisted in a named volume
        ↓
Same backend/services/ as every earlier release — V1.0 adds no new
business logic, only the scaffolding around it: request logging, a global
exception handler that never leaks internals, configurable CORS
(ALLOWED_ORIGINS), and docs/deployment.md describing real deployment
options without adopting AWS/Terraform prematurely
```

The Docker images are exactly what ships to a real deployment target
(see `docs/deployment.md`) — nothing about them is sandbox-specific.
`mirror.gcr.io` is used instead of `docker.io` for base images purely to
avoid Docker Hub's anonymous-pull rate limit in CI/repeated local builds;
it resolves to the identical official images.

## Why SQLite now, Postgres later

The models are defined with SQLAlchemy against a `DATABASE_URL`. SQLite
needs no external service, so the app has run with zero infrastructure
setup since V0.1 — including through V0.5's FastAPI/React rebuild.
Switching to Postgres, whenever it's actually needed, is a `DATABASE_URL`
change, not a schema rewrite — see `docs/requirements.md` for the release
plan.
