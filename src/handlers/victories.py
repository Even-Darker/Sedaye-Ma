"""
Victory Wall handlers for Sedaye Ma bot.
Displays successfully removed Instagram pages.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select, func
from datetime import datetime, timedelta

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, Victory, InstagramTarget
from src.database.models import TargetStatus


async def show_victories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show victory wall."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        # Get this week's victories
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        weekly_result = await session.execute(
            select(Victory).where(Victory.victory_date >= week_ago)
        )
        weekly_victories = len(weekly_result.scalars().all())
        
        # Get total victories
        total_result = await session.execute(select(func.count(Victory.id)))
        total_victories = total_result.scalar() or 0
        
        # Get total followers silenced
        silenced_result = await session.execute(
            select(func.sum(InstagramTarget.followers_count))
            .where(InstagramTarget.status == TargetStatus.REMOVED)
        )
        followers_silenced = silenced_result.scalar() or 0
        
        # Get latest victory
        latest_result = await session.execute(
            select(Victory)
            .order_by(Victory.victory_date.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()
        
        # Build message
        message = f"""
{Messages.VICTORIES_HEADER}
{Messages.VICTORIES_SUBTITLE}

{Messages.VICTORY_THIS_WEEK.format(weekly_victories)}
{Messages.VICTORY_TOTAL.format(total_victories)}
{Messages.VICTORY_FOLLOWERS_SILENCED.format(Formatters.escape_markdown(Formatters.format_number(followers_silenced)))}

━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if latest:
            # Get target details
            target_result = await session.execute(
                select(InstagramTarget).where(InstagramTarget.id == latest.target_id)
            )
            target = target_result.scalar_one_or_none()
            
            if target:
                message += Formatters.format_victory_card(latest, target)
        else:
            message += "\n_هنوز پیروزی ثبت نشده است\\._"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.victories_actions()
        )


async def view_all_victories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all victories list."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(Victory)
            .order_by(Victory.victory_date.desc())
            .limit(10)
        )
        victories = result.scalars().all()
        
        message = f"{Messages.VICTORIES_HEADER}\n\n"
        
        for victory in victories:
            target_result = await session.execute(
                select(InstagramTarget).where(InstagramTarget.id == victory.target_id)
            )
            target = target_result.scalar_one_or_none()
            
            if target:
                date = victory.victory_date.strftime("%Y/%m/%d")
                message += f"✅ @{Formatters.escape_markdown(target.ig_handle)} \\- {Formatters.escape_markdown(date)}\n"
        
        if not victories:
            message += "_هنوز پیروزی ثبت نشده است\\._"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
        )


async def celebrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show celebration message."""
    query = update.callback_query
    await query.answer("🎉🎊🔥 تبریک! 🔥🎊🎉", show_alert=True)


# Export handlers
victories_handlers = [
    CallbackQueryHandler(show_victories, pattern=f"^{CallbackData.MENU_VICTORIES}$"),
    CallbackQueryHandler(view_all_victories, pattern=f"^{CallbackData.VICTORIES_ALL}$"),
    CallbackQueryHandler(celebrate, pattern=f"^{CallbackData.VICTORIES_CELEBRATE}$"),
]
