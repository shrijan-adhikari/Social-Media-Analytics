import os
import asyncio
from pathlib import Path
from typing import AsyncGenerator, List

from twscrape import API, gather
from twscrape.models import Tweet, User

from app.core.config import get_settings

class TwitterCollector:
    """
    Wrapper around twscrape.API to manage Twitter data collection.
    Persists session/accounts in an isolated SQLite database.
    """
    def __init__(self, db_filename: str = "twscrape_accounts.db"):
        # Store twscrape DB in the backend directory
        db_path = Path(__file__).parent.parent.parent / db_filename
        self.api = API(pool=str(db_path))

    async def initialize(self) -> None:
        """Initializes twscrape and logs in or sets cookies using environment settings."""
        settings = get_settings()
        if settings.TWITTER_USERNAME:
            if settings.TWITTER_COOKIES:
                await self.api.pool.add_account_cookies(
                    username=settings.TWITTER_USERNAME,
                    cookies=settings.TWITTER_COOKIES,
                )
            elif settings.TWITTER_PASSWORD:
                await self.api.pool.add_account(
                    username=settings.TWITTER_USERNAME,
                    password=settings.TWITTER_PASSWORD or "",
                    email=settings.TWITTER_EMAIL or "",
                    email_password="",
                )
                await self.api.pool.login_all()

    async def add_account(self, username: str, password: str, email: str, email_password: str):
        """Adds a Twitter account to the pool and logs in."""
        await self.api.pool.add_account(username, password, email, email_password)
        await self.api.pool.login_all()

    async def get_user_by_login(self, username: str) -> User | None:
        """Fetches a single user's profile by their handle."""
        return await self.api.user_by_login(username)

    async def search_tweets(self, query: str, limit: int = 20) -> List[Tweet]:
        """Searches tweets using a given query. Defaults to small limit for testing."""
        return await gather(self.api.search(query, limit=limit))

    async def get_user_tweets(self, user_id: int, limit: int = 20) -> List[Tweet]:
        """Fetches recent tweets for a specific user ID."""
        return await gather(self.api.user_tweets(user_id, limit=limit))
