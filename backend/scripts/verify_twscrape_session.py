import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.services.twitter_collector import TwitterCollector


async def check_session():
    settings = get_settings()
    collector = TwitterCollector()

    try:
        await collector.initialize()
    except Exception as e:
        print(f"SESSION_INIT_ERROR: {type(e).__name__}: {e}")
        return

    accounts = await collector.api.pool.get_all()
    if not accounts:
        print("NO_ACCOUNTS_IN_POOL")
        return

    acc = accounts[0]
    print(f"ACCOUNT_LOADED: True")
    print(f"ACCOUNT_ACTIVE: {acc.active}")
    print(f"ACCOUNT_ERROR_MSG: {acc.error_msg or 'None'}")

    if not acc.active:
        print("SESSION_NOT_ACTIVE")
        return

    # Perform a single minimal authenticated request (e.g., lookup username or self)
    test_handle = settings.TWITTER_USERNAME or "X"
    print(f"TESTING_AUTHENTICATED_REQUEST (lookup @{test_handle})...")
    try:
        user_info = await collector.get_user_by_login(test_handle)
        if user_info:
            print("AUTHENTICATED_REQUEST_SUCCESS: True")
            print(f"RESOLVED_USER: @{user_info.username} (Twitter ID: {user_info.id})")
        else:
            print("AUTHENTICATED_REQUEST_SUCCESS: False (user returned None)")
    except Exception as e:
        print("AUTHENTICATED_REQUEST_SUCCESS: False")
        print(f"REQUEST_ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(check_session())
