"""Shared pytest fixtures for the backend test suite.

Unit tests (no PostgreSQL required):
  - These tests override the `get_db` dependency with an in-memory SQLite
    session. SQLite is used here because it requires no external setup and
    is explicitly permitted for testing by DATABASE.md / PROJECT_CONTEXT.md.
  - SQLite does not support all PostgreSQL features (e.g., JSONB, native ENUM).
    The models use SQLAlchemy's dialect-agnostic column types where possible.
    JSONB falls back to JSON in SQLite; ENUMs use VARCHAR.

Integration tests (PostgreSQL required):
  - Tests marked with @pytest.mark.integration require DATABASE_URL to be set.
  - They are skipped automatically when DATABASE_URL is absent.
  - Run them with: pytest tests/ -m integration
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.base import Base


# ── SQLite in-memory engine for unit tests ──────────────────────────────────

def _make_sqlite_engine():
    """Create an in-memory SQLite engine with SQLAlchemy 2.x style."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # SQLite foreign key enforcement is off by default; enable it.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="session")
def sqlite_engine():
    """Session-scoped SQLite engine — shared across the test session."""
    engine = _make_sqlite_engine()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    """Function-scoped database session using SQLite.

    Each test runs in an isolated transaction that is rolled back on teardown.
    """
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with the DB dependency overridden.

    The `get_db` dependency is replaced with one that returns the test SQLite
    session, so no real PostgreSQL connection is needed for unit tests.
    """
    from app.main import app
    from app.db.session import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Integration test helpers ─────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a live PostgreSQL instance "
        "(set DATABASE_URL env var to run these)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests when DATABASE_URL is not set."""
    if not os.getenv("DATABASE_URL"):
        skip_integration = pytest.mark.skip(
            reason="DATABASE_URL not set — skipping PostgreSQL integration tests"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
