"""FastAPI backend — a thin HTTP layer over the same backend/services used
by the Streamlit app (app/streamlit_app.py). All business logic lives in
backend/services/; this and Streamlit are two different front doors to it
(see docs/architecture.md). Run with:

    uvicorn backend.api.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import applications, candidates, documents, evidence, jobs
from backend.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jobseek.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("JobSeek API started")
    yield


app = FastAPI(title="JobSeek API", version="0.5.0", lifespan=lifespan)

# The React dev server (Vite) runs on 5173 by default; a production build
# would be served from a fixed origin configured at deploy time instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)
app.include_router(documents.router)
app.include_router(evidence.router)
app.include_router(jobs.router)
app.include_router(applications.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
