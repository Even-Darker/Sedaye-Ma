"""
Removal reporting handlers for Sedaye Ma bot.
Allows users to report successful removal of target pages.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
from sqlalchemy import select
from datetime import datetime

from config import Messages, settings
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, InstagramTarget, Victory, Admin
from src.database.models import TargetStatus

# Conversation states
REPORT_HANDLE = 1
CONFIRM_REMOVAL = 2


async def start_report_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the removal reporting flow."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"{Messages.REMOVE_REPORT_HEADER}\n\n{Messages.REMOVE_REPORT_HANDLE_PROMPT}",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_sandisi()
    )
    
    return REPORT_HANDLE


async def receive_removal_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive handle for removal verification."""
    from src.services.instagram import InstagramValidator, validate_instagram_handle
    
    handle = update.message.text.strip().replace("@", "").lower()
    
    # Show loading message
    loading_msg = await update.message.reply_text(
        Messages.REMOVE_REPORT_VERIFYING,
        parse_mode="MarkdownV2"
    )
    
    # Validate format first
    is_valid, _ = InstagramValidator.validate_handle_format(handle)
    if not is_valid:
        await loading_msg.edit_text(
            "⚠️ *فرمت نامعتبر*\nلطفاً یک handle معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return REPORT_HANDLE
    
    # Check if target exists in DB
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await loading_msg.edit_text(
                "⚠️ *صفحه یافت نشد*\n"
                "این صفحه در لیست اهداف ما وجود ندارد\\. لطفاً مطمئن شوید که قبلاً ثبت شده است\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_sandisi()
            )
            return ConversationHandler.END
            
        if target.status == TargetStatus.REMOVED:
            await loading_msg.edit_text(
                "✅ *قبلاً ثبت شده*\n"
                "حذف این صفحه قبلاً ثبت و جشن گرفته شده است\\! 🎉",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_sandisi()
            )
            return ConversationHandler.END
            
    # Check Instagram status
    profile = await validate_instagram_handle(handle)
    context.user_data["removal_target_id"] = target.id
    context.user_data["removal_handle"] = handle
    
    if not profile.exists:
        # Page is gone! Good sign.
        await loading_msg.edit_text(
            Messages.REMOVE_REPORT_NOT_FOUND,
            parse_mode="MarkdownV2"
        )
        # Auto-submit to admins
        await submit_removal_request(context, target.id, handle, auto_confirmed=True)
        return ConversationHandler.END
    else:
        # Page still exists
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.REMOVE_REPORT_BTN_YES, callback_data=CallbackData.REMOVAL_CONFIRM_YES)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_SANDISI)]
        ])
        
        await loading_msg.edit_text(
            Messages.REMOVE_REPORT_EXISTS,
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )
        return CONFIRM_REMOVAL


async def confirm_manual_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle manual confirmation of removal."""
    query = update.callback_query
    await query.answer()
    
    if query.data == CallbackData.REMOVAL_CONFIRM_YES:
        target_id = context.user_data.get("removal_target_id")
        handle = context.user_data.get("removal_handle")
        
        await submit_removal_request(context, target_id, handle, auto_confirmed=False)
        
        await query.edit_message_text(
            Messages.REMOVE_REPORT_SUBMITTED,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_sandisi()
        )
        return ConversationHandler.END
    
    return ConversationHandler.END


async def submit_removal_request(context: ContextTypes.DEFAULT_TYPE, target_id: int, handle: str, auto_confirmed: bool):
    """Submit removal request to admins."""
    # Notify all admins
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید حذف و ثبت پیروزی", callback_data=CallbackData.ADMIN_CONFIRM_REMOVAL.format(id=target_id))],
        [InlineKeyboardButton("بررسی صفحه", url=f"https://instagram.com/{handle}")]
    ])
    
    status_icon = "🟢" if auto_confirmed else "⚠️"
    status_text = "تایید خودکار (صفحه یافت نشد)" if auto_confirmed else "گزارش دستی (صفحه هنوز دیده می‌شود)"
    
    msg = (
        f"🏆 *گزارش حذف صفحه*\n\n"
        f"📍 Handle: @{Formatters.escape_markdown(handle)}\n"
        f"وضعیت ربات: {status_text} {status_icon}\n\n"
        "آیا حذف این صفحه را تأیید می‌کنید؟"
    )
    
    # Fetch admins from config/DB and notify
    # For now sending to super admins for simplicity, can expand to all admins
    for admin_id in settings.super_admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="MarkdownV2",
                reply_markup=admin_keyboard
            )
        except Exception:
            pass
            

async def cancel_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel flow."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        Messages.REPORT_SANDISI_DESCRIPTION,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.report_sandisi_menu()
    )
    return ConversationHandler.END


# Conversation Handler
report_removal_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_report_removal, pattern=f"^{CallbackData.SUGGEST_REMOVAL}$")
    ],
    states={
        REPORT_HANDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_removal_handle)
        ],
        CONFIRM_REMOVAL: [
            CallbackQueryHandler(confirm_manual_removal, pattern=f"^{CallbackData.REMOVAL_CONFIRM_YES}$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_removal, pattern=f"^{CallbackData.BACK_SANDISI}$")
    ],
    per_message=False
)
