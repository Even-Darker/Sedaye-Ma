"""
Start command handler for Sedaye Ma bot.
Handles /start command and initial onboarding.
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy import select

from config import Messages, settings
from src.utils import Keyboards
from src.database import get_db, Admin


async def is_user_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    if user_id in settings.super_admin_ids:
        return True
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == user_id)
        )
        return result.scalar_one_or_none() is not None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show welcome message."""
    user_id = update.effective_user.id
    is_admin = await is_user_admin(user_id)
    
    await update.message.reply_text(
        Messages.WELCOME,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.main_menu_persistent(is_admin=is_admin)
    )





async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start button click - show main menu."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_admin = await is_user_admin(user_id)
    
    await query.edit_message_text(
        Messages.MAIN_MENU_HEADER,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.main_menu(is_admin=is_admin)
    )


# Export handlers
start_handler = CommandHandler("start", start_command)

start_callback_handler = CallbackQueryHandler(start_callback, pattern="^start$")

