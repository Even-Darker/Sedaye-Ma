"""
Sedaye Ma (صدای ما) - Voice of the People
Main Telegram Bot Entry Point

A privacy-first, open-source bot for amplifying the voice of Iranian people.
"""
import logging
import asyncio
from telegram import BotCommand
from telegram.ext import Application

from config import settings
from src.database import init_db
from src.handlers import (
    start_handler,
    start_callback_handler,
    menu_handlers,
    instagram_handlers,
    victories_handlers,
    announcements_handlers,
    petitions_handlers,
    solidarity_handlers,
    resources_handlers,
    settings_handlers,
    admin_handlers,
    suggest_handlers,
    report_removal_conversation,
    text_menu_handler,
)


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully!")
    
    # Set bot commands
    commands = [
        BotCommand("start", "شروع ربات"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully!")


def main():
    """Start the bot."""
    # Validate configuration
    if not settings.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set! Please configure .env file.")
        return
    
    logger.info("🔥 Starting Sedaye Ma Bot...")
    logger.info(f"Environment: {settings.environment}")
    
    # Build application
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .build()
    )
    
    # Register handlers
    # Start command and main menu button
    application.add_handler(start_handler)
    application.add_handler(start_callback_handler)    

    
    # Instagram targets
    for handler in instagram_handlers:
        application.add_handler(handler)
    
    # Victories
    for handler in victories_handlers:
        application.add_handler(handler)
    
    # Announcements
    for handler in announcements_handlers:
        application.add_handler(handler)
    
    # Petitions
    for handler in petitions_handlers:
        application.add_handler(handler)
    
    # Solidarity (conversation handler should be added)
    for handler in solidarity_handlers:
        application.add_handler(handler)
    
    # Resources
    for handler in resources_handlers:
        application.add_handler(handler)
    
    # Settings
    for handler in settings_handlers:
        application.add_handler(handler)
    

    
    # User removal reports (victories)
    application.add_handler(report_removal_conversation)
    
    # User suggestions 
    for handler in suggest_handlers:
        application.add_handler(handler)
    
    # Admin handlers (must be last to not interfere with conversations)
    for handler in admin_handlers:
        application.add_handler(handler)
        
    # Menu navigation (Generic back buttons - must be after conversations)
    for handler in menu_handlers:
        application.add_handler(handler)

    # Text menu handler (must be last to not catch commands or conversation states)
    application.add_handler(text_menu_handler)
    
    logger.info("✅ All handlers registered!")
    logger.info("🚀 Bot is running... Press Ctrl+C to stop.")
    
    # Run the bot
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
