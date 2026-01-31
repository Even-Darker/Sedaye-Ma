"""
Settings handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from sqlalchemy import select



from config import Messages
from src.utils import Keyboards
from src.utils.keyboards import CallbackData
from src.database import get_db, User
from src.utils.security import encrypt_id

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    query = update.callback_query
    if query:
        await query.answer()
    
    chat_id = update.effective_chat.id
    enc_id = encrypt_id(chat_id)
    
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.encrypted_chat_id == enc_id)
        )
        user = result.scalar_one_or_none()
        
        # Create default user if not exists
        if not user:
            user = User(
                encrypted_chat_id=enc_id,
                # Default prefs
                announcements_urgent=True,
                announcements_news=True,
                victories=True,
                targets=True,
                petitions=False
            )
            session.add(user)
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
                reply_markup=Keyboards.notification_settings(user)
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.notification_settings(user)
            )
        
        return ConversationHandler.END


async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a notification setting."""
    query = update.callback_query
    
    notif_type = query.data.split(":")[-1]
    chat_id = update.effective_chat.id
    enc_id = encrypt_id(chat_id)
    
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.encrypted_chat_id == enc_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Should exist if they are toggleing, but safe fallback
            user = User(
                encrypted_chat_id=enc_id
            )
            session.add(user)
        
        # Toggle the appropriate setting
        if notif_type == "urgent":
            user.announcements_urgent = not user.announcements_urgent
        elif notif_type == "news":
            user.announcements_news = not user.announcements_news
        elif notif_type == "victories":
            user.victories = not user.victories
        elif notif_type == "targets":
            user.targets = not user.targets
        elif notif_type == "petitions":
            user.petitions = not user.petitions
        elif notif_type == "emails":
            user.email_campaigns = not user.email_campaigns
        
        await session.commit()
        
        await query.answer("✓ تنظیمات ذخیره شد")
        
        await query.edit_message_reply_markup(
            reply_markup=Keyboards.notification_settings(user)
        )


# Export handlers
settings_handlers = [
    CallbackQueryHandler(show_settings, pattern=f"^{CallbackData.MENU_SETTINGS}$"),
    CallbackQueryHandler(toggle_notification, pattern=r"^notif:toggle:\w+$"),
]
