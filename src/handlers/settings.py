"""
Settings handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages
from src.utils import Keyboards
from src.utils.keyboards import CallbackData
from src.database import get_db, NotificationPreference


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    query = update.callback_query
    if query:
        await query.answer()
    
    chat_id = update.effective_chat.id
    
    async with get_db() as session:
        result = await session.execute(
            select(NotificationPreference).where(NotificationPreference.chat_id == chat_id)
        )
        prefs = result.scalar_one_or_none()
        
        # Create default preferences if not exists
        if not prefs:
            prefs = NotificationPreference(
                chat_id=chat_id,
                announcements_urgent=True,
                announcements_news=True,
                victories=True,
                petitions=False
            )
            session.add(prefs)
            await session.commit()
        
        message = f"""
{Messages.SETTINGS_HEADER}

{Messages.NOTIFICATIONS_HEADER}

{Messages.SETTINGS_TIP}
"""
        
        if query:
            await query.edit_message_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.notification_settings(prefs)
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.notification_settings(prefs)
            )


async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a notification setting."""
    query = update.callback_query
    
    notif_type = query.data.split(":")[-1]
    chat_id = update.effective_chat.id
    
    async with get_db() as session:
        result = await session.execute(
            select(NotificationPreference).where(NotificationPreference.chat_id == chat_id)
        )
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            prefs = NotificationPreference(chat_id=chat_id)
            session.add(prefs)
        
        # Toggle the appropriate setting
        if notif_type == "urgent":
            prefs.announcements_urgent = not prefs.announcements_urgent
        elif notif_type == "news":
            prefs.announcements_news = not prefs.announcements_news
        elif notif_type == "victories":
            prefs.victories = not prefs.victories
        elif notif_type == "petitions":
            prefs.petitions = not prefs.petitions
        elif notif_type == "emails":
            prefs.email_campaigns = not prefs.email_campaigns
        
        await session.commit()
        
        await query.answer("✓ تنظیمات ذخیره شد")
        
        await query.edit_message_reply_markup(
            reply_markup=Keyboards.notification_settings(prefs)
        )


# Export handlers
settings_handlers = [
    CallbackQueryHandler(show_settings, pattern=f"^{CallbackData.MENU_SETTINGS}$"),
    CallbackQueryHandler(toggle_notification, pattern=r"^notif:toggle:\w+$"),
]
