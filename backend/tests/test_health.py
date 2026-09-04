"""Tests for health endpoints.

These tests do not require a live PostgreSQL connection.
The DB check in /health/db is overridden via the test client fixture.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """GET /health must return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_body(client: TestClient) -> None:
    """GET /health body must be exactly {"status": "ok"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_db_returns_json(client: TestClient) -> None:
    """GET /health/db must return JSON with a 'status' field.

    The status value may be 'ok' (if DB available) or 'unavailable' (if not).
    Without a live PostgreSQL instance the response will be 503.
    This test only verifies the response shape is correct.
    """
    response = client.get("/health/db")
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "unavailable")


def test_health_db_does_not_expose_credentials(client: TestClient) -> None:
    """GET /health/db must not leak DATABASE_URL or credentials."""
    response = client.get("/health/db")
    body = response.text
    # Must not contain fragments of a typical DATABASE_URL
    assert "postgresql" not in body.lower()
    assert "password" not in body.lower()
    assert "@" not in body


@pytest.mark.integration
def test_health_db_ok_with_postgres(client: TestClient) -> None:
    """GET /health/db returns 200 when PostgreSQL is reachable.

    Requires: DATABASE_URL environment variable pointing to a live PostgreSQL.
    """
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
