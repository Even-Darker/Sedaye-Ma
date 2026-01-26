"""
Admin handlers for Sedaye Ma bot.
Protected commands for managing the bot.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
import re
import logging
from sqlalchemy import select

logger = logging.getLogger(__name__)
from datetime import datetime

from config import Messages, settings
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.utils.decorators import admin_required, super_admin_required
from src.database import get_db, Admin, InstagramTarget, Victory, Announcement, SolidarityMessage
from src.database.models import TargetStatus, AdminRole


# Conversation states
ADDING_TARGET_HANDLE = 1
ADDING_TARGET_REASONS = 2
ADDING_ANNOUNCEMENT_TITLE = 3
ADDING_ANNOUNCEMENT_CONTENT = 4
ADDING_ADMIN_ID = 5


async def is_super_admin(user_id: int) -> bool:
    """Check if user is a super admin (Database only)."""
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(
                Admin.telegram_id == user_id,
                Admin.role == AdminRole.SUPER_ADMIN
            )
        )
        return result.scalar_one_or_none() is not None


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    from sqlalchemy import func
    import logging
    logger = logging.getLogger(__name__)

    user_id = update.effective_user.id
    super_admin = await is_super_admin(user_id)
    
    pending_count = 0
    try:
        # Get pending targets count
        async with get_db() as session:
            result = await session.execute(
                select(func.count(InstagramTarget.id)).where(
                    InstagramTarget.status == TargetStatus.PENDING
                )
            )
            pending_count = result.scalar() or 0
    except Exception as e:
        logger.error(f"Error fetching pending count: {e}")
        # Continue without count
        
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                Messages.ADMIN_HEADER,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.admin_menu(is_super_admin=super_admin, pending_count=pending_count)
            )
        else:
            await update.message.reply_text(
                Messages.ADMIN_HEADER,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.admin_menu(is_super_admin=super_admin, pending_count=pending_count)
            )
    except Exception as e:
        logger.error(f"Error showing admin panel: {e}")
        # Fallback
        if update.callback_query:
            await update.callback_query.answer("⚠️ خطا در باز کردن پنل", show_alert=True)
        else:
            await update.message.reply_text("⚠️ خطا در پردازش درخواست")


@admin_required
async def start_add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new target."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ *افزودن صفحه جدید*\n\n"
        "لطفاً handle اینستاگرام را وارد کنید \\(تکی یا لیست\\):\n\n"
        "مثال:\n"
        "@user\\_1\n"
        "@user\\_2\n"
        "\\.\\.\\.",
        parse_mode="MarkdownV2"
    )
    
    return ADDING_TARGET_HANDLE


async def receive_target_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive target handle(s) and validate."""
    from src.services.instagram import InstagramValidator, validate_instagram_handle
    from src.utils.parsers import HandleParser
    
    text = update.message.text
    user_id = update.effective_user.id
    
    # Show loading message
    loading_msg = await update.message.reply_text(
        "⏳ در حال پردازش\\.\\.\\.",
        parse_mode="MarkdownV2"
    )
    
    # Parse handles
    handles = HandleParser.extract_handles(text)
    
    if not handles:
        await loading_msg.edit_text(
            f"⚠️ *فرمت نامعتبر است*\n\n"
            "لطفاً یک handle معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return ADDING_TARGET_HANDLE
    
    # Process Handles
    unique_handles = list(set(handles))
    
    # Check for duplicates in DB
    async with get_db() as session:
        existing_result = await session.execute(
            select(InstagramTarget.ig_handle).where(InstagramTarget.ig_handle.in_(unique_handles))
        )
        existing_handles = [h.lower() for h in existing_result.scalars().all()]
        
    new_handles = [h for h in unique_handles if h not in existing_handles]
    
    if not new_handles:
        await loading_msg.edit_text(
            f"⚠️ همه {len(unique_handles)} مورد قبلاً در لیست وجود دارند\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
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
                parse_mode="MarkdownV2"
            )
             return ADDING_TARGET_HANDLE

        # Validate on Instagram
        profile = await validate_instagram_handle(handle)
        if not profile.exists:
            await loading_msg.edit_text(
                f"❌ *صفحه پیدا نشد*\n\n"
                f"صفحه @{Formatters.escape_markdown(handle)} در اینستاگرام وجود ندارد\\.",
                parse_mode="MarkdownV2"
            )
            return ADDING_TARGET_HANDLE
            
        context.user_data["new_target_handles"] = [handle]
        
        await loading_msg.edit_text(
            f"✅ *صفحه تأیید شد*\n\n"
            f"📍 Handle: @{Formatters.escape_markdown(handle)}\n\n"
            "حالا دلایل گزارش را وارد کنید \\(اگر دلیل خاصی ندارید بزنید ساندیس\\!\\):",
            parse_mode="MarkdownV2"
        )
        return ADDING_TARGET_REASONS

    # Bulk Mode
    else:
        context.user_data["new_target_handles"] = new_handles
        
        preview = "\n".join([f"• [@{Formatters.escape_markdown(h)}](https://instagram.com/{h})" for h in new_handles[:10]])
        if len(new_handles) > 10:
            preview += f"\n\\.\\.\\. و {len(new_handles) - 10} مورد دیگر"
        
        await loading_msg.edit_text(
            f"✅ *{len(new_handles)} نام کاربری یافت شد*\n\n"
            f"{preview}\n\n"
            f"آیا مطمئن هستید؟\n\n"
            "حالا دلایل گزارش را برای **همه این موارد** تاسپ کنید \\(اگر دلیل خاصی ندارید تایپ کنید ساندیس\\!\\):",
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        return ADDING_TARGET_REASONS


async def receive_target_reasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive target reasons and save."""
    from src.utils.validators import Validators
    
    reasons_text = update.message.text.strip()
    reasons_list = [r.strip().lower() for r in reasons_text.split(",")]
    
    handles = context.user_data.get("new_target_handles", [])
    user_id = update.effective_user.id
    
    if not handles:
        await update.message.reply_text(
            "⚠️ خطا: لطفاً دوباره شروع کنید\\.",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
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
        return ADDING_TARGET_REASONS
    
    added_count = 0
    skipped_count = 0
    
    async with get_db() as session:
        for handle in handles:
            # Double-check for duplicates
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
                status=TargetStatus.ACTIVE
            )
            session.add(target)
            added_count += 1
            
        await session.commit()
    
    # Build result message
    if added_count == 0 and skipped_count > 0:
        msg = f"⚠️ *همه {skipped_count} مورد قبلاً اضافه شده بودند*\\."
    else:
        dup_text = f"\n_({skipped_count} تکراری نادیده گرفته شد)_" if skipped_count > 0 else ""
        msg = (
            f"✅ *{added_count} صفحه اضافه شد\\!*{dup_text}\n\n"
            f"📄 دلایل: {Formatters.escape_markdown(', '.join(reasons))}\n"
        )
        
    await update.message.reply_text(
        msg,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
    )
    
    # Clear data
    context.user_data.pop("new_target_handles", None)
    
    return ConversationHandler.END



@admin_required
async def manage_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show targets for management."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget)
            .where(InstagramTarget.status == TargetStatus.ACTIVE)
            .order_by(InstagramTarget.anonymous_report_count.desc())
            .limit(10)
        )
        targets = result.scalars().all()
        
        message = "📋 *مدیریت صفحات*\n\n"
        
        buttons = []
        for target in targets:
            message += f"• @{Formatters.escape_markdown(target.ig_handle)} \\- {target.anonymous_report_count} گزارش\n"
            buttons.append([
                InlineKeyboardButton(
                    f"@{target.ig_handle}",
                    callback_data=CallbackData.ADMIN_TARGET_EDIT.format(id=target.id)
                )
            ])
        
        if not targets:
            message += "_هیچ صفحه‌ای وجود ندارد\\._"
        
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_ADMIN)])
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


@admin_required
async def mark_as_victory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a target as removed (victory!)."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        # Update status
        target.status = TargetStatus.REMOVED
        target.removed_at = datetime.utcnow()
        
        # Create victory record
        victory = Victory(
            target_id=target.id,
            final_report_count=target.anonymous_report_count
        )
        session.add(victory)
        await session.commit()
        
        await query.answer(f"🏆 پیروزی ثبت شد! @{target.ig_handle}", show_alert=True)
        
        # Return to admin panel
        await query.edit_message_text(
            Messages.ADMIN_HEADER,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
        )


@admin_required
async def moderate_solidarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending solidarity messages for moderation."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(SolidarityMessage)
            .where(SolidarityMessage.is_approved == False)
            .order_by(SolidarityMessage.created_at.asc())
            .limit(1)
        )
        message = result.scalar_one_or_none()
        
        if not message:
            await query.edit_message_text(
                "💬 *تأیید پیام‌ها*\n\n_هیچ پیام در انتظار تأیید نیست\\._",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_admin()
            )
            return
        
        text = f"""
💬 *پیام در انتظار تأیید*

"{Formatters.escape_markdown(message.message)}"
"""
        if message.location:
            text += f"\n📍 {Formatters.escape_markdown(message.location)}"
        
        await query.edit_message_text(
            text,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_solidarity_moderation(message.id)
        )


@admin_required
async def approve_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a solidarity message."""
    query = update.callback_query
    
    message_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(SolidarityMessage).where(SolidarityMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if message:
            message.is_approved = True
            await session.commit()
        
        await query.answer("✅ پیام تأیید شد")
        
        # Show next message or return
        await moderate_solidarity(update, context)


@admin_required
async def reject_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a solidarity message."""
    query = update.callback_query
    
    message_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(SolidarityMessage).where(SolidarityMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if message:
            await session.delete(message)
            await session.commit()
        
        await query.answer("❌ پیام رد شد")
        
        # Show next message or return
        await moderate_solidarity(update, context)


# ═══════════════════════════════════════════════════════════════
# ADMIN MANAGEMENT (Super Admin Only)
# ═══════════════════════════════════════════════════════════════

@super_admin_required
async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of admins for management."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.role != AdminRole.SUPER_ADMIN).order_by(Admin.created_at.desc())
        )
        admins = result.scalars().all()
        
        message = "👥 *مدیریت ادمین‌ها*\n\n"
        
        if admins:
            message += "_برای حذف ادمین، روی آن کلیک کنید:_\n\n"
            for admin in admins:
                # Escape values to prevent Markdown errors
                safe_id = Formatters.escape_markdown(str(admin.telegram_id))
                safe_role = Formatters.escape_markdown(admin.role.value)
                message += f"• {safe_id} \\({safe_role}\\)\n"
        else:
            message += "_هیچ ادمینی ثبت نشده است\\._\n"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_list(admins)
        )


@super_admin_required
async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new admin."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ *افزودن ادمین جدید*\n\n"
        "لطفاً یکی از موارد زیر را ارسال کنید:\n\n"
        "1️⃣ نام کاربری \\(@username\\)\n"
        "2️⃣ شناسه عددی \\(User ID\\)\n"
        "3️⃣ *فوروارد کردن یک پیام از کاربر*",
        parse_mode="MarkdownV2"
    )
    
    return ADDING_ADMIN_ID


async def receive_admin_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive admin username and save."""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    display_name = text
    username_query = text
    
    # Ensure @ for username lookup (API usually expects @username for queries)
    if not text.isdigit() and not text.startswith("@"):
        username_query = f"@{text}"
    elif text.startswith("@"):
        username_query = text
    
    # Check if message is forwarded
    if update.message.forward_origin:
        # Telegram Update: forward_origin is used for general forwards in newer API, 
        # but PTB often abstracts this or uses forward_from for user forwards.
        # Let's check standard forward_from first.
        origin = update.message.forward_origin
        
        # Determine origin type (PTB v13 vs v20 distinction, assuming v20 object structure for safety)
        if hasattr(origin, 'type') and origin.type == 'user':
             new_admin_id = origin.sender_user.id
             display_name = origin.sender_user.first_name
        elif update.message.forward_from:
             new_admin_id = update.message.forward_from.id
             display_name = update.message.forward_from.first_name
        else:
             await update.message.reply_text(
                "⚠️ *شناسه مخفی شده است*\n\n"
                "کاربر تنظیمات حریم خصوصی خود را طوری تنظیم کرده که شناسه او در فوروارد نمایش داده نمی‌شود\\.\n"
                "لطفاً از روش **شناسه عددی (User ID)** استفاده کنید\\.",
                parse_mode="MarkdownV2"
            )
             return ADDING_ADMIN_ID

    elif not text:
         # No text and no forward?
         await update.message.reply_text("❌ لطفاً یک پیام متنی یا فوروارد ارسال کنید.")
         return ADDING_ADMIN_ID

    # 1. Try as User ID (digits)
    elif text.isdigit():
        new_admin_id = int(text)
        display_name = str(new_admin_id)
    
    # 2. Try as Username (via API)
    else:
        try:
             chat = await context.bot.get_chat(username_query)
             new_admin_id = chat.id
             display_name = chat.username or chat.first_name
        except Exception as e:
            logger.error(f"Failed to find user with query '{username_query}': {e}")
            # logger.exception(e) # Optional: print stack trace if needed
            await update.message.reply_text(
                "⚠️ *کاربر یافت نشد*\n\n"
                "ربات تلگرام تنها زمانی می‌تواند نام کاربری را پیدا کند که آن کاربر، ربات را `start` کرده باشد\\.\n\n"
                "💡 *راه حل‌ها:*\n"
                "۱\\. *فوروارد کردن پیام*: یک پیام از کاربر را به اینجا فوروارد کنید\\.\n"
                "2\\. *استارت*: از کاربر بخواهید ربات را استارت کند\\.\n"
                "3\\. *شناسه عددی*: شناسه عددی \\(User ID\\) کاربر را وارد کنید\\.",
                parse_mode="MarkdownV2"
            )
            return ADDING_ADMIN_ID
            
    if not new_admin_id:
         await update.message.reply_text("❌ خطای نامشخص", parse_mode="MarkdownV2")
         return ADDING_ADMIN_ID
    
    # Check if it's themselves
    if new_admin_id == user_id:
        await update.message.reply_text(
            "⚠️ شما نمی‌توانید خودتان را اضافه کنید\\!",
            parse_mode="MarkdownV2"
        )
        return ADDING_ADMIN_ID
    
    async with get_db() as session:
        # Check if already exists
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == new_admin_id)
        )
        if result.scalar_one_or_none():
            await update.message.reply_text(
                "⚠️ این کاربر قبلاً به عنوان ادمین ثبت شده است\\.",
                parse_mode="MarkdownV2"
            )
            return ADDING_ADMIN_ID
        
        # Add new admin
        new_admin = Admin(
            telegram_id=new_admin_id,
            role=AdminRole.MODERATOR # Default role
        )
        session.add(new_admin)
        await session.commit()
        
    await update.message.reply_text(
        f"✅ *ادمین جدید اضافه شد*\n\n"
        f"کاربر: {Formatters.escape_markdown(str(display_name))}\n"
        f"شناسه: `{new_admin_id}`",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=True) # Assuming adder is super
    )
    return ConversationHandler.END


@super_admin_required
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove an admin."""
    query = update.callback_query
    
    admin_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            await query.answer("❌ ادمین یافت نشد", show_alert=True)
            return
        
        # Don't allow removing super admins
        if admin.role == AdminRole.SUPER_ADMIN:
            await query.answer("⛔ ادمین‌های اصلی قابل حذف نیستند", show_alert=True)
            return
        
        telegram_id = admin.telegram_id
        await session.delete(admin)
        await session.commit()
        
        await query.answer(f"✅ ادمین {telegram_id} حذف شد")
        
        # Refresh the list
        await manage_admins(update, context)


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel admin action."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    await query.edit_message_text(
        Messages.ADMIN_HEADER,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=await is_super_admin(user_id))
    )
    
    return ConversationHandler.END

    return ConversationHandler.END


# Global Menu Pattern for Fallbacks
MENU_PATTERN = re.compile(f"^({'|'.join(map(re.escape, [
    Messages.MENU_TARGETS, Messages.MENU_ANNOUNCEMENTS, 
    Messages.MENU_PETITIONS, Messages.MENU_SOLIDARITY, 
    Messages.MENU_RESOURCES, Messages.MENU_SETTINGS, 
    Messages.ADMIN_HEADER
]))})$")


async def handle_menu_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle global menu commands by ending conversation and routing."""
    text = update.message.text
    context.user_data.clear()
    
    # Import handlers locally to avoid cycles
    from src.handlers import (
        instagram, announcements, petitions, solidarity,
        resources, settings
    )
    # We can call admin.admin_panel directly as we are in admin.py
    
    if text == Messages.MENU_TARGETS or "ریپورت ساندیسی" in text:
        await instagram.show_report_sandisi_menu(update, context)
    elif text == Messages.MENU_ANNOUNCEMENTS:
        await announcements.show_announcements(update, context)
    elif text == Messages.MENU_PETITIONS:
        await petitions.show_petitions(update, context)
    elif text == Messages.MENU_SOLIDARITY:
        await solidarity.show_solidarity(update, context)
    elif text == Messages.MENU_RESOURCES:
        await resources.show_resources(update, context)
    elif text == Messages.MENU_SETTINGS:
        await settings.show_settings(update, context)
    elif text == Messages.ADMIN_HEADER:
        await admin_panel(update, context)
    else:
        await update.message.reply_text(Messages.ERROR_GENERIC)
        
    return ConversationHandler.END


# Add target conversation handler
add_target_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_add_target, pattern=f"^{CallbackData.ADMIN_ADD_TARGET}$")
    ],
    states={
        ADDING_TARGET_HANDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(MENU_PATTERN), receive_target_handle),
        ],
        ADDING_TARGET_REASONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(MENU_PATTERN), receive_target_reasons),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_admin_action, pattern=f"^{CallbackData.BACK_MAIN}$"),
        MessageHandler(filters.Regex(MENU_PATTERN), handle_menu_fallback),
    ],
    per_message=False,
)


# Add admin conversation handler
add_admin_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_add_admin, pattern=f"^{CallbackData.ADMIN_ADD_ADMIN}$")
    ],
    states={
        ADDING_ADMIN_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(MENU_PATTERN), receive_admin_username),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_admin_action, pattern=f"^{CallbackData.BACK_MAIN}$"),
        MessageHandler(filters.Regex(MENU_PATTERN), handle_menu_fallback),
    ],
    per_message=False,
)


# ═══════════════════════════════════════════════════════════════
# PENDING TARGET APPROVAL
# ═══════════════════════════════════════════════════════════════

@admin_required
async def show_pending_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending targets for approval."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget)
            .where(InstagramTarget.status == TargetStatus.PENDING)
            .order_by(InstagramTarget.first_listed.asc())
            .limit(1)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            user_id = update.effective_user.id
            await query.edit_message_text(
                "✅ *صفحات پیشنهادی*\n\n_هیچ صفحه‌ای در انتظار تأیید نیست\\._",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_admin()
            )
            return
        
        # Show the pending target
        reasons_text = ", ".join(target.report_reasons) if target.report_reasons else "ندارد"
        message = (
            f"📋 *صفحه در انتظار تأیید*\n\n"
            f"📍 Handle: @{Formatters.escape_markdown(target.ig_handle)}\n"
            f"📋 دلایل: {Formatters.escape_markdown(reasons_text)}\n"
            f"🔗 [مشاهده صفحه](https://instagram.com/{target.ig_handle})"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_pending_approval(target.id),
            disable_web_page_preview=True
        )


@admin_required
async def approve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending target."""
    query = update.callback_query
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer("❌ صفحه یافت نشد", show_alert=True)
            return
        
        target.status = TargetStatus.ACTIVE
        await session.commit()
        
        await query.answer(f"✅ صفحه @{target.ig_handle} تأیید شد!")
        
        # Show next pending or return
        await show_pending_targets(update, context)


@admin_required
async def reject_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject and delete a pending target."""
    query = update.callback_query
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer("❌ صفحه یافت نشد", show_alert=True)
            return
        
        handle = target.ig_handle
        await session.delete(target)
        await session.commit()
        
        await query.answer(f"❌ صفحه @{handle} رد شد")
        
        # Show next pending or return
        await show_pending_targets(update, context)


@admin_required
async def confirm_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm a target removal and create victory."""
    query = update.callback_query
    await query.answer()
    
    # Extract ID from callback data: admin:confirm_removal:{id}
    try:
        target_id = int(query.data.split(":")[-1])
    except (ValueError, IndexError):
        await query.edit_message_text("❌ خطا در پردازش درخواست")
        return
        
    async with get_db() as session:
        # Get target
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.edit_message_text("❌ هدف پیدا نشد")
            return
            
        if target.status == TargetStatus.REMOVED:
            await query.edit_message_text("✅ این پیروزی قبلاً ثبت شده است.")
            return
            
        # Update status
        target.status = TargetStatus.REMOVED
        target.removed_at = datetime.utcnow()
        
        victory = Victory(
            target_id=target.id,
            victory_date=datetime.utcnow(),
            final_report_count=target.anonymous_report_count
        )
        session.add(victory)
        await session.commit()
        
        # Announce victory to admin
        await query.edit_message_text(
            f"🎉 *پیروزی ثبت شد!*\n\n"
            f"صفحه @{Formatters.escape_markdown(target.ig_handle)} به لیست پیروزی‌ها اضافه شد.\n"
            f"آمار ربات به‌روزرسانی شد.",
            parse_mode="MarkdownV2"
        )


@admin_required
async def admin_process_closed_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process closed report confirmation (Yes/No)."""
    query = update.callback_query
    action = query.data.split(":")[2] # 'yes' or 'no'
    target_id = int(query.data.split(":")[-1])
    
    if action == "no":
        await query.answer("❌ گزارش رد شد (تغییری ایجاد نشد)")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text(f"{query.message.text}\n\n❌ توسط ادمین رد شد.")
        return

    # Action YES
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            await query.edit_message_text("❌ هدف پیدا نشد")
            return
            
        if target.status == TargetStatus.REMOVED:
            await query.answer("⚠️ قبلاً ثبت شده", show_alert=True)
            await query.edit_message_text(f"{query.message.text}\n\n✅ قبلاً ثبت شده بود.")
            return

        # Update status
        target.status = TargetStatus.REMOVED
        target.removed_at = datetime.utcnow()
        
        victory = Victory(
            target_id=target.id,
            victory_date=datetime.utcnow(),
            final_report_count=target.anonymous_report_count
        )
        session.add(victory)
        await session.commit()
        
        await query.answer("🏆 پیروزی ثبت شد!", show_alert=True)
        await query.edit_message_text(
            f"{query.message.text}\n\n🏆 *تایید شد: پیروزی ثبت شد!*",
            parse_mode="MarkdownV2"
        )


# Export handlers
admin_handlers = [
    CommandHandler("admin", admin_panel),
    CallbackQueryHandler(admin_panel, pattern=r"^admin:panel$"),
    add_target_conversation,
    add_admin_conversation,
    CallbackQueryHandler(manage_targets, pattern=f"^{CallbackData.ADMIN_MANAGE_TARGETS}$"),
    CallbackQueryHandler(mark_as_victory, pattern=r"^admin:target:victory:\d+$"),
    CallbackQueryHandler(confirm_removal, pattern=r"^admin:confirm_removal:\d+$"),
    CallbackQueryHandler(moderate_solidarity, pattern=f"^{CallbackData.ADMIN_SOLIDARITY}$"),
    CallbackQueryHandler(approve_message, pattern=r"^admin:approve_msg:\d+$"),
    CallbackQueryHandler(reject_message, pattern=r"^admin:reject_msg:\d+$"),
    CallbackQueryHandler(manage_admins, pattern=f"^{CallbackData.ADMIN_MANAGE_ADMINS}$"),
    CallbackQueryHandler(remove_admin, pattern=r"^admin:remove_admin:\d+$"),
    CallbackQueryHandler(show_pending_targets, pattern=f"^{CallbackData.ADMIN_PENDING_TARGETS}$"),
    CallbackQueryHandler(approve_target, pattern=r"^admin:approve_target:\d+$"),
    CallbackQueryHandler(reject_target, pattern=r"^admin:reject_target:\d+$"),
    CallbackQueryHandler(reject_target, pattern=r"^admin:reject_target:\d+$"),
    # Quick Action Confirmation
    CallbackQueryHandler(admin_process_closed_report, pattern=r"^admin:closed:(yes|no):\d+$"),
    # Back to Admin Panel
    CallbackQueryHandler(admin_panel, pattern=f"^{CallbackData.BACK_ADMIN}$"),
]
