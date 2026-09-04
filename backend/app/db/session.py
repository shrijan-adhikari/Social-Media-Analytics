"""SQLAlchemy engine and session management.

Uses SQLAlchemy 2.x style with psycopg (v3) as the async-capable driver.
All database access goes through the `get_db` FastAPI dependency.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _build_engine():
    """Build the SQLAlchemy engine from application settings.

    Uses psycopg (v3) binary driver. Connection pool size is intentionally
    left at defaults for Phase 1 — tune later when load patterns are known.
    """
    settings = get_settings()
    if not settings.DATABASE_URL:
        # Development convenience: engine creation is deferred until first use.
        # Tests that do not need a real DB will override get_db anyway.
        return None
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Detect stale connections before use.
        echo=(settings.APP_ENV == "development"),
    )


# Module-level engine — None when DATABASE_URL is unset (test/offline mode).
engine = _build_engine()

# Session factory bound to the engine (or None in offline mode).
SessionLocal: sessionmaker[Session] | None = (
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
    if engine is not None
    else None
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    if SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set the DATABASE_URL environment variable."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if PostgreSQL is reachable, False otherwise.

    Used by the /health/db endpoint. Does not raise.
    """
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
