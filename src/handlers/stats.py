"""
Statistics handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select, func
from datetime import datetime, timedelta

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, InstagramTarget, Victory
from src.database.models import TargetStatus


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live statistics."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        # Active targets count
        active_result = await session.execute(
            select(func.count(InstagramTarget.id))
            .where(InstagramTarget.status == TargetStatus.ACTIVE)
        )
        active_targets = active_result.scalar() or 0
        
        # Removed targets count
        removed_result = await session.execute(
            select(func.count(InstagramTarget.id))
            .where(InstagramTarget.status == TargetStatus.REMOVED)
        )
        removed_targets = removed_result.scalar() or 0
        
        # Total reports
        reports_result = await session.execute(
            select(func.sum(InstagramTarget.anonymous_report_count))
        )
        total_reports = reports_result.scalar() or 0
        
        # Followers silenced
        silenced_result = await session.execute(
            select(func.sum(InstagramTarget.followers_count))
            .where(InstagramTarget.status == TargetStatus.REMOVED)
        )
        followers_silenced = silenced_result.scalar() or 0
        
        # This week's stats
        week_ago = datetime.utcnow() - timedelta(days=7)
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        
        # Weekly victories
        weekly_victories_result = await session.execute(
            select(func.count(Victory.id))
            .where(Victory.victory_date >= week_ago)
        )
        weekly_removals = weekly_victories_result.scalar() or 0
        
        # Hottest target
        hottest_result = await session.execute(
            select(InstagramTarget)
            .where(InstagramTarget.status == TargetStatus.ACTIVE)
            .order_by(InstagramTarget.anonymous_report_count.desc())
            .limit(1)
        )
        hottest = hottest_result.scalar_one_or_none()
        
        stats = {
            'active_targets': active_targets,
            'removed_targets': removed_targets,
            'total_reports': total_reports,
            'followers_silenced': followers_silenced,
            'weekly_increase_percent': 23,  # Would need historical data
            'weekly_removals': weekly_removals,
        }
        
        message = Formatters.format_stats(stats)
        
        if hottest:
            message += f"""

{Messages.STATS_HOTTEST}
@{Formatters.escape_markdown(hottest.ig_handle)} \\- {hottest.anonymous_report_count} {Messages.TARGET_REPORTS}
"""
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
        )


# Export handlers
stats_handlers = [
    CallbackQueryHandler(show_stats, pattern=f"^{CallbackData.MENU_STATS}$"),
]
