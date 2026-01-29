import asyncio
import unittest
import os
import sys
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, UTC

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["SUPER_ADMIN_IDS"] = "123456789"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "Vj75PKfqG2TvdP3mFmxH3qp7lowbaNweLzK3HYAucB8="

from src.database import init_db, AsyncSessionLocal
from src.database.models import Base, User, InstagramTarget, Victory, SolidarityMessage, Petition, Admin, AdminRole, PetitionStatus
from src.handlers.admin_stats import admin_stats
from src.utils.security import encrypt_id

class TestAdminStats(unittest.IsolatedAsyncioTestCase):
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
            
        self.admin_id = 123456789
        async with AsyncSessionLocal() as session:
            session.add(Admin(encrypted_telegram_id=encrypt_id(self.admin_id), role=AdminRole.SUPER_ADMIN))
            await session.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_stats_aggregation(self):
        """Verify that the /stat command aggregates data correctly."""
        now = datetime.now(UTC).replace(tzinfo=None)
        
        async with AsyncSessionLocal() as session:
            # Add Users
            session.add(User(encrypted_chat_id=encrypt_id(1), last_seen=now - timedelta(hours=2)))   # DAU
            session.add(User(encrypted_chat_id=encrypt_id(2), last_seen=now - timedelta(days=5)))    # WAU
            session.add(User(encrypted_chat_id=encrypt_id(3), last_seen=now - timedelta(days=20)))   # MAU
            session.add(User(encrypted_chat_id=encrypt_id(4), last_seen=now - timedelta(days=40)))   # Old
            session.add(User(encrypted_chat_id=encrypt_id(5), is_blocked_by_user=True))             # Blocked
            
            # Add Targets & Victories
            t1 = InstagramTarget(ig_handle="target1", anonymous_report_count=100)
            t2 = InstagramTarget(ig_handle="target2", anonymous_report_count=200)
            session.add(t1)
            session.add(t2)
            await session.flush()
            
            session.add(Victory(target_id=t1.id, final_report_count=100))
            
            # Add Solidarity
            session.add(SolidarityMessage(message="Stay strong", hearts=50, is_approved=True))
            
            # Add Petitions
            session.add(Petition(title="P1", description="D", url="U", status=PetitionStatus.ACTIVE))
            
            await session.commit()
            
        update = AsyncMock()
        update.effective_user.id = self.admin_id
        update.message.reply_text = AsyncMock()
        context = AsyncMock()
        
        await admin_stats(update, context)
        
        # Verify content exists, ignoring ZWNJ and exact escaping complexity
        args, kwargs = update.message.reply_text.call_args
        msg = args[0]
        self.assertIn("تعداد کل", msg)
        self.assertIn("۲۴ ساعت", msg)
        self.assertIn("۷ روز", msg)
        self.assertIn("مسدود", msg)
        
        # Check for numbers in Arabic digits (as produced by {:,})
        # Check for numbers
        self.assertIn("5", msg) # 4 users + 1 blocked = 5 total
        self.assertIn("300", msg)
        self.assertIn("1", msg)   # 1 blocked user
        
        self.assertIn("پیروزی", msg)
        self.assertIn("ضربات گزارش", msg)
        self.assertIn("درصد موفقیت", msg)

if __name__ == "__main__":
    unittest.main()
