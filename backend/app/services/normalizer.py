from datetime import datetime, timezone
from typing import Any, Dict

from twscrape.models import Tweet, User

from app.schemas.tweet import TweetCreate
from app.schemas.user import UserCreate


def normalize_user(raw_user: User) -> UserCreate:
    """Translates a twscrape User object into a UserCreate schema."""
    raw_desc = getattr(raw_user, "rawDescription", None)
    desc = getattr(raw_user, "description", None)
    bio = raw_desc if isinstance(raw_desc, str) else (desc if isinstance(desc, str) else None)
    loc = getattr(raw_user, "location", None)
    img = getattr(raw_user, "profileImageUrl", None)
    return UserCreate(
        twitter_user_id=str(raw_user.id),
        username=raw_user.username if isinstance(raw_user.username, str) else str(raw_user.username),
        display_name=raw_user.displayname if isinstance(raw_user.displayname, str) else str(raw_user.displayname),
        bio=bio,
        profile_image_url=img if isinstance(img, str) else None,
        declared_location=loc if isinstance(loc, str) else None,
        followers_count=raw_user.followersCount if isinstance(raw_user.followersCount, int) else None,
        following_count=raw_user.friendsCount if isinstance(raw_user.friendsCount, int) else None,
        created_at=raw_user.created if isinstance(raw_user.created, datetime) else None,
        last_seen_at=datetime.now(timezone.utc),
    )


import json

def serialize_raw_payload(raw_obj: Any) -> dict | None:
    if raw_obj is None:
        return None
    data = raw_obj.dict() if hasattr(raw_obj, "dict") else (vars(raw_obj) if hasattr(raw_obj, "__dict__") else str(raw_obj))
    return json.loads(json.dumps(data, default=str))


def normalize_tweet(raw_tweet: Tweet, author_internal_id: int) -> TweetCreate:
    """Translates a twscrape Tweet object into a TweetCreate schema."""
    bookmark_count = getattr(raw_tweet, "bookmarkedCount", None)
    if bookmark_count is None:
        bookmark_count = getattr(raw_tweet, "bookmarkCount", None)

    return TweetCreate(
        twitter_tweet_id=str(raw_tweet.id),
        author_id=author_internal_id,
        text=raw_tweet.rawContent,
        created_at_utc=raw_tweet.date,
        conversation_id=str(raw_tweet.conversationId) if raw_tweet.conversationId else None,
        reply_to_tweet_id=str(raw_tweet.inReplyToTweetId) if raw_tweet.inReplyToTweetId else None,
        reply_to_user_id=str(raw_tweet.inReplyToUser.id) if raw_tweet.inReplyToUser else None,
        repost_of_tweet_id=str(raw_tweet.retweetedTweet.id) if getattr(raw_tweet, "retweetedTweet", None) else None,
        quoted_tweet_id=str(raw_tweet.quotedTweet.id) if getattr(raw_tweet, "quotedTweet", None) else None,
        like_count=raw_tweet.likeCount,
        retweet_count=raw_tweet.retweetCount,
        reply_count=raw_tweet.replyCount,
        quote_count=raw_tweet.quoteCount,
        bookmark_count=bookmark_count,
        raw_payload=serialize_raw_payload(raw_tweet),
    )


def extract_interaction_candidates(raw_tweet: Tweet) -> list[dict]:
    """
    Extracts raw interaction candidate metadata from a twscrape Tweet object.
    Returns a list of dicts with:
    - target_twitter_user_id: str
    - target_username: str | None
    - target_display_name: str | None
    - interaction_type: InteractionType ("reply", "repost", "quote", "mention")
    - timestamp_utc: datetime
    """
    from app.models.interaction import InteractionType

    candidates = []
    created_at = raw_tweet.date or datetime.now(timezone.utc)

    # 1. Reply
    if raw_tweet.inReplyToUser and raw_tweet.inReplyToUser.id:
        candidates.append({
            "target_twitter_user_id": str(raw_tweet.inReplyToUser.id),
            "target_username": raw_tweet.inReplyToUser.username,
            "target_display_name": getattr(raw_tweet.inReplyToUser, "displayname", None),
            "interaction_type": InteractionType.REPLY,
            "timestamp_utc": created_at,
        })

    # 2. Repost / Retweet
    retweeted = getattr(raw_tweet, "retweetedTweet", None)
    if retweeted and retweeted.user and retweeted.user.id:
        candidates.append({
            "target_twitter_user_id": str(retweeted.user.id),
            "target_username": retweeted.user.username,
            "target_display_name": getattr(retweeted.user, "displayname", None),
            "interaction_type": InteractionType.REPOST,
            "timestamp_utc": created_at,
        })

    # 3. Quote
    quoted = getattr(raw_tweet, "quotedTweet", None)
    if quoted and quoted.user and quoted.user.id:
        candidates.append({
            "target_twitter_user_id": str(quoted.user.id),
            "target_username": quoted.user.username,
            "target_display_name": getattr(quoted.user, "displayname", None),
            "interaction_type": InteractionType.QUOTE,
            "timestamp_utc": created_at,
        })

    # 4. Mentions
    mentioned_users = getattr(raw_tweet, "mentionedUsers", []) or []
    for user_ref in mentioned_users:
        if user_ref and getattr(user_ref, "id", None):
            # Avoid duplicate reply target if already captured as reply
            target_id = str(user_ref.id)
            if raw_tweet.inReplyToUser and str(raw_tweet.inReplyToUser.id) == target_id:
                continue
            candidates.append({
                "target_twitter_user_id": target_id,
                "target_username": getattr(user_ref, "username", None),
                "target_display_name": getattr(user_ref, "displayname", None),
                "interaction_type": InteractionType.MENTION,
                "timestamp_utc": created_at,
            })

    return candidates
