# Requirements — AI-Powered Job Application Assistant (JobSeek)

## Product vision

A web application that automatically discovers relevant vacancies, builds a
verified evidence profile from a candidate's CV and employment references,
compares vacancies against that evidence, explains strengths and gaps, and
generates evidence-grounded application material without inventing
qualifications.

**Central principle:** every claim generated about the candidate must be
traceable to verified evidence.

## Functional requirements

### Candidate management
- Upload CV as PDF/DOCX.
- Upload multiple employment references (Arbeitszeugnisse).
- Extract experience, skills, technologies, education, projects and dates.
- Show extracted information to the user.
- User approves/corrects/rejects extracted evidence.
- Persist verified evidence.

### Job acquisition
- Manual job-description input.
- Job search by keyword.
- Country/location filter.
- Publication-date filter.
- Remote/hybrid/onsite filter where data permit it.
- Integrate Arbeitnow first, Adzuna second.
- Normalize results from different providers.
- Detect duplicate vacancies.

### Job analysis
- Extract required and preferred qualifications.
- Identify responsibilities.
- Extract technologies, languages, seniority and constraints.
- Match each requirement against candidate evidence.
- Distinguish direct, related, transferable and missing evidence.
- Explain where evidence came from.

### Application generation
- Suggest CV modifications.
- Generate tailored profile.
- Suggest which existing experience to emphasize.
- Generate cover letter.
- Never introduce unsupported experience.
- Run generated material through a final evidence validator.

### Application management
- Save interesting vacancies.
- Track application status.
- Associate CV/cover-letter versions with an application.
- Record application/interview/rejection dates.

## Non-functional requirements

- **Maintainability** — modular architecture, clear interfaces between layers.
- **Testability** — business logic testable independently of the GUI and the LLM.
- **Extensibility** — adding another job provider must not require changing
  the matching engine.
- **Reliability** — failure of one job provider (e.g. Adzuna) must not break
  manual job analysis.
- **Explainability** — matching results must point to supporting evidence.
- **Security/privacy** — CVs and references contain personal data and must
  not be unnecessarily exposed or logged. See `docs/privacy.md`.
- **AI safety** — generated claims require evidence; see the evidence
  validator (V0.3).
- **Reproducibility** — prompts and model configuration are versioned in
  the repository, not edited ad hoc.

## Release roadmap

| Release | Goal |
|---|---|
| V0.1 | Core evidence MVP: CV upload → structured evidence → human verification → storage |
| V0.2 | Job matching: manual job input → requirement extraction → matching → gap analysis |
| V0.3 | AI application generation: CV suggestions, cover letter, claim validator |
| V0.4 | Automated job discovery: Arbeitnow, then Adzuna, normalization, dedup |
| V0.5 | Productization: FastAPI backend + React frontend, improved schema |
| V1.0 | Production-style release: CI/CD, Docker, tests, deployment, monitoring |

This document currently covers **V0.1**. Later releases will extend it in
place rather than replacing it, so history stays traceable via git.

### V0.1 definition of done

You can upload your CV, the system extracts a structured set of candidate
evidence (skills, experience, education, projects) with a reference back to
the source text, you can approve/reject/edit each item in the UI, and
approved items persist as verified evidence you can view afterward.
