import datetime
from unittest.mock import MagicMock

from app.models.interaction import InteractionType
from app.schemas.tweet import TweetCreate
from app.schemas.user import UserCreate
from app.services.normalizer import (
    extract_interaction_candidates,
    normalize_tweet,
    normalize_user,
)


def test_normalize_user():
    mock_raw_user = MagicMock()
    mock_raw_user.id = 123456789
    mock_raw_user.username = "testuser"
    mock_raw_user.displayname = "Test User"
    mock_raw_user.description = "Test bio"
    mock_raw_user.profileImageUrl = "http://example.com/img.jpg"
    mock_raw_user.location = "Test City"
    mock_raw_user.followersCount = 100
    mock_raw_user.friendsCount = 50
    mock_raw_user.created = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)

    user_create = normalize_user(mock_raw_user)
    assert isinstance(user_create, UserCreate)
    assert user_create.twitter_user_id == "123456789"
    assert user_create.username == "testuser"
    assert user_create.followers_count == 100


def test_normalize_tweet():
    mock_raw_tweet = MagicMock()
    mock_raw_tweet.id = 987654321
    mock_raw_tweet.rawContent = "Hello world"
    mock_raw_tweet.date = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
    mock_raw_tweet.conversationId = 111111111
    mock_raw_tweet.inReplyToTweetId = None
    mock_raw_tweet.inReplyToUser = None
    mock_raw_tweet.retweetedTweet = None
    mock_raw_tweet.quotedTweet = None
    mock_raw_tweet.likeCount = 10
    mock_raw_tweet.retweetCount = 5
    mock_raw_tweet.replyCount = 2
    mock_raw_tweet.quoteCount = 1
    mock_raw_tweet.bookmarkCount = 0
    mock_raw_tweet.dict.return_value = {"id": 987654321}

    tweet_create = normalize_tweet(mock_raw_tweet, author_internal_id=1)

    assert isinstance(tweet_create, TweetCreate)
    assert tweet_create.twitter_tweet_id == "987654321"
    assert tweet_create.author_id == 1
    assert tweet_create.text == "Hello world"
    assert tweet_create.conversation_id == "111111111"
    assert tweet_create.reply_to_tweet_id is None
    assert tweet_create.raw_payload == {"id": 987654321}


def test_extract_interaction_candidates_reply():
    mock_tweet = MagicMock()
    mock_tweet.date = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
    mock_tweet.inReplyToUser = MagicMock(id=55555, username="target_reply", displayname="Target")
    mock_tweet.retweetedTweet = None
    mock_tweet.quotedTweet = None
    mock_tweet.mentionedUsers = []

    candidates = extract_interaction_candidates(mock_tweet)
    assert len(candidates) == 1
    assert candidates[0]["interaction_type"] == InteractionType.REPLY
    assert candidates[0]["target_twitter_user_id"] == "55555"
    assert candidates[0]["target_username"] == "target_reply"


def test_extract_interaction_candidates_mentions_and_quotes():
    mock_tweet = MagicMock()
    mock_tweet.date = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
    mock_tweet.inReplyToUser = None
    mock_tweet.retweetedTweet = None

    # Quoted tweet
    mock_quoted = MagicMock()
    mock_quoted.user = MagicMock(id=777, username="quoted_user", displayname="Quoted")
    mock_tweet.quotedTweet = mock_quoted

    # Mentioned users
    mock_mention = MagicMock(id=888, username="mentioned_user", displayname="Mentioned")
    mock_tweet.mentionedUsers = [mock_mention]

    candidates = extract_interaction_candidates(mock_tweet)
    assert len(candidates) == 2
    types = [c["interaction_type"] for c in candidates]
    assert InteractionType.QUOTE in types
    assert InteractionType.MENTION in types
