"""
Notification service for Sedaye Ma bot.
Handles broadcasting announcements and victories.
"""
from typing import List
from telegram import Bot
from sqlalchemy import select

from src.database import get_db, NotificationPreference, Announcement, Victory, InstagramTarget
from src.database.models import AnnouncementCategory
from src.utils.formatters import Formatters


class NotificationService:
    """Service for sending notifications to opted-in users."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def broadcast_announcement(self, announcement: Announcement):
        """Broadcast an announcement to all opted-in users."""
        async with get_db() as session:
            # Get appropriate subscribers based on category
            if announcement.category == AnnouncementCategory.URGENT:
                result = await session.execute(
                    select(NotificationPreference)
                    .where(NotificationPreference.announcements_urgent == True)
                )
            else:
                result = await session.execute(
                    select(NotificationPreference)
                    .where(NotificationPreference.announcements_news == True)
                )
            
            subscribers = result.scalars().all()
            
            message = Formatters.format_announcement(announcement)
            
            sent_count = 0
            for pref in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=pref.chat_id,
                        text=message,
                        parse_mode="MarkdownV2"
                    )
                    sent_count += 1
                except Exception:
                    # User may have blocked the bot
                    pass
            
            return sent_count
    
    async def broadcast_victory(self, victory: Victory, target: InstagramTarget):
        """Broadcast a victory to all opted-in users."""
        async with get_db() as session:
            result = await session.execute(
                select(NotificationPreference)
                .where(NotificationPreference.victories == True)
            )
            subscribers = result.scalars().all()
            
            message = f"""
🏆🎉 *پیروزی جدید\\!* 🎉🏆

@{Formatters.escape_markdown(target.ig_handle)} حذف شد\\!

👥 {Formatters.escape_markdown(Formatters.format_number(target.followers_count))} فالوور ساکت شد
📊 {victory.final_report_count} گزارش از جامعه

صدای ما شنیده شد\\! ✊🔥
"""
            
            sent_count = 0
            for pref in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=pref.chat_id,
                        text=message,
                        parse_mode="MarkdownV2"
                    )
                    sent_count += 1
                except Exception:
                    pass
            
            return sent_count
    
    async def broadcast_petition(self, petition):
        """Broadcast a new petition to opted-in users."""
        async with get_db() as session:
            result = await session.execute(
                select(NotificationPreference)
                .where(NotificationPreference.petitions == True)
            )
            subscribers = result.scalars().all()
            
            message = Formatters.format_petition_card(petition)
            
            sent_count = 0
            for pref in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=pref.chat_id,
                        text=message,
                        parse_mode="MarkdownV2"
                    )
                    sent_count += 1
                except Exception:
                    pass
            
            return sent_count
            
    async def notify_admins_new_submission(self, count: int, handles: List[str]):
        """Notify all admins about new pending submissions."""
        from src.database.models import Admin
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        from src.utils.keyboards import CallbackData
        
        async with get_db() as session:
            result = await session.execute(select(Admin.telegram_id))
            admin_ids = result.scalars().all()
            
            preview = ", ".join([f"@{h}" for h in handles[:3]])
            if len(handles) > 3:
                preview += f" و {len(handles)-3} مورد دیگر"
            
            message = (
                f"🔔 *گزارش جدید ساندیسی*\n\n"
                f"👤 یک کاربر {count} صفحه جدید پیشنهاد داد:\n"
                f"`{Formatters.escape_markdown(preview)}`\n\n"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 بررسی موارد", callback_data=CallbackData.ADMIN_PENDING_TARGETS)]
            ])
            
            sent_count = 0
            for uid in admin_ids:
                try:
                    await self.bot.send_message(
                        chat_id=uid,
                        text=message,
                        parse_mode="MarkdownV2",
                        reply_markup=keyboard
                    )
                    sent_count += 1
                except Exception:
                    pass
            return sent_count
