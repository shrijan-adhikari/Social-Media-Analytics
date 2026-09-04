"""Pydantic v2 schemas for Interaction entities.

`InteractionCreate` is used by the ingestion/normalization pipeline.
`InteractionRead` is the API response shape.

Edge direction: source_user_id → target_user_id (see interaction.py for full docs).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.interaction import InteractionType


class InteractionCreate(BaseModel):
    """Data required to create an interaction record."""

    source_user_id: int = Field(..., description="Internal users.id of the actor")
    target_user_id: int = Field(..., description="Internal users.id of the target")
    tweet_id: int | None = Field(
        None, description="Internal tweets.id that produced this interaction"
    )
    interaction_type: InteractionType
    timestamp_utc: datetime = Field(..., description="Interaction timestamp (UTC)")
    weight: float = Field(1.0, ge=0.0, description="Edge weight for graph analysis")


class InteractionRead(BaseModel):
    """API response schema for an interaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_user_id: int
    target_user_id: int
    tweet_id: int | None = None
    interaction_type: InteractionType
    timestamp_utc: datetime
    weight: float
