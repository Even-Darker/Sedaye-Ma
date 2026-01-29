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
    
    # RATE LIMIT CHECK (24 Hours)
    # ---------------------------------------------------------
    # RATE LIMIT CHECK (24 Hours)
    # ---------------------------------------------------------
    user_id = update.effective_user.id
    from src.database.models import UserVictoryLog, User
    from src.database.models import UserVictoryLog, User
    from src.utils.security import encrypt_id
    from datetime import datetime, timedelta
    
    enc_id = encrypt_id(user_id)
    
    async with get_db() as session:
        # Get Encrypted ID
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        user_obj = res_user.scalar_one_or_none()
        
        # Check last submission
        log_result = await session.execute(
            select(UserVictoryLog)
            .where(
                UserVictoryLog.target_id == target.id,
                UserVictoryLog.encrypted_user_id == enc_id
            )
            .order_by(UserVictoryLog.created_at.desc())
            .limit(1)
        )
        last_log = log_result.scalar_one_or_none()
        
        if last_log:
            # Check if within 24 hours
            if datetime.utcnow() - last_log.created_at < timedelta(hours=24):
                await loading_msg.edit_text(
                    "⚠️ *قبلاً گزارش شده است*\n\n"
                    "شما قبلاً حذف شدن این صفحه را گزارش داده‌اید\\.\n"
                    "برای جلوگیری از اسپم، هر کاربر فقط هر ۲۴ ساعت یکبار می‌تواند برای یک صفحه گزارش موفقیت ارسال کند\\.\n\n"
                    "لطفا فردا تلاش کنید 🙏",
                    parse_mode="MarkdownV2",
                    reply_markup=Keyboards.back_to_sandisi()
                )
                return ConversationHandler.END

    if not profile.exists:
        # Page is gone! Good sign.
        await loading_msg.edit_text(
            Messages.REMOVE_REPORT_NOT_FOUND,
            parse_mode="MarkdownV2"
        )
        # Log this submission
        async with get_db() as session:
            new_log = UserVictoryLog(target_id=target.id, encrypted_user_id=enc_id)
            session.add(new_log)
            await session.commit()
            
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
        user_id = update.effective_user.id
        
        # Log this submission (Manual confirmation)
        from src.database.models import UserVictoryLog, User
        from src.utils.security import encrypt_id
        
        enc_id = encrypt_id(user_id)
        
        async with get_db() as session:
            res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
            user_obj = res_user.scalar_one_or_none()
            
            new_log = UserVictoryLog(target_id=target_id, encrypted_user_id=enc_id)
            session.add(new_log)
            await session.commit()
        
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
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"submit_removal_request called for target {target_id}, handle {handle}")
    
    from src.services.notification_service import NotificationService
    
    service = NotificationService(context.bot)
    await service.notify_admins_removal_request(target_id, handle, auto_confirmed)
            

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
