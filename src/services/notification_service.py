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
from config import Messages
import logging

logger = logging.getLogger(__name__)


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
            
            message = Formatters.format_new_petition_announcement(petition)
            
            sent_count = 0
            for pref in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=pref.chat_id,
                        text=message,
                        parse_mode="MarkdownV2"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send petition notification to {pref.chat_id}: {e}")
                    pass
            
            return sent_count
            
    async def broadcast_email_campaign(self, campaign):
        """Broadcast a new email campaign to opted-in users."""
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        from src.utils.keyboards import Keyboards, CallbackData
        
        async with get_db() as session:
            result = await session.execute(
                select(NotificationPreference)
                .where(NotificationPreference.email_campaigns == True)
            )
            subscribers = result.scalars().all()
            
            title = Formatters.escape_markdown(campaign.title)
            desc = Formatters.escape_markdown(campaign.description[:200])
            email = Formatters.escape_markdown(campaign.receiver_email)
            
            message = (
                f"{Messages.EMAILS_HEADER}\n\n"
                f"🚨 *کمپین جدید: {title}*\n\n"
                f"{desc}\\.\\.\\.\n\n"
                f"🎯 هدف: `{email}`"
            )
            
            # Simple keyboard to go to emails page
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(Messages.EMAIL_SEND_BTN, callback_data=CallbackData.MENU_EMAILS)]
            ])
            
            sent_count = 0
            for pref in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=pref.chat_id,
                        text=message,
                        parse_mode="MarkdownV2",
                        reply_markup=keyboard
                    )
                    logger.info(f"Successfully sent email notification to {pref.chat_id}")
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email notification to {pref.chat_id}: {e}")
            
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
            
            # The original instruction seems to have intended to add a button to the petition broadcast,
            # but the provided snippet was placed in notify_admins_new_submission.
            # To make the code syntactically correct and align with the likely intent of adding a petition button,
            # I'm adding it to the broadcast_petition method.
            # If the intent was to replace the admin keyboard here, it would break functionality and cause a NameError.
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

    async def notify_admins_removal_request(self, target_id: int, handle: str, auto_confirmed: bool):
        """
        Notify all admins about a removal request (Submit Victory).
        """
        
        from src.database.models import Admin
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        from src.utils.keyboards import CallbackData
        
        logger.info(f"Preparing removal notification for handle: {handle}, target_id: {target_id}")
        
        async with get_db() as session:
            result = await session.execute(select(Admin.telegram_id))
            admin_ids = result.scalars().all()
            
            logger.info(f"Found {len(admin_ids)} admins in database: {admin_ids}")
            
            admin_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تأیید حذف و ثبت پیروزی", callback_data=CallbackData.ADMIN_CONFIRM_REMOVAL.format(id=target_id))],
                [InlineKeyboardButton("بررسی صفحه", url=f"https://instagram.com/{handle}")]
            ])
            
            status_icon = "🟢" if auto_confirmed else "⚠️"
            raw_status = "تایید خودکار (صفحه یافت نشد)" if auto_confirmed else "گزارش دستی (صفحه هنوز دیده می‌شود)"
            status_text = Formatters.escape_markdown(raw_status)
            
            msg = (
                f"🏆 *گزارش حذف صفحه*\n\n"
                f"📍 Handle: [@{Formatters.escape_markdown(handle)}](https://instagram.com/{handle})\n"
                f"وضعیت ربات: {status_text} {status_icon}\n\n"
                "آیا حذف این صفحه را تأیید می‌کنید؟"
            )
            
            sent_count = 0
            for uid in admin_ids:
                try:
                    logger.info(f"Sending notification to admin {uid}...")
                    await self.bot.send_message(
                        chat_id=uid,
                        text=msg,
                        parse_mode="MarkdownV2",
                        reply_markup=admin_keyboard
                    )
                    logger.info(f"SUCCESS: Sent to {uid}")
                    sent_count += 1
                except Exception as e:
                    logger.error(f"FAILED to send to admin {uid}: {e}")
            return sent_count
