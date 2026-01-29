import asyncio
import unittest
import os
import sys
from unittest.mock import AsyncMock, patch
from telegram.error import Forbidden

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "Vj75PKfqG2TvdP3mFmxH3qp7lowbaNweLzK3HYAucB8="

from src.database import AsyncSessionLocal
from src.database.models import Base, User, Announcement, AnnouncementCategory
from src.services.notification_service import NotificationService
from src.utils.middleware import ActivityTracker
from src.utils.security import encrypt_id

class TestBlockedUserTracking(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from src.database import connection
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import StaticPool
        
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        connection.engine = self.engine
        connection.AsyncSessionLocal.configure(bind=self.engine)
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.bot = AsyncMock()
        self.service = NotificationService(self.bot)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_blocked_user_flag_toggled_on_broadcast(self):
        """Verify that is_blocked_by_user is set to True when Forbidden is raised."""
        user_id = 456
        async with AsyncSessionLocal() as session:
            user = User(
                encrypted_chat_id=encrypt_id(user_id),
                announcements_urgent=True,
                is_blocked_by_user=False
            )
            session.add(user)
            await session.commit()
        
        # Mock bot to raise Forbidden
        self.bot.send_message.side_effect = Forbidden("Bot was blocked by the user")
        
        announcement = Announcement(
            title="Test",
            content="Important",
            category=AnnouncementCategory.URGENT
        )
        
        # This should trigger the Forbidden catch and toggle the flag
        await self.service.broadcast_announcement(announcement)
        
        # Verify database update
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            res = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(user_id)))
            updated_user = res.scalar_one()
            self.assertTrue(updated_user.is_blocked_by_user, "is_blocked_by_user should be True after Forbidden error")

    async def test_multiple_users_mixed_status(self):
        """Test with one blocking user and one active user."""
        users = [
            {"id": 1, "block": True},
            {"id": 2, "block": False}
        ]
        
        async with AsyncSessionLocal() as session:
            for u in users:
                session.add(User(
                    encrypted_chat_id=encrypt_id(u["id"]),
                    announcements_news=True,
                    is_blocked_by_user=False
                ))
            await session.commit()
            
        # Mock send_message to block for user 1
        async def mock_send(chat_id, **kwargs):
            if chat_id == 1: # Simplified for testing, real code decrypts
                raise Forbidden("Blocked")
            return AsyncMock()
            
        # We need to reach into the loop where decrypt_id happens
        # Let's mock send_message more carefully
        blocking_chat_id = 1
        
        async def side_effect(chat_id, **kwargs):
            if chat_id == blocking_chat_id:
                raise Forbidden("Blocked")
            return AsyncMock()
            
        self.bot.send_message.side_effect = side_effect
        
        announcement = Announcement(
            title="News",
            content="Updates",
            category=AnnouncementCategory.NEWS
        )
        
        await self.service.broadcast_announcement(announcement)
        
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            # Check user 1 (blocked)
            res1 = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(1)))
            u1 = res1.scalar_one()
            self.assertTrue(u1.is_blocked_by_user)
            
            # Check user 2 (active)
            res2 = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(2)))
            u2 = res2.scalar_one()
            self.assertFalse(u2.is_blocked_by_user)

    async def test_auto_unblock_on_interaction(self):
        """Verify that is_blocked_by_user is reset to False on next interaction."""
        user_id = 789
        async with AsyncSessionLocal() as session:
            session.add(User(
                encrypted_chat_id=encrypt_id(user_id),
                is_blocked_by_user=True
            ))
            await session.commit()
            
        tracker = ActivityTracker()
        # Reset tracker cache for this user to force DB update
        tracker._cache.pop(user_id, None)
        
        update_obj = AsyncMock()
        update_obj.effective_user.id = user_id
        context = AsyncMock()
        
        await tracker(update_obj, context)
        
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            res = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(user_id)))
            updated_user = res.scalar_one()
            self.assertFalse(updated_user.is_blocked_by_user, "is_blocked_by_user should be reset to False on interaction")

if __name__ == "__main__":
    unittest.main()
