"""Central place for environment-driven settings. Loaded once at import time."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@dataclass(frozen=True)
class Settings:
    database_url: str
    document_storage_dir: Path
    anthropic_api_key: str | None
    anthropic_model: str
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    allowed_origins: list[str]


def load_settings() -> Settings:
    raw_origins = os.getenv("ALLOWED_ORIGINS")
    allowed_origins = (
        [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if raw_origins
        else DEFAULT_ALLOWED_ORIGINS
    )
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/jobseek.db"),
        document_storage_dir=Path(os.getenv("DOCUMENT_STORAGE_DIR", "./data/uploads")),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
        adzuna_app_id=os.getenv("ADZUNA_APP_ID") or None,
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY") or None,
        allowed_origins=allowed_origins,
    )


settings = load_settings()
