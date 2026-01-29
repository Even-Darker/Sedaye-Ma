import asyncio
import unittest
import time
import os
import sys
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["SUPER_ADMIN_IDS"] = "123456789"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "Vj75PKfqG2TvdP3mFmxH3qp7lowbaNweLzK3HYAucB8="

from src.database import init_db, AsyncSessionLocal
from src.database.models import Base, User
from src.utils.security import encrypt_id
from src.utils.middleware import ActivityTracker
from sqlalchemy import select, update as update_sqla

class TestActivityTracker(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Initialize in-memory database
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
            
        self.tracker = ActivityTracker()
        self.tracker._cache = {} # Clear singleton cache for fresh test
        self.tracker._last_prune = time.time()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_multi_user_isolation(self):
        """Verify that activities of User A do not affect User B."""
        USER_A = 101
        USER_B = 102
        
        async with AsyncSessionLocal() as session:
            session.add(User(encrypted_chat_id=encrypt_id(USER_A), last_seen=datetime(2000, 1, 1)))
            session.add(User(encrypted_chat_id=encrypt_id(USER_B), last_seen=datetime(2000, 1, 1)))
            await session.commit()
            
        update_a = AsyncMock()
        update_a.effective_user.id = USER_A
        update_b = AsyncMock()
        update_b.effective_user.id = USER_B
        context = AsyncMock()
        
        # Trigger User A
        await self.tracker(update_a, context)
        
        # Verify A is updated, B is NOT
        async with AsyncSessionLocal() as session:
            res_a = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(USER_A)))
            res_b = await session.execute(select(User).where(User.encrypted_chat_id == encrypt_id(USER_B)))
            self.assertGreater(res_a.scalar_one().last_seen.year, 2020)
            self.assertEqual(res_b.scalar_one().last_seen.year, 2000)

    async def test_24h_rule_and_cache(self):
        """Verify once-per-24h update rule and cache avoidance."""
        USER_ID = 201
        async with AsyncSessionLocal() as session:
            session.add(User(encrypted_chat_id=encrypt_id(USER_ID), last_seen=datetime(2000, 1, 1)))
            await session.commit()
            
        update_msg = AsyncMock()
        update_msg.effective_user.id = USER_ID
        context = AsyncMock()
        
        # 1. First interaction
        await self.tracker(update_msg, context)
        async with AsyncSessionLocal() as session:
            u = (await session.execute(select(User))).scalar_one()
            initial_last_seen = u.last_seen
            
        # 2. Interaction 1 hour later (Mocked cache entry)
        self.tracker._cache[USER_ID] = time.time() - 3600
        # Manually change DB to check if it's NOT overwritten
        async with AsyncSessionLocal() as session:
            await session.execute(update_sqla(User).values(last_seen=datetime(2021, 1, 1)))
            await session.commit()
            
        await self.tracker(update_msg, context)
        async with AsyncSessionLocal() as session:
            u = (await session.execute(select(User))).scalar_one()
            self.assertEqual(u.last_seen.year, 2021) # Should still be 2021 because cache skipped DB write

        # 3. Interaction 25 hours later
        self.tracker._cache[USER_ID] = time.time() - (25 * 3600)
        await self.tracker(update_msg, context)
        async with AsyncSessionLocal() as session:
            u = (await session.execute(select(User))).scalar_one()
            self.assertGreater(u.last_seen.year, 2024) # Should be updated to now

    async def test_prune_cache(self):
        """Verify memory management logic."""
        self.tracker._cache = {
            101: time.time() - 100,      # Fresh
            102: time.time() - 90000,    # Stale (>24h)
            103: time.time() - 50,       # Fresh
        }
        self.tracker._last_prune = time.time() - 4000 # Force prune (last prune was >1h ago)
        
        self.tracker.prune_cache()
        
        self.assertIn(101, self.tracker._cache)
        self.assertNotIn(102, self.tracker._cache)
        self.assertIn(103, self.tracker._cache)
        self.assertEqual(len(self.tracker._cache), 2)

    async def test_graceful_missing_user(self):
        """Verify that skipping non-existent users works without crashing."""
        update_msg = AsyncMock()
        update_msg.effective_user.id = 999999 # Non-existent ID
        context = AsyncMock()
        
        # Should not raise exception
        await self.tracker(update_msg, context)
        self.assertIn(999999, self.tracker._cache)

if __name__ == "__main__":
    unittest.main()
