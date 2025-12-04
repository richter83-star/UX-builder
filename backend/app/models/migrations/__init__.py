"""Lightweight migration runner.

This is intentionally small to keep parity with the existing codebase while adding
new tables. In production we would wire full Alembic; here we expose a simple
`run_migrations()` helper used by tests and local setup.
"""
from sqlalchemy import create_engine

from app.models.database import Base
from app.utils.config import settings


def run_migrations(database_url: str | None = None):
    engine = create_engine(database_url or settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
