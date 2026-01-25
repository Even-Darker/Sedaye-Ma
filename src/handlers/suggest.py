"""
Target suggestion handlers for Sedaye Ma bot.
Allows users to suggest new pages to report.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
SUGGEST_CONFIRM_HANDLE = 2
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
            "لطفاً handle اینستاگرام را وارد کنید \\(بدون @\\):"
        )
    else:
        message = (
            "➕ *پیشنهاد صفحه جدید*\n\n"
            "شما می‌توانید صفحه‌ای را برای گزارش پیشنهاد دهید\\.\n"
            "پس از تأیید ادمین‌ها، صفحه به لیست اضافه خواهد شد\\.\n\n"
            "لطفاً handle اینستاگرام را وارد کنید \\(بدون @\\):"
        )
    
    await query.edit_message_text(
        message,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )
    
    return SUGGEST_HANDLE


async def receive_suggest_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the suggested handle and validate it."""
    from src.services.instagram import InstagramValidator, validate_instagram_handle
    
    handle = update.message.text.strip().replace("@", "").lower()
    user_id = update.effective_user.id
    
    # Store admin status for later
    is_admin = await is_user_admin(user_id)
    context.user_data["is_admin"] = is_admin
    
    # Show loading message
    loading_msg = await update.message.reply_text(
        "⏳ در حال بررسی صفحه اینستاگرام\\.\\.\\.",
        parse_mode="MarkdownV2"
    )
    
    # Validate format first
    is_valid, format_error = InstagramValidator.validate_handle_format(handle)
    if not is_valid:
        await loading_msg.edit_text(
            f"⚠️ *فرمت handle نامعتبر است*\n\n"
            f"خطا: {Formatters.escape_markdown(format_error)}\n\n"
            "لطفاً یک handle معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return SUGGEST_HANDLE
    
    # Check if already in database (any status)
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
        )
        existing = result.scalar_one_or_none()
        if existing:
            status_text = {
                TargetStatus.ACTIVE: "قبلاً در لیست وجود دارد",
                TargetStatus.PENDING: "قبلاً پیشنهاد شده و در انتظار تأیید است",
                TargetStatus.REMOVED: "قبلاً گزارش شده و حذف شده است",
                TargetStatus.REPORTED: "قبلاً در لیست وجود دارد",
            }
            await loading_msg.edit_text(
                f"⚠️ صفحه @{Formatters.escape_markdown(handle)} {status_text.get(existing.status, 'موجود است')}\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
    
    # Validate on Instagram
    profile = await validate_instagram_handle(handle)
    
    context.user_data["suggest_handle"] = handle
    
    if not profile.exists:
        # CASE: BAD (Explicitly Not Found)
        error_detail = ""
        if profile.error:
            error_detail = f"\n_{Formatters.escape_markdown(profile.error)}_"
        await loading_msg.edit_text(
            f"❌ *صفحه پیدا نشد*\n\n"
            f"صفحه @{Formatters.escape_markdown(handle)} در اینستاگرام وجود ندارد\\.{error_detail}\n\n"
            "لطفاً یک handle معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return SUGGEST_HANDLE
    
    # CASE: UNKNOWN (Login Wall / Generic 200) -> Ask User Confirmation
    if not profile.verified:
        ig_link = f"https://instagram.com/{handle}"
        # FIX: Escape the link text (URL) to be safe in Markdown
        escaped_link = Formatters.escape_markdown(ig_link)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله، صفحه موجود است", callback_data="confirm_existing")],
            [InlineKeyboardButton("❌ خیر، تصحیح می‌کنم", callback_data="confirm_retry")],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])
        
        await loading_msg.edit_text(
            f"⚠️ *نیاز به تأیید دستی*\n\n"
            f"بات نتوانست به طور خودکار وجود صفحه @{Formatters.escape_markdown(handle)} را تأیید کند "
            f"\\(محدودیت اینستاگرام\\)\\.\n\n"
            f"لطفاً لینک زیر را چک کنید؛ اگر صفحه باز می‌شود دکمه «بله» را بزنید:\n"
            f"🔗 [{escaped_link}]({ig_link})",
            parse_mode="MarkdownV2",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return SUGGEST_CONFIRM_HANDLE
    
    # CASE: GOOD (Verified Exists) -> Auto-Proceed
    return await ask_reasons(loading_msg, handle)


async def confirm_handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation of inconclusive handle."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "confirm_retry":
        await query.edit_message_text(
            "لطفاً handle صحیح را وارد کنید:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
        )
        return SUGGEST_HANDLE
    
    # Confirmed
    handle = context.user_data.get("suggest_handle")
    # Edit the message to show next step
    return await ask_reasons(query, handle)


async def ask_reasons(messageable, handle):
    """Show the ask reasons message."""
    ig_link = f"https://instagram.com/{handle}"
    text = (
        f"✅ *صفحه تأیید شد*\n\n"
        f"📍 Handle: [@{Formatters.escape_markdown(handle)}]({ig_link})\n\n"
        "چرا این صفحه باید گزارش شود؟\n"
        "لطفاً دلایل را وارد کنید \\(با کاما جدا کنید\\):\n\n"
        "`violence, misinformation, propaganda, human_rights, harassment`"
    )
    
    # Helper to edit message whether it's an Update (callback) or Message
    if hasattr(messageable, "edit_message_text"): # CallbackQuery
        await messageable.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=None, 
            disable_web_page_preview=True
        )
    else: # Message
        await messageable.edit_text(
            text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
    
    return SUGGEST_REASONS


async def receive_suggest_reasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive reasons and save the target."""
    from src.utils.validators import Validators
    
    reasons_text = update.message.text.strip()
    reasons_list = [r.strip().lower() for r in reasons_text.split(",")]
    handle = context.user_data.get("suggest_handle")
    is_admin = context.user_data.get("is_admin", False)
    
    if not handle:
        await update.message.reply_text(
            "⚠️ خطا: لطفاً دوباره شروع کنید\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
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
    # Even if unknown/confirmed manually, we respect admin status
    target_status = TargetStatus.ACTIVE if is_admin else TargetStatus.PENDING
    
    # Save target
    async with get_db() as session:
        # Double-check for duplicates
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
        )
        if result.scalar_one_or_none():
            await update.message.reply_text(
                f"⚠️ این صفحه قبلاً ثبت شده است\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
        
        target = InstagramTarget(
            ig_handle=handle,
            report_reasons=reasons,
            priority=5,
            status=target_status
        )
        session.add(target)
        await session.commit()
    
    ig_link = f"https://instagram.com/{handle}"
    
    if is_admin:
        # Admin message - added directly
        await update.message.reply_text(
            f"✅ *صفحه اضافه شد\\!*\n\n"
            f"📍 Handle: [@{Formatters.escape_markdown(handle)}]({ig_link})\n"
            f"📋 دلایل: {Formatters.escape_markdown(', '.join(reasons))}",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main(),
            disable_web_page_preview=True
        )
    else:
        # Regular user message - pending approval
        await update.message.reply_text(
            f"✅ *پیشنهاد شما ثبت شد\\!*\n\n"
            f"📍 Handle: [@{Formatters.escape_markdown(handle)}]({ig_link})\n"
            f"📋 دلایل: {Formatters.escape_markdown(', '.join(reasons))}\n\n"
            f"_پس از تأیید ادمین‌ها، صفحه به لیست اضافه خواهد شد\\._",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main(),
            disable_web_page_preview=True
        )
    
    # Clear user data
    context.user_data.pop("suggest_handle", None)
    context.user_data.pop("is_admin", None)
    
    return ConversationHandler.END


async def cancel_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the suggestion flow."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("suggest_handle", None)
    context.user_data.pop("is_admin", None)
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
        SUGGEST_CONFIRM_HANDLE: [
            CallbackQueryHandler(confirm_handle_callback),
        ],
        SUGGEST_REASONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_suggest_reasons),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_suggest, pattern=f"^{CallbackData.BACK_MAIN}$"),
    ],
    per_message=False,
)


# Export handlers
suggest_handlers = [
    suggest_target_conversation,
]
