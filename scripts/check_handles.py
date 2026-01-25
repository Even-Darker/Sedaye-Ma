
import asyncio
import sys
import os
from sqlalchemy import select

# Add project root to path
sys.path.append(os.getcwd())

from src.database import get_db, InstagramTarget

async def check_handles():
    # Print DB path for debugging
    from config import settings
    print(f"DEBUG: Using database URL: {settings.database_url}")
    
    handles_to_check = [
        "amiir_khanlari11",
        "amirfrff26t3dfwya11",
        "sashah222"
    ]
    
    print(f"Checking for handles: {handles_to_check}")
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle.in_(handles_to_check))
        )
        found_targets = result.scalars().all()
        
        found_handles = {t.ig_handle for t in found_targets}
        
        print("\nResults:")
        for h in handles_to_check:
            if h in found_handles:
                print(f"✅ FOUND: {h}")
            else:
                print(f"❌ NOT FOUND: {h}")

if __name__ == "__main__":
    asyncio.run(check_handles())
