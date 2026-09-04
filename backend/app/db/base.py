"""Declarative base for all SQLAlchemy ORM models.

All model modules must be imported here so that Alembic autogenerate
can discover the full metadata when env.py runs.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all application models."""


# Import all models so their table metadata is registered on Base.
# This import must come after Base is defined.
from app.models import user, tweet, interaction  # noqa: E402, F401
