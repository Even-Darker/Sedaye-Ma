"""
Target suggestion handlers for Sedaye Ma bot.
Allows users to suggest new pages to report.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
from sqlalchemy import select

from config import Messages, settings
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, InstagramTarget, Admin
from src.database.models import TargetStatus


# Conversation states
SUGGEST_HANDLE = 1
SUGGEST_CONFIRM = 2
SUGGEST_REASONS = 3


async def is_user_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    if user_id in settings.super_admin_ids:
        return True
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == user_id)
        )
        return result.scalar_one_or_none() is not None


async def start_suggest_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the target suggestion flow."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_admin = await is_user_admin(user_id)
    
    if is_admin:
        message = (
            "➕ *افزودن صفحه جدید*\n\n"
            "لطفاً handle یا لینک پروفایل اینستاگرام را وارد کنید\\.\n"
            "می‌توانید نام کاربری \\(با یا بدون @\\) یا لینک مستقیم ارسال کنید:\n\n"
            "مثال:\n"
            "@username\n"
            "یا\n"
            "https://instagram\\.com/username\n\n"
            "همچنین برای ارسال چند صفحه می‌توانید آنها را در یک پیام ارسال کنید:\n"
            "مثال:\n"
            "@username1\n"
            "@username2\n"
            "https://instagram\\.com/username\n"
            "\\.\\.\\."
        )
    else:
        message = (
            "➕ *پیشنهاد صفحه جدید*\n\n"
            "شما می‌توانید صفحه‌ای را برای گزارش پیشنهاد دهید\\.\n"
            "پس از تأیید ادمین‌ها، صفحه به لیست اضافه خواهد شد\\.\n\n"
            "لطفاً handle یا لینک پروفایل اینستاگرام را وارد کنید \\(تکی یا لیست\\):\n\n"
            "مثال:\n"
            "@username\n"
            "یا\n"
            "https://instagram\\.com/username\n\n"
            "همچنین برای ارسال چند صفحه می‌توانید آنها را در یک پیام ارسال کنید:\n"
            "مثال:\n"
            "@username1\n"
            "@username2\n"
            "https://instagram\\.com/username\n"
            "\\.\\.\\."
        )
    
    await query.edit_message_text(
        message,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_sandisi()
    )
    
    return SUGGEST_HANDLE


async def receive_suggest_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the suggested handle(s) and validate."""
    from src.services.instagram import InstagramValidator, validate_instagram_handle
    from src.utils.parsers import HandleParser
    
    text = update.message.text
    user_id = update.effective_user.id
    
    # Store admin status for later
    is_admin = await is_user_admin(user_id)
    context.user_data["is_admin"] = is_admin
    
    # Show loading message
    loading_msg = await update.message.reply_text(
        "⏳ در حال پردازش\\.\\.\\.",
        parse_mode="MarkdownV2"
    )
    
    # Parse handles
    handles = HandleParser.extract_handles(text)
    
    if not handles:
        await loading_msg.edit_text(
            "⚠️ *هیچ نام کاربری معتبری یافت نشد*\n\n"
            "لطفاً مطمئن شوید که نام‌های کاربری را صحیح وارد کرده‌اید\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_sandisi()
        )
        return SUGGEST_HANDLE
        
    # Process Handles
    unique_handles = list(set(handles))
    
    # Check for duplicates in DB (bulk check optimization)
    # For simplicity, we check one by one or filter out existing
    async with get_db() as session:
        existing_result = await session.execute(
            select(InstagramTarget.ig_handle).where(InstagramTarget.ig_handle.in_(unique_handles))
        )
        existing_handles = [h.lower() for h in existing_result.scalars().all()]
        
    new_handles = [h for h in unique_handles if h not in existing_handles]
    
    if not new_handles:
        await loading_msg.edit_text(
            "⚠️ *همه موارد تکراری هستند*\n\n"
            "تمام صفحات وارد شده قبلاً در سیستم ثبت شده‌اند\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_sandisi()
        )
        return ConversationHandler.END

    # If single handle, validate logic similar to before (strict)
    if len(new_handles) == 1:
        handle = new_handles[0]
        
        # Validate format
        is_valid, format_error = InstagramValidator.validate_handle_format(handle)
        if not is_valid:
             await loading_msg.edit_text(
                f"⚠️ *فرمت handle نامعتبر است*\n\n"
                f"خطا: {Formatters.escape_markdown(format_error)}\n",
                parse_mode="MarkdownV2",
                 reply_markup=Keyboards.back_to_sandisi()
            )
             return SUGGEST_HANDLE

        # Validate on Instagram
        profile = await validate_instagram_handle(handle)
        if not profile.exists:
            await loading_msg.edit_text(
                f"❌ *صفحه پیدا نشد*\n\n"
                f"صفحه @{Formatters.escape_markdown(handle)} در اینستاگرام وجود ندارد\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_sandisi()
            )
            return SUGGEST_HANDLE
            
        context.user_data["suggest_handles"] = [handle]
        ig_link = f"https://instagram.com/{handle}"
        
        await loading_msg.edit_text(
            f"✅ *صفحه تایید شد*\n\n"
            f"📍 Handle: [@{Formatters.escape_markdown(handle)}]({ig_link})\n\n"
            "آیا این صفحه صحیح است؟",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.confirm_suggest_handle(),
            disable_web_page_preview=True
        )
        return SUGGEST_CONFIRM

    # Bulk Mode
    else:
        context.user_data["suggest_handles"] = new_handles
        
        preview = "\n".join([f"• [@{Formatters.escape_markdown(h)}](https://instagram.com/{h})" for h in new_handles[:10]])
        if len(new_handles) > 10:
            preview += f"\n\\.\\.\\. و {len(new_handles) - 10} مورد دیگر"
            
        await loading_msg.edit_text(
            f"✅ *{len(new_handles)} نام کاربری یافت شد*\n\n"
            f"{preview}\n\n"
            "آیا می‌خواهید این موارد را اضافه کنید؟",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.confirm_suggest_handle(), # Reuse confirm keyboard
            disable_web_page_preview=True
        )
        return SUGGEST_CONFIRM






async def confirm_handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation action (Yes/Edit)."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == CallbackData.SUGGEST_CONFIRM_EDIT:
        await query.edit_message_text(
            "✏️ *ویرایش نام کاربری*\n\n"
            "لطفاً handle \\(ها\\) صحیح را وارد کنید:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_sandisi()
        )
        return SUGGEST_HANDLE
        
    elif action == CallbackData.SUGGEST_CONFIRM_YES:
        handles = context.user_data.get("suggest_handles", [])
        
        # Format text based on count
        if len(handles) == 1:
            handle = handles[0]
            ig_link = f"https://instagram.com/{handle}"
            text = f"✅ *صفحه تأیید شد*\n\n📍 Handle: [@{Formatters.escape_markdown(handle)}]({ig_link})"
        else:
            text = f"✅ *{len(handles)} مورد تأیید شد*"
            
        await query.edit_message_text(
            f"{text}\n\n"
            "چرا باید گزارش شود؟\n"
            "لطفاً دلایل را تایپ کنید \\(اگر دلیل خاصی ندارید تایپ کنید ساندیس\\!\\):",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        return SUGGEST_REASONS


async def receive_suggest_reasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive reasons and save the target(s)."""
    from src.utils.validators import Validators
    
    reasons_text = update.message.text.strip()
    reasons_list = [r.strip().lower() for r in reasons_text.split(",")]
    
    handles = context.user_data.get("suggest_handles", [])
    is_admin = context.user_data.get("is_admin", False)
    
    if not handles:
        await update.message.reply_text(
            "⚠️ خطا: لطفاً دوباره شروع کنید\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_sandisi()
        )
        return ConversationHandler.END
    
    # Validate reasons
    is_valid, reasons, error = Validators.validate_report_reasons(reasons_list)
    if not is_valid:
        await update.message.reply_text(
            f"⚠️ {Formatters.escape_markdown(error or 'Invalid reasons')}\n\n"
            "لطفاً حداقل یک دلیل معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return SUGGEST_REASONS
    
    # Determine status based on admin level
    target_status = TargetStatus.ACTIVE if is_admin else TargetStatus.PENDING
    
    # Save all targets
    added_count = 0
    skipped_count = 0
    
    async with get_db() as session:
        for handle in handles:
            # Double-check duplicates (race condition protection)
            result = await session.execute(
                select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
            )
            if result.scalar_one_or_none():
                skipped_count += 1
                continue
                
            target = InstagramTarget(
                ig_handle=handle,
                report_reasons=reasons,
                priority=5,
                status=target_status
            )
            session.add(target)
            added_count += 1
            
        await session.commit()
    
    # Final message
    if added_count == 0 and skipped_count > 0:
        msg = f"⚠️ *همه موارد تکراری بودند*\n{skipped_count} مورد قبلاً ثبت شده بود\\."
    else:
        dup_text = f"\n_({skipped_count} تکراری نادیده گرفته شد)_" if skipped_count > 0 else ""
        if is_admin:
            msg = (
                f"✅ *{added_count} صفحه اضافه شد\\!*{dup_text}\n\n"
                f"📄 دلایل: {Formatters.escape_markdown(', '.join(reasons))}\n"
            )
        else:
             msg = (
                f"✅ *پیشنهاد {added_count} صفحه ثبت شد\\!*{dup_text}\n\n"
                f"📄 دلایل: {Formatters.escape_markdown(', '.join(reasons))}\n\n"
                f"_پس از تأیید ادمین‌ها، به لیست اضافه خواهند شد\\._"
            )
    
    await update.message.reply_text(
        msg,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_sandisi(),
        disable_web_page_preview=True
    )
    
    # Clear user data
    context.user_data.pop("suggest_handles", None)
    context.user_data.pop("is_admin", None)
    
    return ConversationHandler.END


async def cancel_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the suggestion flow."""
    import logging
    logger = logging.getLogger(__name__)
    
    query = update.callback_query
    await query.answer()
    context.user_data.pop("suggest_handles", None)
    context.user_data.pop("is_admin", None)
    
    try:
        await query.edit_message_text(
            Messages.REPORT_SANDISI_DESCRIPTION,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.report_sandisi_menu()
        )
    except Exception as e:
        logger.error(f"Error in cancel_suggest: {e}")
        # Fallback to plain text if markdown fails
        await query.edit_message_text(
            Messages.REPORT_SANDISI_DESCRIPTION.replace("*", "").replace("_", "").replace("\\", ""),
            reply_markup=Keyboards.report_sandisi_menu()
        )
        
    return ConversationHandler.END


# Conversation handler for target suggestions
suggest_target_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_suggest_target, pattern=f"^{CallbackData.SUGGEST_TARGET}$")
    ],
    states={
        SUGGEST_HANDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_suggest_handle),
        ],
        SUGGEST_CONFIRM: [
            CallbackQueryHandler(confirm_handle_action, pattern=f"^{CallbackData.SUGGEST_CONFIRM_YES}$"),
            CallbackQueryHandler(confirm_handle_action, pattern=f"^{CallbackData.SUGGEST_CONFIRM_EDIT}$"),
        ],
        SUGGEST_REASONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_suggest_reasons),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_suggest, pattern=f"^{CallbackData.BACK_SANDISI}$"),
    ],
    per_message=False,
)


# Export handlers
suggest_handlers = [
    suggest_target_conversation,
]

