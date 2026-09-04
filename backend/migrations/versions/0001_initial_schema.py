"""Initial schema: users, tweets, interactions.

Revision ID: 0001
Revises:
Create Date: 2026-09-01

Creates the three foundational tables for Phase 1.

Design notes:
- Twitter IDs stored as VARCHAR(32) TEXT to preserve full 64-bit snowflake
  precision (avoids JavaScript >2^53 precision loss in JSON).
- All timestamps are TIMESTAMPTZ (timezone-aware UTC).
- interaction_type_enum is a native PostgreSQL ENUM for storage efficiency.
- JSONB for raw_payload enables future filtered queries on stored payloads.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("twitter_user_id", sa.String(32), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("profile_image_url", sa.Text(), nullable=True),
        sa.Column("declared_location", sa.String(255), nullable=True),
        sa.Column("followers_count", sa.Integer(), nullable=True),
        sa.Column("following_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twitter_user_id", name="uq_users_twitter_user_id"),
    )
    op.create_index("ix_users_twitter_user_id", "users", ["twitter_user_id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])

    # ── tweets ─────────────────────────────────────────────────────────────
    op.create_table(
        "tweets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("twitter_tweet_id", sa.String(32), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conversation_id", sa.String(32), nullable=True),
        sa.Column("reply_to_tweet_id", sa.String(32), nullable=True),
        sa.Column("reply_to_user_id", sa.String(32), nullable=True),
        sa.Column("repost_of_tweet_id", sa.String(32), nullable=True),
        sa.Column("quoted_tweet_id", sa.String(32), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("retweet_count", sa.Integer(), nullable=True),
        sa.Column("reply_count", sa.Integer(), nullable=True),
        sa.Column("quote_count", sa.Integer(), nullable=True),
        sa.Column("bookmark_count", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twitter_tweet_id", name="uq_tweets_twitter_tweet_id"),
    )
    op.create_index("ix_tweets_twitter_tweet_id", "tweets", ["twitter_tweet_id"])
    op.create_index("ix_tweets_author_id", "tweets", ["author_id"])
    op.create_index("ix_tweets_created_at_utc", "tweets", ["created_at_utc"])
    op.create_index(
        "ix_tweets_author_created", "tweets", ["author_id", "created_at_utc"]
    )
    op.create_index("ix_tweets_conversation_id", "tweets", ["conversation_id"])
    op.create_index("ix_tweets_ingested_at", "tweets", ["ingested_at"])

    # ── interactions ───────────────────────────────────────────────────────
    # ENUM creation is handled automatically by sa.Enum inside op.create_table
    op.create_table(
        "interactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_user_id", sa.BigInteger(), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=False),
        sa.Column("tweet_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "interaction_type",
            sa.Enum(
                "reply", "repost", "quote", "mention",
                name="interaction_type_enum",
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.ForeignKeyConstraint(
            ["source_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tweet_id"], ["tweets.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interactions_source_user_id", "interactions", ["source_user_id"])
    op.create_index("ix_interactions_target_user_id", "interactions", ["target_user_id"])
    op.create_index("ix_interactions_tweet_id", "interactions", ["tweet_id"])
    op.create_index(
        "ix_interactions_source_target_type",
        "interactions",
        ["source_user_id", "target_user_id", "interaction_type"],
    )
    op.create_index(
        "ix_interactions_timestamp_utc", "interactions", ["timestamp_utc"]
    )
    op.create_index(
        "ix_interactions_interaction_type", "interactions", ["interaction_type"]
    )


def downgrade() -> None:
    op.drop_table("interactions")
    # Drop the ENUM type after the table using it is gone.
    interaction_type_enum = postgresql.ENUM(
        "reply", "repost", "quote", "mention",
        name="interaction_type_enum",
    )
    interaction_type_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_table("tweets")
    op.drop_table("users")
