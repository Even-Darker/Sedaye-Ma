"""
Sedaye Ma (صدای ما) - Voice of the People
Main Telegram Bot Entry Point

A privacy-first, open-source bot for amplifying the voice of Iranian people.
"""
import logging
import asyncio
import sys
import os

# Add parent directory to path to allow imports from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import BotCommand, Update, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, TypeHandler

from sqlalchemy import select

from config import settings
from src.database import init_db, Admin, get_db
from src.utils.security import decrypt_id
from src.utils.middleware import ActivityTracker
from src.handlers import (
    start_handler,
    start_callback_handler,
    menu_handlers,
    instagram_handlers,
    victories_handlers,
    free_configs_handlers,
    announcements_handlers,
    petitions_handlers,
    solidarity_handlers,
    resources_handlers,
    settings_handlers,
    admin_handlers,
    suggest_handlers,
    report_removal_conversation,
    text_menu_handler,
    email_campaign_handlers,
    admin_stats,
)


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",

    level=logging.INFO
)
# Suppress httpx logs (telegram polling)
logging.getLogger("httpx").setLevel(logging.WARNING)
# Force DEBUG for our code
logging.getLogger("src").setLevel(logging.DEBUG)

# Ensure environment is loaded (redundant safety)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database after bot starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully!")
    
    # Define command sets
    user_commands = [
        BotCommand("start", "شروع ربات"),
        BotCommand("help", "راهنما"),
    ]
    
    admin_commands = [
        BotCommand("start", "شروع ربات"),
        BotCommand("stat", "آمار (ادمین)"),
        BotCommand("help", "راهنما"),
    ]
    
    # 1. Reset/Clear wider scopes to ensure no "leaks" from previous sessions
    from telegram import BotCommandScopeAllPrivateChats
    await application.bot.delete_my_commands(scope=BotCommandScopeDefault())
    await application.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    
    # 2. Set default commands for everyone (normal users)
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault(), language_code="fa")
    
    # 3. Set custom commands for each admin
    async with get_db() as session:
        result = await session.execute(select(Admin.encrypted_telegram_id))
        admin_ids = result.scalars().all()
        
        for enc_id in admin_ids:
            try:
                chat_id = decrypt_id(enc_id)
                if chat_id:
                    await application.bot.set_my_commands(
                        admin_commands, 
                        scope=BotCommandScopeChat(chat_id=chat_id)
                    )
            except Exception as e:
                logger.error(f"Failed to set commands for admin {enc_id}: {e}")
                
    logger.info("Bot commands set successfully (Conditional Visibility)!")


def main():
    """Start the bot."""
    # Validate configuration
    if not settings.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set! Please configure .env file.")
        return
    
    logger.info("🔥 Starting Sedaye Ma Bot...")
    from src.version import __version__
    logger.info(f"Version: {__version__}")
    logger.info(f"Environment: {settings.environment}")
    
    # Build application
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .build()
    )
    
    # Register Activity Tracker (Middleware)
    application.add_handler(TypeHandler(Update, ActivityTracker()), group=-1)

    # Register handlers
    # Start command and main menu button
    from src.handlers.start import help_command_handler
    application.add_handler(start_handler)
    application.add_handler(help_command_handler)
    application.add_handler(start_callback_handler)    

    
    # Instagram targets
    for handler in instagram_handlers:
        application.add_handler(handler)
    
    # Victories
    for handler in victories_handlers:
        application.add_handler(handler)

    # Free Configs
    for handler in free_configs_handlers:
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
    
    # Register Admin Petitions Handlers
    from src.handlers.admin_petitions import manage_petitions, add_petition_conv, delete_petition_command
    application.add_handler(add_petition_conv)
    application.add_handler(CallbackQueryHandler(manage_petitions, pattern=r"^admin:petitions:page:\d+$"))
    application.add_handler(CallbackQueryHandler(manage_petitions, pattern=r"^admin:petitions$")) # Alias for first page
    application.add_handler(CallbackQueryHandler(manage_petitions, pattern=r"^admin:petitions$")) # Alias for first page
    application.add_handler(MessageHandler(filters.Regex(r"^/delete_petition_\d+$"), delete_petition_command))

    # Email Campaigns
    for handler in email_campaign_handlers:
        application.add_handler(handler)

    # Admin handlers (must be last to not interfere with conversations)
    application.add_handler(CommandHandler("stat", admin_stats))
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
