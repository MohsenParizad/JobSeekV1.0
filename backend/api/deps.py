"""Shared FastAPI dependencies."""
from collections.abc import Iterator

from sqlalchemy.orm import Session

from backend.db import get_session


def get_db() -> Iterator[Session]:
    session = get_session()
    try:
        yield session
    finally:
        session.close()
