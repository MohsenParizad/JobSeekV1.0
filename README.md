# JobSeek — AI-Powered Job Application Assistant

A job-application assistant that builds a **verified evidence profile**
from a candidate's CV and employment references, matches it against
vacancies, and generates application material that never claims more than
the evidence supports.

> Every claim generated about the candidate must be traceable to verified
> evidence. See `docs/requirements.md` for the full product vision and
> `docs/architecture.md` for the system design.

## Status

**V0.4 — Automated job discovery.** Upload a CV, get structured evidence
extracted and approve it (V0.1); search live vacancies from Arbeitnow (and
Adzuna, once configured) by keyword/country/location/date/work-model,
deduplicated across providers, and save any result to analyze against your
verified evidence — or still paste a description manually (V0.2); then
generate a tailored summary, CV suggestions, and a cover letter with every
checkable claim independently validated against your verified evidence
(V0.3). Fuller application-tracking (save/status/dates) and the FastAPI +
React rebuild land in later releases (see the roadmap in
`docs/requirements.md`).

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
tests/unit/              unit tests (run against the fake LLM provider, no API key needed)
docs/                    requirements, architecture, privacy notes
data/                    uploaded documents + local sqlite db (git-ignored)
```
