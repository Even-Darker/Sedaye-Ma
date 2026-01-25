"""
Instagram target handlers for Sedaye Ma bot.
Handles listing, viewing, and reporting Instagram targets.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
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


async def show_targets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of active targets."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget)
            .where(InstagramTarget.status == TargetStatus.ACTIVE)
            .order_by(InstagramTarget.priority.asc(), InstagramTarget.anonymous_report_count.desc())
            .limit(TARGETS_PER_PAGE)
        )
        targets = result.scalars().all()
        
        if not targets:
            await query.edit_message_text(
                f"{Messages.TARGETS_HEADER}\n\n{Messages.TARGETS_EMPTY}",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_main()
            )
            return
        
        # Count total for pagination
        count_result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        )
        total = len(count_result.scalars().all())
        total_pages = (total + TARGETS_PER_PAGE - 1) // TARGETS_PER_PAGE
        
        await query.edit_message_text(
            Messages.TARGETS_HEADER,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.targets_list(targets, page=0, total_pages=total_pages)
        )


async def show_targets_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated targets."""
    query = update.callback_query
    await query.answer()
    
    # Extract page number from callback data
    page = int(query.data.split(":")[-1])
    offset = page * TARGETS_PER_PAGE
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget)
            .where(InstagramTarget.status == TargetStatus.ACTIVE)
            .order_by(InstagramTarget.priority.asc(), InstagramTarget.anonymous_report_count.desc())
            .offset(offset)
            .limit(TARGETS_PER_PAGE)
        )
        targets = result.scalars().all()
        
        # Count total for pagination
        count_result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.status == TargetStatus.ACTIVE)
        )
        total = len(count_result.scalars().all())
        total_pages = (total + TARGETS_PER_PAGE - 1) // TARGETS_PER_PAGE
        
        await query.edit_message_text(
            Messages.TARGETS_HEADER,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.targets_list(targets, page=page, total_pages=total_pages)
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


async def i_reported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'I reported' button - increment counter."""
    query = update.callback_query
    
    target_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(InstagramTarget).where(InstagramTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        # Increment counter (anonymous!)
        target.anonymous_report_count += 1
        await session.commit()
        
        await query.answer("🙏 ممنون! گزارش شما ثبت شد ✊", show_alert=True)
        
        # Update the card with new count
        message = Formatters.format_target_card(target)
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.target_actions(target.id, target.ig_handle)
        )


# Export handlers
instagram_handlers = [
    CallbackQueryHandler(show_report_sandisi_menu, pattern=f"^{CallbackData.MENU_TARGETS}$"),
    CallbackQueryHandler(show_targets_list, pattern=f"^{CallbackData.TARGETS_LIST}$"),
    CallbackQueryHandler(show_targets_page, pattern=r"^targets:page:\d+$"),
    CallbackQueryHandler(view_target, pattern=r"^target:view:\d+$"),
    CallbackQueryHandler(show_template, pattern=r"^target:template:\d+$"),
    CallbackQueryHandler(i_reported, pattern=r"^target:reported:\d+$"),
]
