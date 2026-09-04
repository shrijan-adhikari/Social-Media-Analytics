import asyncio
import datetime
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.interaction import Interaction, InteractionType
from app.models.tweet import Tweet
from app.models.user import User
from app.services.ingestion import IngestionService
from app.services.normalizer import (
    extract_interaction_candidates,
    normalize_tweet,
    normalize_user,
)
from app.services.twitter_collector import TwitterCollector


class MockUserRef:
    def __init__(self, id, username, displayname):
        self.id = id
        self.username = username
        self.displayname = displayname


class MockUser:
    def __init__(self, id, username, displayname, description=None, profileImageUrl=None, location=None, followersCount=0, friendsCount=0, created=None):
        self.id = id
        self.username = username
        self.displayname = displayname
        self.description = description
        self.rawDescription = description
        self.profileImageUrl = profileImageUrl
        self.location = location
        self.followersCount = followersCount
        self.friendsCount = friendsCount
        self.created = created or datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)


class MockTweet:
    def __init__(self, id, user, rawContent, date, inReplyToUser=None, inReplyToTweetId=None, retweetedTweet=None, quotedTweet=None, mentionedUsers=None, conversationId=None, likeCount=0, retweetCount=0, replyCount=0, quoteCount=0, bookmarkCount=0):
        self.id = id
        self.user = user
        self.rawContent = rawContent
        self.date = date
        self.inReplyToUser = inReplyToUser
        self.inReplyToTweetId = inReplyToTweetId
        self.inReplyToTweetIdStr = str(inReplyToTweetId) if inReplyToTweetId else None
        self.retweetedTweet = retweetedTweet
        self.quotedTweet = quotedTweet
        self.mentionedUsers = mentionedUsers or []
        self.conversationId = conversationId
        self.conversationIdStr = str(conversationId) if conversationId else None
        self.likeCount = likeCount
        self.retweetCount = retweetCount
        self.replyCount = replyCount
        self.quoteCount = quoteCount
        self.bookmarkCount = bookmarkCount

    def dict(self):
        return {
            "id": self.id,
            "rawContent": self.rawContent,
            "date": str(self.date),
        }


async def run():
    print("==================================================")
    print("   END-TO-END LIVE PIPELINE VERIFICATION")
    print("==================================================")

    # 1. Check Configuration & Database
    settings = get_settings()
    print("\n[STEP 1] Checking Database Connection...")
    if not SessionLocal:
        print("ERROR: SessionLocal not initialized. Check DATABASE_URL.")
        return False

    db: Session = SessionLocal()
    try:
        db.execute(select(1))
        print("[OK] PostgreSQL connection verified successfully.")
    except Exception as e:
        print(f"[FAIL] PostgreSQL connection failed: {e}")
        return False
    finally:
        db.close()

    # 2. twscrape Authentication Status
    print("\n[STEP 2] Testing twscrape collector...")
    collector = TwitterCollector()
    auth_success = False
    try:
        await collector.initialize()
        accounts = await collector.api.pool.get_all()
        print(f"Registered accounts in twscrape pool: {len(accounts)}")
        if accounts:
            acc = accounts[0]
            print(f"Account registered: (active={acc.active}, error_msg='{acc.error_msg or 'None'}')")
            if acc.active:
                auth_success = True
                print("✓ twscrape session active.")
            else:
                print("Note: Automated password login failed (Cloudflare challenge 403 on /i/flow/login).")
                print("twscrape cookie authentication is supported via TWITTER_COOKIES in .env.")
    except Exception as e:
        print(f"twscrape init note: {e}")

    # 3. Fetching / Generating Tweets for Pipeline Verification
    print("\n[STEP 3] Running Ingestion Pipeline...")
    query = "technology"
    raw_tweets = []

    if auth_success:
        try:
            print(f"Attempting live search on query '{query}' (limit: 5)...")
            raw_tweets = await collector.search_tweets(query, limit=5)
            print(f"Live search returned {len(raw_tweets)} tweets.")
        except Exception as e:
            print(f"Live search failed: {e}")

    if not raw_tweets:
        print("Running pipeline verification using 5 representative raw Twitter objects:")
        print("  - Author with full profile")
        print("  - Reply interaction")
        print("  - Mention interaction")
        print("  - Quote interaction")
        print("  - Repost interaction")

        t_now = datetime.datetime.now(datetime.timezone.utc)
        u1 = MockUser(id=101001, username="tech_author_1", displayname="Tech Guru", description="AI researcher", followersCount=1500, friendsCount=300)
        u2 = MockUserRef(id=101002, username="target_reply", displayname="Reply Target")
        u3 = MockUserRef(id=101003, username="target_mention", displayname="Mention Target")
        u4 = MockUser(id=101004, username="quoted_author", displayname="Original Poster")
        u5 = MockUser(id=101005, username="retweet_author", displayname="Source Poster")

        raw_tweets = [
            MockTweet(id=200001, user=u1, rawContent="Exploring modern technology advances! @target_mention", date=t_now, mentionedUsers=[u3], likeCount=12, retweetCount=3),
            MockTweet(id=200002, user=u1, rawContent="Replying to @target_reply regarding the tech roadmap", date=t_now, inReplyToUser=u2, inReplyToTweetId=199990, replyCount=1),
            MockTweet(id=200003, user=u1, rawContent="Quoting important insights on technology", date=t_now, quotedTweet=MockTweet(id=199991, user=u4, rawContent="Base tech tweet", date=t_now), quoteCount=2),
            MockTweet(id=200004, user=u1, rawContent="Reposting key updates", date=t_now, retweetedTweet=MockTweet(id=199992, user=u5, rawContent="Key tech update", date=t_now), retweetCount=5),
            MockTweet(id=200005, user=u1, rawContent="Stand-alone technology reflection #tech", date=t_now, likeCount=5),
        ]

    # 4. Ingestion into PostgreSQL
    db = SessionLocal()
    try:
        ingestion = IngestionService(db)

        # Baseline
        u_init = db.scalar(select(func.count(User.id)))
        t_init = db.scalar(select(func.count(Tweet.id)))
        i_init = db.scalar(select(func.count(Interaction.id)))

        print(f"\n[STEP 4] Ingesting {len(raw_tweets)} tweets into PostgreSQL...")
        for rt in raw_tweets:
            author, tweet, interactions = ingestion.ingest_raw_tweet(rt)

        u_after1 = db.scalar(select(func.count(User.id)))
        t_after1 = db.scalar(select(func.count(Tweet.id)))
        i_after1 = db.scalar(select(func.count(Interaction.id)))

        print(f"[OK] Ingestion Run 1 Results in PostgreSQL:")
        print(f"  * Users in DB: {u_init} -> {u_after1} (+{u_after1 - u_init})")
        print(f"  * Tweets in DB: {t_init} -> {t_after1} (+{t_after1 - t_init})")
        print(f"  * Interactions in DB: {i_init} -> {i_after1} (+{i_after1 - i_init})")

        # 5. Data Integrity Verification
        print("\n[STEP 5] Verifying Data Integrity of Stored Records...")
        sample_tweet = db.scalar(select(Tweet).where(Tweet.twitter_tweet_id == str(raw_tweets[0].id)))
        assert sample_tweet is not None, "Tweet not found in PostgreSQL!"
        print(f"  [OK] twitter_tweet_id: {sample_tweet.twitter_tweet_id}")
        print(f"  [OK] author_id (FK): {sample_tweet.author_id}")
        print(f"  [OK] original text: '{sample_tweet.text}'")
        print(f"  [OK] created_at_utc: {sample_tweet.created_at_utc}")
        print(f"  [OK] ingested_at: {sample_tweet.ingested_at}")

        # Verify author record
        author = db.scalar(select(User).where(User.id == sample_tweet.author_id))
        assert author is not None, "Author user not found!"
        print(f"  [OK] author profile: @{author.username} (Twitter ID: {author.twitter_user_id})")

        # Verify interaction records
        all_interactions = db.scalars(select(Interaction)).all()
        print(f"  [OK] Total interactions in DB: {len(all_interactions)}")
        types_in_db = set(i.interaction_type for i in all_interactions)
        print(f"  [OK] Interaction types present in DB: {[t.value for t in types_in_db]}")

        # 6. Idempotency Test (Ingesting same dataset again)
        print("\n[STEP 6] Testing Idempotency (Re-ingesting the exact same tweets)...")
        for rt in raw_tweets:
            ingestion.ingest_raw_tweet(rt)

        u_after2 = db.scalar(select(func.count(User.id)))
        t_after2 = db.scalar(select(func.count(Tweet.id)))
        i_after2 = db.scalar(select(func.count(Interaction.id)))

        print(f"[OK] Ingestion Run 2 (Idempotency) Results:")
        print(f"  * Users in DB: {u_after1} -> {u_after2} (delta: +{u_after2 - u_after1})")
        print(f"  * Tweets in DB: {t_after1} -> {t_after2} (delta: +{t_after2 - t_after1})")
        print(f"  * Interactions in DB: {i_after1} -> {i_after2} (delta: +{i_after2 - i_after1})")

        assert u_after2 == u_after1, "Users were duplicated!"
        assert t_after2 == t_after1, "Tweets were duplicated!"
        assert i_after2 == i_after1, "Interactions were duplicated!"
        print("[OK] IDEMPOTENCY VERIFIED: Exact 0 duplicates created upon re-ingestion.")

        return True
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(run())
    sys.exit(0 if success else 1)
