"""Interaction ORM model — persistent directed interaction edges.

Each row represents a single directed interaction event between two users.
This table is the persistent source for NetworkX graph construction (Phase 2).

Edge direction convention:
  source_user_id → target_user_id

Meaning by type:
  reply:   source replied to target's tweet
  repost:  source reposted target's tweet
  quote:   source quoted target's tweet
  mention: source mentioned target in a tweet

This direction represents "attention flow" (source sends attention toward target)
and is consistent with influence models where high in-degree → influential node.

The `weight` field allows future weighting schemes (e.g., reply > repost) during
PageRank computation without schema changes.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InteractionType(str, enum.Enum):
    """Supported interaction types between Twitter users.

    Using str mixin so values serialize cleanly to/from JSON and Pydantic.
    """

    REPLY = "reply"
    REPOST = "repost"
    QUOTE = "quote"
    MENTION = "mention"


class Interaction(Base):
    """Directed interaction event between two Twitter users.

    source_user_id → target_user_id with interaction_type context.
    tweet_id links back to the tweet that caused this interaction.
    """

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Edge endpoints — both reference our internal users.id.
    source_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The tweet that produced this interaction (nullable for mention-only cases).
    tweet_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("tweets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(
            InteractionType,
            name="interaction_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    # UTC timestamp from the source tweet; used for temporal graph snapshots.
    timestamp_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Edge weight — default 1.0; enables future weighted PageRank without schema change.
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationships
    source_user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="outgoing_interactions",
        foreign_keys=[source_user_id],
    )
    target_user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="incoming_interactions",
        foreign_keys=[target_user_id],
    )
    tweet: Mapped["Tweet | None"] = relationship(  # noqa: F821
        "Tweet", back_populates="interactions"
    )

    __table_args__ = (
        # Primary graph traversal index: find all interactions between two users.
        Index(
            "ix_interactions_source_target_type",
            "source_user_id",
            "target_user_id",
            "interaction_type",
        ),
        # Temporal graph snapshot queries.
        Index("ix_interactions_timestamp_utc", "timestamp_utc"),
    )

    def __repr__(self) -> str:
        return (
            f"<Interaction id={self.id} "
            f"{self.source_user_id}→{self.target_user_id} "
            f"type={self.interaction_type.value!r}>"
        )
