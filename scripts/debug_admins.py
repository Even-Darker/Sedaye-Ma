
import asyncio
import logging
import os
from dotenv import load_dotenv
from sqlalchemy import select

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_admin_notifications():
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # Must setup DB modules
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from src.database import get_db, Admin
    from telegram.ext import Application
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    # For debug, hardcode if env fails again, but try env first
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment!")
        return

    # FORCE ABSOLUTE DB PATH
    # import os # Already imported globally
    db_path = Path(__file__).parent.parent / "data" / "sedaye_ma.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    logger.info(f"Using DB Path: {os.environ['DATABASE_URL']}")

    logger.info("--- Checking Database for Admins ---")
    async with get_db() as session:
        result = await session.execute(select(Admin))
        admins = result.scalars().all()
        
        if not admins:
            logger.error("NO ADMINS FOUND IN DATABASE!")
        else:
            for admin in admins:
                logger.info(f"Found Admin: ID={admin.telegram_id}, Role={admin.role}")

    logger.info("--- Testing Notification ---")
    app = Application.builder().token(token).build()
    await app.bot.initialize()
    
    target_id = 1233202831 # The user's ID from logs
    
    try:
        await app.bot.send_message(chat_id=target_id, text="🔔 TEST NOTIFICATION: If you see this, the bot CAN message you.")
        logger.info(f"Successfully sent message to {target_id}")
    except Exception as e:
        logger.error(f"Failed to send to {target_id}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_admin_notifications())
