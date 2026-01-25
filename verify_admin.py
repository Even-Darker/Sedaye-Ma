import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Mock env vars BEFORE importing settings
os.environ['SUPER_ADMIN_IDS'] = '123456789'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'

from config import settings
from src.utils.decorators import admin_required

async def test_admin_access():
    print(f"Loaded SUPER_ADMIN_IDS: {settings.super_admin_ids}")
    
    # Mock update
    update = MagicMock()
    update.effective_user.id = 123456789
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    
    context = MagicMock()
    
    # Mock handler
    @admin_required
    async def restricted_handler(u, c):
        print("✅ Handler executed!")
        return True
        
    print(f"Testing access for user {update.effective_user.id}...")
    result = await restricted_handler(update, context)
    
    if result:
        print("ACCESS GRANTED")
    else:
        print("ACCESS DENIED (Check decorator logic)")

if __name__ == "__main__":
    asyncio.run(test_admin_access())
