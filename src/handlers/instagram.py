"""
Instagram target handlers for Sedaye Ma bot.
Handles listing, viewing, and reporting Instagram targets.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select
from datetime import datetime

from config import Messages, settings
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.utils.decorators import rate_limit
from src.database import get_db, InstagramTarget, ReportTemplate
from src.database.models import TargetStatus


TARGETS_PER_PAGE = 5


async def show_report_sandisi_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Report Sandisi submenu."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            Messages.REPORT_SANDISI_DESCRIPTION,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.report_sandisi_menu()
        )
    else:
        # From text menu
        await update.message.reply_text(
            Messages.REPORT_SANDISI_DESCRIPTION,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.report_sandisi_menu()
        )


async def show_filter_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the targets filter menu (New vs All)."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        (
            "� *کدام صفحات را نمایش دهیم؟*\n\n"
            "🧃 جدید: ساندیسی هایی که هنوز شما ریپورت نکردین\n"
            "🕰️ قدیمی: ساندیسی هایی که قبلا ریپورت کردین"
        ),
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.targets_filter_menu()
    )


async def show_targets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of active targets with optional filter."""
    query = update.callback_query
    if not context.user_data.get('skip_answer'):
        await query.answer()
    
    # Determine filter type from callback data
    # Defaults to ALL if not specified (legacy behavior)
    filter_type = CallbackData.FILTER_ALL
    if query.data in [CallbackData.FILTER_NEW, CallbackData.FILTER_REPORTED, CallbackData.FILTER_ALL]:
        filter_type = query.data
        # Save filter in user_context for pagination
        context.user_data['targets_filter'] = filter_type
    elif 'targets_filter' in context.user_data:
        filter_type = context.user_data['targets_filter']
        
    # Prepare User Hash for filtering
    user_id = query.from_user.id
    from src.database.models import UserReportLog, User
    from src.utils.security import encrypt_id
    
    enc_id = encrypt_id(user_id)
    
    async with get_db() as session:
        # Get canonical encrypted ID for filtering
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        db_user = res_user.scalar_one_or_none()

        # Base query
        stmt = select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        
        # Apply Filter
        # Default flag
        show_report_btn = True

        # Apply Filter
        if filter_type == CallbackData.FILTER_NEW:
            if enc_id:
                # Subquery: IDs user has reported
                subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                stmt = stmt.where(InstagramTarget.id.not_in(subq))
            # If no enc_id, they haven't reported anything, so ALL are new. No filter needed.
            
            header_text = f"{Messages.TARGETS_HEADER}\n\n{Messages.REPORTING_STEP_BY_STEP}\n{Messages.TARGETS_PROBLEM_HELP}"
            
        elif filter_type == CallbackData.FILTER_REPORTED:
            if enc_id:
                # Subquery: IDs user HAS reported
                subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                stmt = stmt.where(InstagramTarget.id.in_(subq))
            else:
                 # No reports, so return empty
                 stmt = stmt.where(InstagramTarget.id == -1) # Impossible ID

            # Enhanced description for reported validation
            header_text = (
                f"{Messages.TARGETS_HEADER}\n\n"
                "✅ *گزارش‌های من*\n"
                "لیست صفحاتی که شما قبلاً گزارش داده‌اید\\.\n"
                "نیازی به اقدام مجدد برای این موارد نیست، مگر اینکه مشکل جدیدی پیش آمده باشد\\.\n\n"
                f"{Messages.TARGETS_PROBLEM_HELP}"
            )
            show_report_btn = False
            
        else:
            header_text = f"{Messages.TARGETS_HEADER}\n\n📋 *همه صفحات*\n{Messages.TARGETS_PROBLEM_HELP}"

        # Order and Limit
        stmt = stmt.order_by(InstagramTarget.priority.asc(), InstagramTarget.anonymous_report_count.desc())
        stmt = stmt.limit(TARGETS_PER_PAGE)
        
        result = await session.execute(stmt)
        targets = result.scalars().all()
        
        if not targets:
            empty_msg = Messages.TARGETS_EMPTY
            if filter_type == CallbackData.FILTER_NEW:
                empty_msg = "👏 آفرین\\! شما تمام صفحات فعال را گزارش کرده‌اید\\."
            elif filter_type == CallbackData.FILTER_REPORTED:
                empty_msg = "شما هنوز هیچ صفحه‌ای را گزارش نکرده‌اید\\."
                
            await query.edit_message_text(
                f"{header_text}\n\n{empty_msg}",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_sandisi()
            )
            return
        
        # Count total for pagination (reuse basic query logic logic)
        # Re-build count query efficiently
        count_stmt = select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        if filter_type == CallbackData.FILTER_NEW:
             if enc_id:
                 subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                 count_stmt = count_stmt.where(InstagramTarget.id.not_in(subq))
        elif filter_type == CallbackData.FILTER_REPORTED:
             if enc_id:
                 subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                 count_stmt = count_stmt.where(InstagramTarget.id.in_(subq))
             else:
                 count_stmt = count_stmt.where(InstagramTarget.id == -1)
             
        count_result = await session.execute(count_stmt)
        total = len(count_result.scalars().all())
        total_pages = (total + TARGETS_PER_PAGE - 1) // TARGETS_PER_PAGE
        
        await query.edit_message_text(
            header_text,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.targets_list(
                targets, 
                page=0, 
                total_pages=total_pages, 
                show_report_button=show_report_btn
            )
        )


async def show_targets_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated targets with active filter."""
    query = update.callback_query
    await query.answer()
    
    # Extract page number from callback data
    page = int(query.data.split(":")[-1])
    offset = page * TARGETS_PER_PAGE
    
    # Get active filter from context
    filter_type = context.user_data.get('targets_filter', CallbackData.FILTER_ALL)
    
    # Prepare User Hash
    user_id = query.from_user.id
    from src.database.models import UserReportLog, User
    from src.utils.security import encrypt_id
    
    enc_id = encrypt_id(user_id)
    
    async with get_db() as session:
        # Get canonical encrypted ID for filtering
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        db_user = res_user.scalar_one_or_none()

        stmt = select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        
        # Default flag
        show_report_btn = True
        
        if filter_type == CallbackData.FILTER_NEW:
            if enc_id:
                subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                stmt = stmt.where(InstagramTarget.id.not_in(subq))
            header_text = f"{Messages.TARGETS_HEADER}\n\n🆕 *صفحات جدید \\(گزارش نشده توسط شما\\)*\n\n_📝 دکمه «گزارش»: اگر فکر می‌کنید صفحه بسته شده است یا مشکل دیگری هست حتما به ما گزارش دهید\\!_"
            
        elif filter_type == CallbackData.FILTER_REPORTED:
            if enc_id:
                subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                stmt = stmt.where(InstagramTarget.id.in_(subq))
            else:
                 stmt = stmt.where(InstagramTarget.id == -1)

            # Enhanced description for reported validation
            header_text = (
                f"{Messages.TARGETS_HEADER}\n\n"
                "✅ *گزارش‌های من*\n"
                "لیست صفحاتی که شما قبلاً گزارش داده‌اید\\.\n"
                "نیازی به اقدام مجدد برای این موارد نیست، مگر اینکه مشکل جدیدی پیش آمده باشد\\.\n\n"
                "_📝 دکمه «گزارش»: اگر فکر می‌کنید صفحه بسته شده است یا مشکل دیگری هست حتما به ما گزارش دهید\\!_"
            )
            show_report_btn = False
        else:
            header_text = f"{Messages.TARGETS_HEADER}\n\n📋 *همه صفحات*"
            
        # Order and Limit
        stmt = stmt.order_by(InstagramTarget.priority.asc(), InstagramTarget.anonymous_report_count.desc())
        stmt = stmt.offset(offset).limit(TARGETS_PER_PAGE)
        
        result = await session.execute(stmt)
        targets = result.scalars().all()
        
        # Count total
        count_stmt = select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        if filter_type == CallbackData.FILTER_NEW:
             if enc_id:
                 subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                 count_stmt = count_stmt.where(InstagramTarget.id.not_in(subq))
        elif filter_type == CallbackData.FILTER_REPORTED:
             if enc_id:
                 subq = select(UserReportLog.target_id).where(UserReportLog.encrypted_user_id == enc_id)
                 count_stmt = count_stmt.where(InstagramTarget.id.in_(subq))
             else:
                 count_stmt = count_stmt.where(InstagramTarget.id == -1)
             
        count_result = await session.execute(count_stmt)
        total = len(count_result.scalars().all())
        total_pages = (total + TARGETS_PER_PAGE - 1) // TARGETS_PER_PAGE
        
        await query.edit_message_text(
            header_text,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.targets_list(
                targets, 
                page=page, 
                total_pages=total_pages, 
                show_report_button=show_report_btn
            )
        )


async def view_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a specific target's details."""
    query = update.callback_query
    await query.answer()
    
    # Extract target ID
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        message = Formatters.format_target_card(target)
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.target_actions(target.id, target.ig_handle)
        )


async def show_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show report template for a target."""
    query = update.callback_query
    
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        # Get target
        target_result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = target_result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        # Get first matching template based on target's reasons
        template = None
        if target.report_reasons:
            template_result = await session.execute(
                select(ReportTemplate).where(
                    ReportTemplate.violation_type == target.report_reasons[0],
                    ReportTemplate.is_active == True
                )
            )
            template = template_result.scalar_one_or_none()
        
        # Fallback to generic
        if not template:
            template_result = await session.execute(
                select(ReportTemplate).where(ReportTemplate.is_active == True).limit(1)
            )
            template = template_result.scalar_one_or_none()
        
        if template:
            message = Formatters.format_template(template)
            await query.answer()
            await query.edit_message_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.target_actions(target.id, target.ig_handle)
            )
        else:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)


@rate_limit(limit=20, window=60, penalty_time=3600) # 20 reports per minute, else 1h ban
async def i_reported_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'I reported' button - increment counter."""
    query = update.callback_query
    
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        # 1. Check if user already reported
        user_id = query.from_user.id
        from src.database.models import UserReportLog, User
        from src.utils.security import encrypt_id
        
        enc_id = encrypt_id(user_id)
        
        # Get Encrypted ID
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        user = res_user.scalar_one_or_none()

        # Check for existing log
        existing_log = await session.execute(
            select(UserReportLog).where(
                UserReportLog.target_id == target_id,
                UserReportLog.encrypted_user_id == enc_id
            )
        )
        if existing_log.scalar_one_or_none():
            await query.answer("⚠️ شما قبلاً این صفحه را گزارش کرده‌اید!", show_alert=True)
            return

        # 2. Get target
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        # 3. Log the report (Securely)
        new_log = UserReportLog(target_id=target_id, encrypted_user_id=enc_id)
        session.add(new_log)
        
        # Increment counter (anonymous!)
        target.anonymous_report_count += 1
        await session.commit()
        
        await query.answer("🙏 ممنون! گزارش شما ثبت شد ✊", show_alert=True)
        
        # Check context: List or Card?
        # If it's a list header, refresh list. Else refresh card.
        # Simple heuristic: If text contains header, it's a list.
        # But text might be truncated or difficult to check reliably.
        # Safer: Set a flag when showing list? 
        # Actually, user request "make it so that... report faster" implies List View.
        # I will prioritize List View refresh.
        
        # Prevent double answer in show_targets_list
        context.user_data['skip_answer'] = True
        try:
            await show_targets_list(update, context)
        finally:
            context.user_data['skip_answer'] = False


# Concern Conversation States
CHOOSING_CONCERN = 1
WAITING_FOR_CONCERN_MESSAGE = 2

async def start_concern_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start concern report flow - Show Menu."""
    query = update.callback_query
    target_id = int(query.data.split(":")[-1])
    await query.answer()
    
    # Determine if user is an admin
    from src.database.models import Admin
    from src.utils.security import encrypt_id
    
    user_id = query.from_user.id
    enc_id = encrypt_id(user_id)
    
    async with get_db() as session:
        result = await session.execute(
            select(Admin).where(Admin.encrypted_telegram_id == enc_id)
        )
        is_admin = result.scalar_one_or_none() is not None

    await query.edit_message_text(
        "🤔 *گزارش مشکل*\n\nلطفاً نوع مشکل را انتخاب کنید:",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.concern_menu(target_id, is_admin=is_admin)
    )
    return CHOOSING_CONCERN

async def concern_closed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected 'Page Closed'."""
    query = update.callback_query
    target_id = int(query.data.split(":")[-1])
    await query.answer()
    
    async with get_db() as session:
        # Get target info
        target = (await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )).scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return ConversationHandler.END

        # Check for Duplicate Concern
        # 1. Check if reporting user is an admin
        user_id = query.from_user.id
        from src.database.models import UserConcernLog, User, Admin, Victory
        from src.utils.security import encrypt_id, decrypt_id
        
        enc_id = encrypt_id(user_id)
        
        result_admin = await session.execute(
            select(Admin).where(Admin.encrypted_telegram_id == enc_id)
        )
        admin_obj = result_admin.scalar_one_or_none()
        
        if admin_obj:
            # ADMIN: Directly confirm victory
            target.status = TargetStatus.REMOVED
            target.removed_at = datetime.utcnow()
            
            victory = Victory(
                target_id=target.id,
                victory_date=datetime.utcnow(),
                final_report_count=target.anonymous_report_count
            )
            session.add(victory)
            await session.commit()
            
            await query.answer("🏆 پیروزی مستقیماً ثبت شد!", show_alert=True)
            
            # Broadcast Victory
            try:
                from src.services.notification_service import NotificationService
                await NotificationService(context.bot).broadcast_victory(victory, target)
            except Exception as e:
                logger.error(f"Failed to broadcast direct victory: {e}")
            
            # Show updated list
            await show_targets_list(update, context)
            return ConversationHandler.END

        # NORMAL USER: Proceed with admin notification/approval flow
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        user_obj = res_user.scalar_one_or_none()
        
        existing_log = await session.execute(
            select(UserConcernLog).where(
                UserConcernLog.target_id == target_id,
                UserConcernLog.encrypted_user_id == enc_id,
                UserConcernLog.concern_type == "closed"
            )
        )
        if existing_log.scalar_one_or_none():
            await query.answer("⚠️ شما قبلاً گزارش بسته شدن این صفحه را ارسال کرده‌اید.", show_alert=True)
            return ConversationHandler.END

        # Notify Admins
        admins = (await session.execute(select(Admin))).scalars().all()
        
        for admin in admins:
            try:
                await context.bot.send_message(
                    chat_id=decrypt_id(admin.encrypted_telegram_id),
                    text=f"🚨 *گزارش بسته شدن صفحه*\n\nSandisi: @{target.ig_handle}\nID: `{target.id}`\n\nآیا این صفحه بسته شده است؟",
                    parse_mode="HTML",
                    reply_markup=Keyboards.admin_confirm_closed(target.id)
                )
            except Exception:
                pass
        
        # Log It
        new_log = UserConcernLog(target_id=target_id, encrypted_user_id=enc_id, concern_type="closed")
        session.add(new_log)
        await session.commit()

    await query.answer("✅ گزارش شما برای ادمین ارسال شد.", show_alert=True)
    return ConversationHandler.END

async def concern_other_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected 'Other' - Ask for message."""
    query = update.callback_query
    target_id = int(query.data.split(":")[-1])
    
    context.user_data['concern_target_id'] = target_id
    
    await query.answer()
    await query.edit_message_text(
        "💬 *توضیحات شما*\n\nلطفاً پیام خود را بنویسید \\(توضیح دهید مشکل چیست یا چه اتفاقی افتاده\\):",
        parse_mode="MarkdownV2"
    )
    return WAITING_FOR_CONCERN_MESSAGE

async def receive_concern_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the custom concern message."""
    text = update.message.text
    target_id = context.user_data.get('concern_target_id')
    user = update.effective_user
    
    if not target_id:
        await update.message.reply_text("⚠️ خطا در پردازش. لطفاً مجدد تلاش کنید.")
        return ConversationHandler.END
        
    async with get_db() as session:
        # Get target info
        target = (await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )).scalar_one_or_none()
        
        # Save to Database
        from src.database.models import UserConcernLog, User
        from src.utils.security import encrypt_id
        
        enc_id = encrypt_id(user.id)
        
        res_user = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        user_obj = res_user.scalar_one_or_none()
        
        # Check duplicate (one "other" per target per user?)
        # Or allow multiple messages? Maybe limit spam?
        # Let's check duplicate for now
        existing_log = await session.execute(
            select(UserConcernLog).where(
                UserConcernLog.target_id == target_id,
                UserConcernLog.encrypted_user_id == enc_id,
                UserConcernLog.concern_type == "other"
            )
        )
        if existing_log.scalar_one_or_none():
             # Update message instead of duplicate? Or reject?
             # Rejecting is safer for spam
             await update.message.reply_text("⚠️ شما قبلاً پیامی درباره این صفحه ثبت کرده‌اید.")
             return ConversationHandler.END

        # Create Log
        new_log = UserConcernLog(
            target_id=target_id, 
            encrypted_user_id=enc_id, 
            concern_type="other",
            message_content=text 
        )
        session.add(new_log)
        await session.commit()
        
        # Notify Admins (Keep existing notification as backup/alert)
        from src.database.models import Admin
        admins = (await session.execute(select(Admin))).scalars().all()
        
        for admin in admins:
            try:
                from src.utils.security import decrypt_id
                await context.bot.send_message(
                    chat_id=decrypt_id(admin.encrypted_telegram_id),
                    text=f"📨 *پیام کاربر (مشکل صفحه)*\n\n👤 کاربر: ناشناس (Anonymous)\nTarget: @{target.ig_handle if target else 'Unknown'}\n\n💬 پیام:\n{text}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    await update.message.reply_text(
        "✅ پیام شما برای ادمین‌ها ارسال شد.\nممنون از گزارش شما 🙏",
        reply_markup=Keyboards.back_to_sandisi()
    )
    return ConversationHandler.END


async def cancel_concern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel concern flow."""
    query = update.callback_query
    await query.answer()
    
    # Return to List
    # We need to render the list. 
    # Calling show_targets_list requires 'targets_filter' in user_data which should persist.
    await show_targets_list(update, context)
    return ConversationHandler.END

# Don't forget import ConversationHandler, filters, MessageHandler
from telegram.ext import ConversationHandler, MessageHandler, filters

concern_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_concern_report, pattern=r"^target:report_closed:\d+$")
    ],
    states={
        CHOOSING_CONCERN: [
            CallbackQueryHandler(concern_closed_handler, pattern=r"^target:concern:closed:\d+$"),
            CallbackQueryHandler(concern_other_handler, pattern=r"^target:concern:other:\d+$"),
        ],
        WAITING_FOR_CONCERN_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_concern_message)
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_concern, pattern=f"^{CallbackData.TARGETS_LIST}$"),
    ],
    per_message=False # Important for CallbackQuery mixed with Message
)


# Export handlers
instagram_handlers = [
    concern_conversation, # Must be first to handle 'Back' properly
    CallbackQueryHandler(show_report_sandisi_menu, pattern=f"^{CallbackData.MENU_TARGETS}$"),
    CallbackQueryHandler(show_filter_menu, pattern=f"^{CallbackData.FILTER_MENU}$"),
    CallbackQueryHandler(show_targets_list, pattern=f"^{CallbackData.TARGETS_LIST}$"),
    CallbackQueryHandler(show_targets_list, pattern=f"^{CallbackData.FILTER_NEW}$"),
    CallbackQueryHandler(show_targets_list, pattern=f"^{CallbackData.FILTER_REPORTED}$"),
    CallbackQueryHandler(show_targets_list, pattern=f"^{CallbackData.FILTER_ALL}$"),
    CallbackQueryHandler(show_targets_page, pattern=r"^targets:page:\d+$"),
    CallbackQueryHandler(view_target, pattern=r"^target:view:\d+$"),
    CallbackQueryHandler(show_template, pattern=r"^target:template:\d+$"),
    CallbackQueryHandler(i_reported_handler, pattern=r"^target:reported:\d+$"),
]
