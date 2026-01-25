"""
Admin handlers for Sedaye Ma bot.
Protected commands for managing the bot.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
from sqlalchemy import select
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


def is_super_admin(user_id: int) -> bool:
    """Check if user is a super admin."""
    return user_id in settings.super_admin_ids


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    from sqlalchemy import func
    
    user_id = update.effective_user.id
    super_admin = is_super_admin(user_id)
    
    # Get pending targets count
    async with get_db() as session:
        result = await session.execute(
            select(func.count(InstagramTarget.id)).where(
                InstagramTarget.status == TargetStatus.PENDING
            )
        )
        pending_count = result.scalar() or 0
    
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


@admin_required
async def start_add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new target."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ *افزودن صفحه جدید*\n\nلطفاً handle اینستاگرام را وارد کنید \\(بدون @\\):",
        parse_mode="MarkdownV2"
    )
    
    return ADDING_TARGET_HANDLE


async def receive_target_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive target handle and validate it."""
    from src.services.instagram import InstagramValidator, validate_instagram_handle
    from src.utils.validators import Validators
    
    handle = update.message.text.strip().replace("@", "").lower()
    user_id = update.effective_user.id
    
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
        return ADDING_TARGET_HANDLE
    
    # Check if already in database
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
        )
        if result.scalar_one_or_none():
            await loading_msg.edit_text(
                f"⚠️ صفحه @{Formatters.escape_markdown(handle)} قبلاً در لیست وجود دارد\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
            )
            return ConversationHandler.END
    
    # Validate on Instagram
    profile = await validate_instagram_handle(handle)
    
    if not profile.exists:
        await loading_msg.edit_text(
            f"❌ *صفحه پیدا نشد*\n\n"
            f"صفحه @{Formatters.escape_markdown(handle)} در اینستاگرام وجود ندارد\\.\n\n"
            "لطفاً یک handle معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
        return ADDING_TARGET_HANDLE
    
    # Store handle for next step
    context.user_data["new_target_handle"] = handle
    
    # Show confirmation with reasons prompt
    await loading_msg.edit_text(
        f"✅ *صفحه تأیید شد*\n\n"
        f"📍 Handle: @{Formatters.escape_markdown(handle)}\n\n"
        "حالا دلایل گزارش را وارد کنید \\(با کاما جدا کنید\\):\n"
        "`violence, misinformation, propaganda, human_rights, harassment`",
        parse_mode="MarkdownV2"
    )
    
    return ADDING_TARGET_REASONS


async def receive_target_reasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive target reasons and save."""
    from src.utils.validators import Validators
    
    reasons_text = update.message.text.strip()
    reasons_list = [r.strip().lower() for r in reasons_text.split(",")]
    handle = context.user_data.get("new_target_handle")
    user_id = update.effective_user.id
    
    if not handle:
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
    
    async with get_db() as session:
        # Double-check for duplicates
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.ig_handle == handle)
        )
        if result.scalar_one_or_none():
            await update.message.reply_text(
                f"⚠️ این صفحه قبلاً اضافه شده است\\.",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
            )
            return ConversationHandler.END
        
        target = InstagramTarget(
            ig_handle=handle,
            report_reasons=reasons,
            priority=5,
            status=TargetStatus.ACTIVE
        )
        session.add(target)
        await session.commit()
    
    await update.message.reply_text(
        f"✅ *صفحه اضافه شد\\!*\n\n"
        f"📍 Handle: @{Formatters.escape_markdown(handle)}\n"
        f"📋 دلایل: {Formatters.escape_markdown(', '.join(reasons))}",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
    )
    
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
        
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)])
        
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
                reply_markup=Keyboards.back_to_main()
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
            select(Admin).order_by(Admin.created_at.desc())
        )
        admins = result.scalars().all()
        
        message = "👥 *مدیریت ادمین‌ها*\n\n"
        
        if admins:
            message += "_برای حذف ادمین، روی آن کلیک کنید:_\n\n"
            for admin in admins:
                message += f"• {admin.telegram_id} \\({admin.role.value}\\)\n"
        else:
            message += "_هیچ ادمینی ثبت نشده است\\._\n"
        
        message += f"\n💡 _ادمین‌های اصلی \\(SUPER\\) در فایل \\.env تعریف شده‌اند و قابل حذف نیستند\\._"
        
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
        "لطفاً شناسه عددی تلگرام \\(Telegram ID\\) کاربر را وارد کنید:\n\n"
        "_کاربر می‌تواند شناسه خود را از @userinfobot بگیرد\\._",
        parse_mode="MarkdownV2"
    )
    
    return ADDING_ADMIN_ID


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive admin ID and save."""
    from src.utils.validators import Validators
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validate Telegram ID
    is_valid, new_admin_id, error = Validators.validate_telegram_id(text)
    if not is_valid:
        await update.message.reply_text(
            f"⚠️ {Formatters.escape_markdown(error or 'Invalid ID')}\n\n"
            "لطفاً یک شناسه معتبر وارد کنید:",
            parse_mode="MarkdownV2"
        )
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
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
            )
            return ConversationHandler.END
        
        # Add new admin
        new_admin = Admin(
            telegram_id=new_admin_id,
            role=AdminRole.ADMIN
        )
        session.add(new_admin)
        await session.commit()
    
    await update.message.reply_text(
        f"✅ کاربر {new_admin_id} با موفقیت به عنوان ادمین اضافه شد\\!",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
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
        
        # Don't allow removing super admins defined in env
        if admin.telegram_id in settings.super_admin_ids:
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
        reply_markup=Keyboards.admin_menu(is_super_admin=is_super_admin(user_id))
    )
    
    return ConversationHandler.END


# Add target conversation handler
add_target_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_add_target, pattern=f"^{CallbackData.ADMIN_ADD_TARGET}$")
    ],
    states={
        ADDING_TARGET_HANDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_handle),
        ],
        ADDING_TARGET_REASONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_reasons),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_admin_action, pattern=f"^{CallbackData.BACK_MAIN}$"),
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
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_admin_action, pattern=f"^{CallbackData.BACK_MAIN}$"),
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
                reply_markup=Keyboards.back_to_main()
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


# Export handlers
admin_handlers = [
    CommandHandler("admin", admin_panel),
    CallbackQueryHandler(admin_panel, pattern=r"^admin:panel$"),
    add_target_conversation,
    add_admin_conversation,
    CallbackQueryHandler(manage_targets, pattern=f"^{CallbackData.ADMIN_MANAGE_TARGETS}$"),
    CallbackQueryHandler(mark_as_victory, pattern=r"^admin:target:victory:\d+$"),
    CallbackQueryHandler(moderate_solidarity, pattern=f"^{CallbackData.ADMIN_SOLIDARITY}$"),
    CallbackQueryHandler(approve_message, pattern=r"^admin:approve_msg:\d+$"),
    CallbackQueryHandler(reject_message, pattern=r"^admin:reject_msg:\d+$"),
    CallbackQueryHandler(manage_admins, pattern=f"^{CallbackData.ADMIN_MANAGE_ADMINS}$"),
    CallbackQueryHandler(remove_admin, pattern=r"^admin:remove_admin:\d+$"),
    CallbackQueryHandler(show_pending_targets, pattern=f"^{CallbackData.ADMIN_PENDING_TARGETS}$"),
    CallbackQueryHandler(approve_target, pattern=r"^admin:approve_target:\d+$"),
    CallbackQueryHandler(reject_target, pattern=r"^admin:reject_target:\d+$"),
]
