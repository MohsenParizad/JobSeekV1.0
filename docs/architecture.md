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
                            Matching Engine        (V0.2+, implemented)
                                  │
                                  ▼
                          Evidence / Job / Match Store
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

## Key interfaces

- **`LLMProvider`** (`backend/providers/llm/base.py`) — abstracts the model
  calls behind `extract_evidence`, `extract_job_requirements`, and
  `classify_transferable`. Two implementations exist from day one:
  `AnthropicProvider` (real calls, forced tool-use + a source-text grounding
  check) and `FakeLLMProvider` (deterministic, used in tests and whenever no
  API key is configured), so the rest of the app never depends on a live key.
- **`EvidenceStore`** (`backend/services/evidence/store.py`) — the only
  component that touches the database for evidence.
- **`JobStore`** (`backend/services/jobs/store.py`) — the only component
  that touches the database for jobs/requirements.
- **`MatchStore`** (`backend/services/matching/store.py`) — the only
  component that touches the database for matching runs.
- **`analyze_and_match`** (`backend/services/jobs/analysis.py`) — the
  UI-agnostic orchestration of the V0.2 slice above; the Streamlit tab and,
  later, the FastAPI layer both call this one function.

## Why SQLite now, Postgres later

The models are defined with SQLAlchemy against a `DATABASE_URL`. SQLite
needs no external service, so V0.1 runs with zero infrastructure setup.
Switching to Postgres later (V0.5, per the roadmap) is a `DATABASE_URL`
change, not a schema rewrite — see `docs/requirements.md` for the release
plan.
