import datetime
from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from app.models.interaction import Interaction, InteractionType
from app.models.tweet import Tweet
from app.models.user import User
from app.schemas.interaction import InteractionCreate
from app.schemas.tweet import TweetCreate
from app.schemas.user import UserCreate
from app.services.ingestion import IngestionService


def test_upsert_user(db_session: Session):
    ingestion = IngestionService(db_session)

    # 1. Insert new user
    user_data = UserCreate(
        twitter_user_id="111", username="user1", followers_count=100
    )
    user = ingestion.upsert_user(user_data)
    assert user.id is not None
    assert user.twitter_user_id == "111"
    assert user.followers_count == 100

    # 2. Update existing user
    user_data_updated = UserCreate(
        twitter_user_id="111", username="user1_updated", followers_count=150
    )
    updated_user = ingestion.upsert_user(user_data_updated)
    assert updated_user.id == user.id
    assert updated_user.username == "user1_updated"
    assert updated_user.followers_count == 150


def test_insert_tweet(db_session: Session):
    ingestion = IngestionService(db_session)

    # 1. Insert User first
    user_data = UserCreate(twitter_user_id="222", username="user2")
    user = ingestion.upsert_user(user_data)

    # 2. Insert Tweet
    tweet_data = TweetCreate(
        twitter_tweet_id="999",
        author_id=user.id,
        text="Hello db",
        created_at_utc=datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc),
    )
    tweet = ingestion.insert_tweet(tweet_data)
    assert tweet.id is not None
    assert tweet.twitter_tweet_id == "999"
    assert tweet.text == "Hello db"

    # 3. Insert same Tweet again (idempotent return)
    tweet_again = ingestion.insert_tweet(tweet_data)
    assert tweet_again.id == tweet.id


def test_insert_interactions(db_session: Session):
    ingestion = IngestionService(db_session)

    u1 = ingestion.upsert_user(UserCreate(twitter_user_id="10", username="alice"))
    u2 = ingestion.upsert_user(UserCreate(twitter_user_id="20", username="bob"))

    inter_data = InteractionCreate(
        source_user_id=u1.id,
        target_user_id=u2.id,
        interaction_type=InteractionType.REPLY,
        timestamp_utc=datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc),
        weight=1.0,
    )
    created = ingestion.insert_interactions([inter_data])
    assert len(created) == 1
    assert created[0].id is not None
    assert created[0].source_user_id == u1.id
    assert created[0].target_user_id == u2.id

    # Regression test: Re-inserting same interaction data returns existing without creating duplicate
    created_again = ingestion.insert_interactions([inter_data])
    assert len(created_again) == 1
    assert created_again[0].id == created[0].id


def test_ingest_raw_tweet_end_to_end(db_session: Session):
    ingestion = IngestionService(db_session)

    mock_raw_user = MagicMock()
    mock_raw_user.id = 5001
    mock_raw_user.username = "tweet_author"
    mock_raw_user.displayname = "Author Name"
    mock_raw_user.description = "Bio"
    mock_raw_user.profileImageUrl = None
    mock_raw_user.location = None
    mock_raw_user.followersCount = 10
    mock_raw_user.friendsCount = 5
    mock_raw_user.created = None

    mock_raw_tweet = MagicMock()
    mock_raw_tweet.id = 9001
    mock_raw_tweet.user = mock_raw_user
    mock_raw_tweet.rawContent = "Hey @mention_target, replying to @reply_target"
    mock_raw_tweet.date = datetime.datetime(2021, 2, 1, tzinfo=datetime.timezone.utc)
    mock_raw_tweet.conversationId = None
    mock_raw_tweet.inReplyToTweetId = 8888
    mock_raw_tweet.inReplyToUser = MagicMock(id=6001, username="reply_target", displayname="Reply Target")
    mock_raw_tweet.retweetedTweet = None
    mock_raw_tweet.quotedTweet = None
    mock_raw_tweet.mentionedUsers = [MagicMock(id=7001, username="mention_target", displayname="Mention Target")]
    mock_raw_tweet.likeCount = 0
    mock_raw_tweet.retweetCount = 0
    mock_raw_tweet.replyCount = 0
    mock_raw_tweet.quoteCount = 0
    mock_raw_tweet.bookmarkCount = 0
    mock_raw_tweet.dict.return_value = {"id": 9001}

    author, tweet, interactions = ingestion.ingest_raw_tweet(mock_raw_tweet)

    assert author.twitter_user_id == "5001"
    assert tweet.twitter_tweet_id == "9001"
    assert len(interactions) == 2

    int_types = [i.interaction_type for i in interactions]
    assert InteractionType.REPLY in int_types
    assert InteractionType.MENTION in int_types
