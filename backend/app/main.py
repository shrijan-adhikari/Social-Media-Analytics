"""FastAPI application factory.

Phase 1: health endpoints only.
Analytics API endpoints will be added in Phase 3 (see PROJECT_CONTEXT.md §13).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Social Media Analytics — Intel Synthesis",
        description=(
            "Jury-ready AI social intelligence backend. "
            "Analyzes Twitter/X conversations across sentiment, "
            "demographics, trends and interaction networks."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoints (liveness + readiness)
    app.include_router(health_router)

    # Analytics Read API v1
    app.include_router(api_v1_router)

    return app


# Module-level application instance used by uvicorn and tests.
app = create_app()
