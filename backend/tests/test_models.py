"""Tests for ORM models and Pydantic schemas.

Unit tests — no PostgreSQL required. SQLite in-memory is used for ORM tests.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


# ── InteractionType enum ─────────────────────────────────────────────────────

def test_interaction_type_values() -> None:
    """InteractionType must define exactly the four expected values."""
    from app.models.interaction import InteractionType

    assert InteractionType.REPLY.value == "reply"
    assert InteractionType.REPOST.value == "repost"
    assert InteractionType.QUOTE.value == "quote"
    assert InteractionType.MENTION.value == "mention"


def test_interaction_type_is_str_enum() -> None:
    """InteractionType values should be usable as plain strings via == comparison."""
    from app.models.interaction import InteractionType

    # str(enum) behavior varies by Python version for str subclasses.
    # Use .value for reliable string extraction.
    assert InteractionType.REPLY == "reply"
    assert InteractionType.REPOST.value == "repost"


def test_interaction_type_invalid_value_raises() -> None:
    """Constructing InteractionType with an invalid value should raise ValueError."""
    from app.models.interaction import InteractionType

    with pytest.raises(ValueError):
        InteractionType("follow")


# ── UserCreate schema ─────────────────────────────────────────────────────────

def test_user_create_valid() -> None:
    """UserCreate should accept valid data."""
    from app.schemas.user import UserCreate

    u = UserCreate(
        twitter_user_id="123456789",
        username="test_user",
        display_name="Test User",
        followers_count=100,
    )
    assert u.twitter_user_id == "123456789"
    assert u.username == "test_user"
    assert u.followers_count == 100
    assert u.bio is None


def test_user_create_missing_required_fields() -> None:
    """UserCreate should raise ValidationError when required fields are missing."""
    from app.schemas.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(username="only_username")  # twitter_user_id missing


def test_user_create_empty_username_rejected() -> None:
    """UserCreate should reject an empty username."""
    from app.schemas.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(twitter_user_id="123", username="")


# ── TweetCreate schema ────────────────────────────────────────────────────────

def test_tweet_create_valid() -> None:
    """TweetCreate should accept valid data."""
    from app.schemas.tweet import TweetCreate

    now = datetime.now(timezone.utc)
    t = TweetCreate(
        twitter_tweet_id="9876543210",
        author_id=1,
        text="Hello world",
        created_at_utc=now,
    )
    assert t.twitter_tweet_id == "9876543210"
    assert t.text == "Hello world"
    assert t.raw_payload is None


def test_tweet_create_rejects_empty_text() -> None:
    """TweetCreate should reject empty tweet text."""
    from app.schemas.tweet import TweetCreate

    with pytest.raises(ValidationError):
        TweetCreate(
            twitter_tweet_id="111",
            author_id=1,
            text="",
            created_at_utc=datetime.now(timezone.utc),
        )


def test_tweet_create_accepts_raw_payload() -> None:
    """TweetCreate should accept arbitrary dict as raw_payload."""
    from app.schemas.tweet import TweetCreate

    now = datetime.now(timezone.utc)
    t = TweetCreate(
        twitter_tweet_id="111",
        author_id=1,
        text="Tweet with payload",
        created_at_utc=now,
        raw_payload={"key": "value", "nested": {"a": 1}},
    )
    assert t.raw_payload == {"key": "value", "nested": {"a": 1}}


# ── InteractionCreate schema ──────────────────────────────────────────────────

def test_interaction_create_valid() -> None:
    """InteractionCreate should accept valid data."""
    from app.schemas.interaction import InteractionCreate
    from app.models.interaction import InteractionType

    now = datetime.now(timezone.utc)
    i = InteractionCreate(
        source_user_id=1,
        target_user_id=2,
        interaction_type=InteractionType.REPLY,
        timestamp_utc=now,
    )
    assert i.source_user_id == 1
    assert i.target_user_id == 2
    assert i.interaction_type == InteractionType.REPLY
    assert i.weight == 1.0
    assert i.tweet_id is None


def test_interaction_create_accepts_string_type() -> None:
    """InteractionCreate should accept the string value of InteractionType."""
    from app.schemas.interaction import InteractionCreate
    from app.models.interaction import InteractionType

    i = InteractionCreate(
        source_user_id=1,
        target_user_id=2,
        interaction_type="quote",
        timestamp_utc=datetime.now(timezone.utc),
    )
    assert i.interaction_type == InteractionType.QUOTE


def test_interaction_create_invalid_type_raises() -> None:
    """InteractionCreate should reject unknown interaction_type values."""
    from app.schemas.interaction import InteractionCreate

    with pytest.raises(ValidationError):
        InteractionCreate(
            source_user_id=1,
            target_user_id=2,
            interaction_type="follow",
            timestamp_utc=datetime.now(timezone.utc),
        )


def test_interaction_create_negative_weight_rejected() -> None:
    """InteractionCreate should reject negative weight values."""
    from app.schemas.interaction import InteractionCreate

    with pytest.raises(ValidationError):
        InteractionCreate(
            source_user_id=1,
            target_user_id=2,
            interaction_type="reply",
            timestamp_utc=datetime.now(timezone.utc),
            weight=-0.5,
        )


# ── ORM model creation via SQLite ─────────────────────────────────────────────

def test_user_orm_creation(db_session) -> None:
    """User ORM model should be createable and queryable in SQLite."""
    from app.models.user import User

    user = User(
        twitter_user_id="42",
        username="alice",
        display_name="Alice",
        followers_count=500,
    )
    db_session.add(user)
    db_session.flush()

    fetched = db_session.query(User).filter_by(twitter_user_id="42").one()
    assert fetched.username == "alice"
    assert fetched.id is not None


def test_tweet_orm_creation(db_session) -> None:
    """Tweet ORM model should be createable and queryable in SQLite."""
    from app.models.user import User
    from app.models.tweet import Tweet

    user = User(twitter_user_id="10", username="bob")
    db_session.add(user)
    db_session.flush()

    now = datetime.now(timezone.utc)
    tweet = Tweet(
        twitter_tweet_id="999",
        author_id=user.id,
        text="Test tweet",
        created_at_utc=now,
    )
    db_session.add(tweet)
    db_session.flush()

    fetched = db_session.query(Tweet).filter_by(twitter_tweet_id="999").one()
    assert fetched.text == "Test tweet"
    assert fetched.author_id == user.id


def test_interaction_orm_creation(db_session) -> None:
    """Interaction ORM model should be createable and queryable in SQLite."""
    from app.models.user import User
    from app.models.tweet import Tweet
    from app.models.interaction import Interaction, InteractionType

    src = User(twitter_user_id="20", username="src")
    tgt = User(twitter_user_id="21", username="tgt")
    db_session.add_all([src, tgt])
    db_session.flush()

    now = datetime.now(timezone.utc)
    tweet = Tweet(
        twitter_tweet_id="888",
        author_id=src.id,
        text="source tweet",
        created_at_utc=now,
    )
    db_session.add(tweet)
    db_session.flush()

    interaction = Interaction(
        source_user_id=src.id,
        target_user_id=tgt.id,
        tweet_id=tweet.id,
        interaction_type=InteractionType.REPLY,
        timestamp_utc=now,
        weight=1.0,
    )
    db_session.add(interaction)
    db_session.flush()

    fetched = db_session.query(Interaction).filter_by(id=interaction.id).one()
    assert fetched.source_user_id == src.id
    assert fetched.target_user_id == tgt.id
    assert fetched.interaction_type == InteractionType.REPLY


def test_twitter_id_stored_as_string(db_session) -> None:
    """Twitter IDs must be stored and retrieved as strings (not ints)."""
    from app.models.user import User

    # Snowflake ID that would lose precision as a float (> 2^53)
    big_id = "1234567890123456789"
    user = User(twitter_user_id=big_id, username="bigid_user")
    db_session.add(user)
    db_session.flush()

    fetched = db_session.query(User).filter_by(twitter_user_id=big_id).one()
    # Must be a string, not an integer, to prevent precision loss in JSON.
    assert isinstance(fetched.twitter_user_id, str)
    assert fetched.twitter_user_id == big_id
