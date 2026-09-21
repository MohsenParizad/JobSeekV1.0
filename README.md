# JobSeek — AI-Powered Job Application Assistant

A job-application assistant that builds a **verified evidence profile**
from a candidate's CV and employment references, matches it against
vacancies, and generates application material that never claims more than
the evidence supports.

> Every claim generated about the candidate must be traceable to verified
> evidence. See `docs/requirements.md` for the full product vision and
> `docs/architecture.md` for the system design.

## Status

**V0.1 — Core evidence MVP.** Upload a CV, get structured evidence
extracted, review/approve it, and have it persisted as your verified
profile. Job matching and generation land in later releases (see the
roadmap in `docs/requirements.md`).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY to use real extraction.
# Without a key, the app falls back to a deterministic fake extractor
# so you can still exercise the full workflow.
```

## Run

```bash
streamlit run app/streamlit_app.py
```

## Test

```bash
pytest
```

## Project layout

```
app/                    Streamlit UI
backend/
  models/                SQLAlchemy models (evidence store schema)
  schemas/                Pydantic schemas (LLM I/O contracts)
  services/
    documents/             parsing + extraction
    evidence/               persistence layer
  providers/
    llm/                    LLMProvider interface + Anthropic/fake implementations
tests/unit/              unit tests (run against the fake LLM provider, no API key needed)
docs/                    requirements, architecture, privacy notes
data/                    uploaded documents + local sqlite db (git-ignored)
```
