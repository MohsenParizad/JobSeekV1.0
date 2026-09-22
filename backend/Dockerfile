# Backend image: the FastAPI API only (backend/api/main.py). Deliberately
# does not install the streamlit extra — nothing under backend/ imports it,
# and it pulls in a large dependency tree the API doesn't need (see
# pyproject.toml). Build from the repo root:
#
#   docker build -f backend/Dockerfile -t jobseek-backend .
#
# mirror.gcr.io instead of docker.io: same official image, avoids Docker
# Hub's anonymous-pull rate limit (hit this repeatedly in CI/local testing).
FROM mirror.gcr.io/library/python:3.11-slim

WORKDIR /app

# All backend dependencies are pure Python or ship manylinux wheels, so no
# system build toolchain is needed here.
COPY pyproject.toml ./
COPY backend/ ./backend/

RUN pip install --no-cache-dir .

# Uploaded documents and the SQLite database live under /app/data — mount
# a volume there at runtime so they survive container restarts (see
# docker-compose.yml). Owned by a non-root user for defense in depth.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
