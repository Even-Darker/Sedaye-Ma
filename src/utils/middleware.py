"""
Middleware for Sedaye Ma bot.
Handles global tracking and logging.
"""
import logging
import time
from datetime import datetime, UTC
from telegram import Update
from telegram.ext import ContextTypes

from src.database import get_db, User
from src.utils.security import encrypt_id
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

class ActivityTracker:
    """
    Tracks user activity and updates last_seen timestamp.
    Uses in-memory cache to enforce 24h update rule and minimize DB load.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActivityTracker, cls).__new__(cls)
            # user_id -> last_db_update_timestamp (seconds since epoch)
            cls._instance._cache = {}
            cls._instance._update_interval = 24 * 3600 # 24 hours in seconds
            cls._instance._last_prune = time.time()
        return cls._instance

    def prune_cache(self):
        """Remove entries older than 24 hours to keep memory stable."""
        now = time.time()
        # Only prune if some time has passed since last prune (e.g. 1 hour)
        if now - self._last_prune < 3600:
            return
            
        expired_since = now - self._update_interval
        # Dictionary comprehension creates a new dict, which is safe
        self._cache = {uid: ts for uid, ts in self._cache.items() if ts > expired_since}
        self._last_prune = now
        logger.debug(f"ActivityTracker cache pruned. Remaining entries: {len(self._cache)}")

    async def __call__(self, update_obj: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming update."""
        if not update_obj.effective_user:
            return

        self.prune_cache()
        user_id = update_obj.effective_user.id
        now = time.time()
        
        # 1. Check in-memory cache
        last_update = self._cache.get(user_id)
        if last_update and (now - last_update < self._update_interval):
            # Recently updated, skip DB hit
            return

        # 2. Update DB and Cache
        try:
            enc_id = encrypt_id(user_id)
            async with get_db() as session:
                # We use an update statement directly to be efficient
                stmt = (
                    update(User)
                    .where(User.encrypted_chat_id == enc_id)
                    .values(last_seen=datetime.now(UTC).replace(tzinfo=None)) # removing tzinfo for sqlite compatibility if needed, though models use datetime.utcnow which is naive
                )
                result = await session.execute(stmt)
                await session.commit()
                
                # If no rows affected, user might not be in DB yet (e.g. first /start)
                # But start_command already handles registration.
                # We still update the cache to prevent constant retries if for some reason they aren't in DB.
                self._cache[user_id] = now
                
        except Exception as e:
            logger.error(f"Failed to update last_seen for user {user_id}: {e}")
