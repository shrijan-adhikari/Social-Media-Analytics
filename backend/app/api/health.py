"""Health check endpoints.

GET /health      — lightweight liveness probe; no DB required.
GET /health/db   — readiness probe; verifies PostgreSQL connectivity.

Neither endpoint exposes credentials, connection strings, or internal errors.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """Return ok to confirm the application process is running."""
    return {"status": "ok"}


@router.get("/health/db", summary="Database readiness probe")
def health_db(response: Response) -> dict[str, str]:
    """Verify that PostgreSQL is reachable.

    Returns 200 + ``{"status": "ok"}`` when reachable.
    Returns 503 + ``{"status": "unavailable"}`` when not reachable.

    Does not expose credentials, connection strings, or error details.
    """
    if check_db_connection():
        return {"status": "ok"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "unavailable"}
