# Deployment

## Running with Docker (recommended for anything beyond local dev)

```bash
cp .env.example .env    # fill in ANTHROPIC_API_KEY etc.
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend: http://localhost:8000 (interactive docs at `/docs`)

`docker-compose.yml` builds two images from the Dockerfiles in this repo
(`backend/Dockerfile`, `frontend/react-app/Dockerfile`) and persists the
SQLite database and uploaded documents in a named volume
(`jobseek_data`), so they survive `docker compose down` (use `down -v` to
actually discard them).

### Building the images individually

```bash
docker build -f backend/Dockerfile -t jobseek-backend .
docker build -f frontend/react-app/Dockerfile \
  --build-arg VITE_API_BASE_URL=https://api.your-domain.example \
  -t jobseek-frontend .
```

`VITE_API_BASE_URL` is baked into the frontend's JS at **build time** (Vite
env vars aren't runtime-configurable), so it must be the URL the *browser*
will use to reach the backend — not a Docker-internal service name.

## Environment variables

All read from `.env` (see `.env.example`) by both the backend API and the
Streamlit app.

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Real extraction/matching/generation. Without it, the app runs on a deterministic fake provider — fully functional for testing, not for real use. |
| `ANTHROPIC_MODEL` | No | Defaults to `claude-sonnet-5`. |
| `DATABASE_URL` | No | Defaults to a local SQLite file. Point at a `postgresql://` URL to switch databases — no code or schema changes needed (see `docs/architecture.md`). |
| `DOCUMENT_STORAGE_DIR` | No | Where uploaded CVs/references are stored on disk. |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | No | Enables the Adzuna job provider. Arbeitnow works with no credentials either way. |
| `ALLOWED_ORIGINS` | No (recommended in production) | Comma-separated list of origins the API accepts CORS requests from. Defaults to the local Vite dev server. **Set this to your deployed frontend's real origin** — the default is unsafe to leave in place beyond local development. |

Secrets are never committed: `.env` is git-ignored, `.env.example` documents
the keys with empty values. See `docs/privacy.md` for the fuller data-handling
policy.

## CI

`.github/workflows/ci.yml` runs on every push/PR to `main`:
- **Backend job**: `ruff check .` then `pytest -q` (70+ tests, no external
  network or API key required — the LLM and job-provider calls are either
  mocked or fall back to deterministic fakes).
- **Frontend job**: `npm run lint` (oxlint), `npm test` (Vitest), then
  `npm run build` (`tsc -b && vite build` — a type error fails the build).

Both jobs must pass before merging.

## Deployment targets

This app has no state beyond its SQLite file and uploaded documents, and
the two Docker images are the actual deployable artifact — where you run
them is a separate decision from whether they're ready to deploy. Roughly
in order of effort:

1. **A single VPS** (e.g. Hetzner, DigitalOcean) running
   `docker compose up -d` directly, behind a reverse proxy (Caddy or nginx)
   terminating TLS. Simplest path from what's in this repo today to a real
   URL.
2. **A managed container platform** (Render, Fly.io, Railway) — push the
   two images, point `VITE_API_BASE_URL` at the platform's assigned backend
   URL at build time, set `ALLOWED_ORIGINS` to the assigned frontend URL.
   Most of these also offer a managed Postgres add-on if/when you switch
   off SQLite.
3. **AWS (ECS/Fargate) + Terraform** — the natural next step once traffic
   or team size justifies the added operational surface, but deliberately
   not implemented here: per the project's own roadmap, starting with
   cloud infrastructure before the application itself works is the wrong
   order. Revisit this once options 1–2 stop being enough.

None of these are set up in this repo yet — this section is a map for when
you're ready to pick one, not a claim that hosting already exists.

## Monitoring / logging

- Every HTTP request is logged (method, path, status, duration) by
  `backend/api/middleware.py`'s `RequestLoggingMiddleware`.
- Unhandled exceptions are logged server-side with a full traceback and
  returned to the client as a generic `{"detail": "Internal server error"}`
  — never the exception text, which could leak internals (see
  `register_exception_handlers` in the same file).
- `GET /health` is a liveness check; `docker-compose.yml` wires it into the
  backend container's healthcheck.
- Nothing ships to an external log aggregator or APM yet — for a real
  deployment, forward container stdout (structured as plain log lines
  today) to whatever your platform provides (CloudWatch, Grafana Loki,
  etc.) rather than building a custom sink here.
