from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from twscrape.models import Tweet as TwscrapeTweet

from app.models.interaction import Interaction
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.interaction import InteractionCreate
from app.schemas.tweet import TweetCreate
from app.schemas.user import UserCreate
from app.services.normalizer import (
    extract_interaction_candidates,
    normalize_tweet,
    normalize_user,
)


class IngestionService:
    """Handles persistence of normalized Twitter data into the canonical database."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_user(self, user_data: UserCreate) -> User:
        """
        Upserts a user based on their twitter_user_id.
        Query-then-update approach used for compatibility with both SQLite tests and Postgres.
        """
        stmt = select(User).where(User.twitter_user_id == user_data.twitter_user_id)
        user = self.db.scalar(stmt)

        if not user:
            user = User(**user_data.model_dump(exclude_unset=True))
            self.db.add(user)
        else:
            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def insert_tweet(self, tweet_data: TweetCreate) -> Tweet:
        """
        Inserts a tweet. If already present, returns the existing record.
        """
        stmt = select(Tweet).where(Tweet.twitter_tweet_id == tweet_data.twitter_tweet_id)
        tweet = self.db.scalar(stmt)

        if not tweet:
            tweet = Tweet(**tweet_data.model_dump(exclude_unset=True))
            self.db.add(tweet)
            self.db.commit()
            self.db.refresh(tweet)

        return tweet

    def insert_interactions(
        self, interactions_data: List[InteractionCreate]
    ) -> List[Interaction]:
        """
        Inserts multiple interaction edges, avoiding exact duplicate rows for the same tweet event.
        """
        interactions = []
        for data in interactions_data:
            stmt = select(Interaction).where(
                Interaction.source_user_id == data.source_user_id,
                Interaction.target_user_id == data.target_user_id,
                Interaction.tweet_id == data.tweet_id,
                Interaction.interaction_type == data.interaction_type,
            )
            existing = self.db.scalar(stmt)
            if not existing:
                interaction = Interaction(**data.model_dump(exclude_unset=True))
                self.db.add(interaction)
                interactions.append(interaction)
            else:
                interactions.append(existing)

        self.db.commit()
        for i in interactions:
            self.db.refresh(i)

        return interactions

    def ingest_raw_tweet(
        self, raw_tweet: TwscrapeTweet
    ) -> Tuple[User, Tweet, List[Interaction]]:
        """
        End-to-end ingestion of a single raw twscrape tweet:
        1. Normalize and upsert the author user.
        2. Normalize and insert the tweet entity.
        3. Extract interaction candidates (replies, reposts, quotes, mentions),
           upsert target users if necessary, and insert interaction edges.
        """
        # 1. Author user
        author_schema = normalize_user(raw_tweet.user)
        author_user = self.upsert_user(author_schema)

        # 2. Tweet
        tweet_schema = normalize_tweet(raw_tweet, author_internal_id=author_user.id)
        tweet_entity = self.insert_tweet(tweet_schema)

        # 3. Interactions
        candidates = extract_interaction_candidates(raw_tweet)
        interaction_schemas: List[InteractionCreate] = []

        for cand in candidates:
            # Ensure target user exists in our DB (create lightweight profile if not yet fully crawled)
            target_schema = UserCreate(
                twitter_user_id=cand["target_twitter_user_id"],
                username=cand["target_username"] or f"user_{cand['target_twitter_user_id']}",
                display_name=cand["target_display_name"],
            )
            target_user = self.upsert_user(target_schema)

            # Avoid self-loops in interaction graph if desired or keep them; convention is standard directed edge
            interaction_schemas.append(
                InteractionCreate(
                    source_user_id=author_user.id,
                    target_user_id=target_user.id,
                    tweet_id=tweet_entity.id,
                    interaction_type=cand["interaction_type"],
                    timestamp_utc=cand["timestamp_utc"],
                    weight=1.0,
                )
            )

        saved_interactions = []
        if interaction_schemas:
            saved_interactions = self.insert_interactions(interaction_schemas)

        return author_user, tweet_entity, saved_interactions
