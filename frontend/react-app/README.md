# JobSeek — React frontend

A Vite + React + TypeScript UI for the JobSeek API (`backend/api/`).
Mirrors the Streamlit app's five tabs (Documents, Candidate Profile, Job
Search, Job Analysis, Generate Application) against the same backend.

See the repo root `README.md` for full setup/run instructions covering
both the backend and this frontend together.

## Quick reference

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev             # start the dev server (needs the FastAPI backend running too)
npm run build            # type-check + production build
```

## Layout

```
src/
  api.ts                Typed fetch client for the JobSeek API
  types.ts               TypeScript types mirroring backend/api/schemas.py
  App.tsx                 Tab navigation + candidate bootstrap
  components/              One component per tab
```
