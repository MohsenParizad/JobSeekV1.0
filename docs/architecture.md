# Architecture

## Layering

```
                         ┌─────────────────┐
                         │  Streamlit UI   │   (V0.1–V0.4)
                         │  React (later)  │   (V0.5+, behind a FastAPI layer)
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼──────────────────────┐
          │                       │                      │
          ▼                       ▼                      ▼
 Document Service          Job Service             AI / Generation Service
          │                       │                      │
          ▼                       ▼                      ▼
   Parsing                 Job Providers            LLMProvider interface
   Extraction               Normalization             (Anthropic / fake)
   Validation               Deduplication
          │                       │                      │
          └───────────────────────┼──────────────────────┘
                                  ▼
                            Matching Engine        (V0.2+)
                                  │
                                  ▼
                          Evidence / Data Store
                        (SQLite now, Postgres later)
```

The UI never talks to the LLM directly. It calls services in `backend/`,
which are plain, independently testable Python — the LLM is one
interchangeable component behind `backend/providers/llm/`, not the
application's core.

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

## Key interfaces

- **`LLMProvider`** (`backend/providers/llm/base.py`) — abstracts the model
  call behind `extract_evidence(text) -> list[ExtractedEvidence]`. Two
  implementations exist from day one: `AnthropicProvider` (real calls) and
  `FakeLLMProvider` (deterministic, used in tests and whenever no API key is
  configured), so the rest of the app never depends on a live API key.
- **`EvidenceStore`** (`backend/services/evidence/store.py`) — the only
  component that touches the database for evidence. Matching/generation
  services (later releases) read verified evidence through this, never via
  raw SQL scattered across the codebase.

## Why SQLite now, Postgres later

The models are defined with SQLAlchemy against a `DATABASE_URL`. SQLite
needs no external service, so V0.1 runs with zero infrastructure setup.
Switching to Postgres later (V0.5, per the roadmap) is a `DATABASE_URL`
change, not a schema rewrite — see `docs/requirements.md` for the release
plan.
