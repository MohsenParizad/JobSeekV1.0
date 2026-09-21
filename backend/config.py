"""Central place for environment-driven settings. Loaded once at import time."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    document_storage_dir: Path
    anthropic_api_key: str | None
    anthropic_model: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/jobseek.db"),
        document_storage_dir=Path(os.getenv("DOCUMENT_STORAGE_DIR", "./data/uploads")),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
    )


settings = load_settings()
