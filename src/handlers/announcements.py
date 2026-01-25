"""
Announcements handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, Announcement


async def show_announcements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show announcements list."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        # Get active announcements, pinned first
        result = await session.execute(
            select(Announcement)
            .where(Announcement.is_active == True)
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
            .limit(5)
        )
        announcements = result.scalars().all()
        
        if not announcements:
            await query.edit_message_text(
                f"{Messages.ANNOUNCEMENTS_HEADER}\n\n{Messages.ANNOUNCEMENTS_EMPTY}",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_main()
            )
            return
        
        # Show the latest announcement
        announcement = announcements[0]
        message = Formatters.format_announcement(announcement)
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.announcement_reactions(
                announcement.id,
                fire=announcement.reaction_fire,
                heart=announcement.reaction_heart,
                fist=announcement.reaction_fist
            )
        )


async def react_to_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reaction to announcement."""
    query = update.callback_query
    
    # Parse callback data: announce:react:{id}:{emoji}
    parts = query.data.split(":")
    announcement_id = int(parts[2])
    emoji = parts[3]
    
    async with get_db() as session:
        result = await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()
        
        if not announcement:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        # Increment reaction (anonymous!)
        if emoji == "fire":
            announcement.reaction_fire += 1
        elif emoji == "heart":
            announcement.reaction_heart += 1
        elif emoji == "fist":
            announcement.reaction_fist += 1
        
        await session.commit()
        
        await query.answer("❤️")
        
        # Update keyboard with new counts
        await query.edit_message_reply_markup(
            reply_markup=Keyboards.announcement_reactions(
                announcement.id,
                fire=announcement.reaction_fire,
                heart=announcement.reaction_heart,
                fist=announcement.reaction_fist
            )
        )


# Export handlers
announcements_handlers = [
    CallbackQueryHandler(show_announcements, pattern=f"^{CallbackData.MENU_ANNOUNCEMENTS}$"),
    CallbackQueryHandler(react_to_announcement, pattern=r"^announce:react:\d+:\w+$"),
]
