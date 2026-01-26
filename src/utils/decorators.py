"""
Decorators for Sedaye Ma bot.
Includes admin authentication decorators.
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from config import settings, Messages
from src.database import get_db, Admin
from src.database.models import AdminRole
from sqlalchemy import select


def admin_required(func):
    """
    Decorator to require admin access for a handler.
    Checks if the user is in the admins table.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check database directly
        async with get_db() as session:
            result = await session.execute(
                select(Admin).where(Admin.telegram_id == user_id)
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                return await func(update, context, *args, **kwargs)
        
        # Not authorized
        if update.callback_query:
            await update.callback_query.answer(Messages.ADMIN_UNAUTHORIZED, show_alert=True)
        else:
            await update.message.reply_text(Messages.ADMIN_UNAUTHORIZED, parse_mode="MarkdownV2")
        
        return None
    
    return wrapper


def super_admin_required(func):
    """
    Decorator to require super admin access for a handler.
    Only checks the super admin list from settings.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check database for super_admin role
        async with get_db() as session:
            result = await session.execute(
                select(Admin).where(
                    Admin.telegram_id == user_id,
                    Admin.role == AdminRole.SUPER_ADMIN
                )
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                return await func(update, context, *args, **kwargs)
        
        # Not authorized
        if update.callback_query:
            await update.callback_query.answer(Messages.ADMIN_UNAUTHORIZED, show_alert=True)
        else:
            await update.message.reply_text(Messages.ADMIN_UNAUTHORIZED, parse_mode="MarkdownV2")
        
        return None
    
    return wrapper

# ═══════════════════════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Singleton Rate Limiter using Sliding Window logic.
    Tracks user requests and manages penalty boxes.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RateLimiter, cls).__new__(cls)
            cls._instance.user_requests = {}  # {user_id: [timestamp1, timestamp2]}
            cls._instance.banned_users = {}   # {user_id: banned_until_timestamp}
        return cls._instance

    def is_allowed(self, user_id: int, limit: int, window: int, penalty_time: int) -> tuple[bool, str]:
        """
        Check if request is allowed.
        Returns: (is_allowed, reason)
        """
        import time
        now = time.time()
        
        # 1. Check if user is banned
        if user_id in self.banned_users:
            banned_until = self.banned_users[user_id]
            if now < banned_until:
                return False, "banned"
            else:
                # Ban expired
                del self.banned_users[user_id]
                # Also clear old requests to give a fresh start
                if user_id in self.user_requests:
                    del self.user_requests[user_id]
        
        # 2. Initialize user history if needed
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
            
        # 3. Clean old requests (Sliding Window)
        # Keep only timestamps within the window
        history = self.user_requests[user_id]
        valid_since = now - window
        
        # Filter in place (efficient for small lists)
        new_history = [t for t in history if t > valid_since]
        self.user_requests[user_id] = new_history
        
        # 4. Check Limit
        if len(new_history) >= limit:
            # PENALTY BOX!
            self.banned_users[user_id] = now + penalty_time
            return False, "limit_exceeded"
            
        # 5. Record Request
        self.user_requests[user_id].append(now)
        return True, "ok"


def rate_limit(limit: int, window: int, penalty_time: int = 3600):
    """
    Decorator to rate limit handlers.
    
    Args:
        limit (int): Max requests allowed in window.
        window (int): Time window in seconds.
        penalty_time (int): Ban duration in seconds if limit exceeded (default 1h).
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not update.effective_user:
                return await func(update, context, *args, **kwargs)
                
            user_id = update.effective_user.id
            limiter = RateLimiter()
            
            allowed, reason = limiter.is_allowed(user_id, limit, window, penalty_time)
            
            if not allowed:
                if reason == "limit_exceeded":
                    # First time exceeding: Warn them? Or silent?
                    # Silent is better for security, but a generic warning helps normal users.
                    # We'll stop propagation immediately.
                    # Optional: Log it
                    print(f"RATE LIMIT: User {user_id} banned for {penalty_time}s")
                    pass
                elif reason == "banned":
                    # Already banned, ignore completely
                    pass
                
                # Stop processing (return None)
                return None
                
            return await func(update, context, *args, **kwargs)
            
        return wrapper
    return decorator
