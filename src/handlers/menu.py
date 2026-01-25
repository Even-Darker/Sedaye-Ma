"""
Menu navigation handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages, settings
from src.utils import Keyboards
from src.utils.keyboards import CallbackData
from src.database import get_db, Admin
# Import from instagram to reuse filter menu display logic
from src.handlers.instagram import show_filter_menu


async def is_user_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    if user_id in settings.super_admin_ids:
        return True
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == user_id)
        )
        return result.scalar_one_or_none() is not None


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to main menu."""
    query = update.callback_query
    
    # Check if user is admin to show admin button
    user_id = update.effective_user.id
    admin_access = await is_user_admin(user_id)
    
    await query.answer()
    
    # Instead of deleting, we edit correctly to show main menu options (inline)
    # The main menu is usually persistent reply keyboard, but for inline navigation we show the inline version.
    await query.edit_message_text(
        Messages.MAIN_MENU_HEADER,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.main_menu(is_admin=admin_access)
    )


async def back_to_report_sandisi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to Report Sandisi menu."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        Messages.REPORT_SANDISI_DESCRIPTION,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.report_sandisi_menu()
    )


# Export handlers
menu_handlers = [
    CallbackQueryHandler(back_to_main, pattern=f"^{CallbackData.BACK_MAIN}$"),
    CallbackQueryHandler(back_to_report_sandisi, pattern=f"^{CallbackData.BACK_SANDISI}$"),
    CallbackQueryHandler(show_filter_menu, pattern=f"^{CallbackData.BACK_FILTER}$"),
]
