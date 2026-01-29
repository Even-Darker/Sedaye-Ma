"""
Admin statistics dashboard handlers for Sedaye Ma bot.
Provides insights into community growth, engagement, and mission impact.
"""
import logging
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func
from telegram import Update
from telegram.ext import ContextTypes

from src.database import (
    get_db, User, InstagramTarget, Victory, SolidarityMessage, 
    Petition, EmailCampaign, TargetStatus, PetitionStatus
)
from src.utils.decorators import admin_required
from src.utils import Keyboards, Formatters

logger = logging.getLogger(__name__)

def generate_progress_bar(percentage: int, length: int = 10) -> str:
    """Generate a unicode progress bar."""
    filled = int(length * percentage / 100)
    return "█" * filled + "░" * (length - filled)

@admin_required
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and show the stats dashboard."""
    now = datetime.now(UTC).replace(tzinfo=None) # naive for DB compatibility
    
    async with get_db() as session:
        # --- 1. User Demographics ---
        total_users = (await session.execute(select(func.count(User.id)))).scalar()
        
        dau = (await session.execute(
            select(func.count(User.id)).where(User.last_seen >= now - timedelta(days=1))
        )).scalar()
        
        wau = (await session.execute(
            select(func.count(User.id)).where(User.last_seen >= now - timedelta(days=7))
        )).scalar()
        
        mau = (await session.execute(
            select(func.count(User.id)).where(User.last_seen >= now - timedelta(days=30))
        )).scalar()
        
        # --- 2. Mission Impact ---
        victories = (await session.execute(select(func.count(Victory.id)))).scalar()
        active_targets = (await session.execute(
            select(func.count(InstagramTarget.id)).where(InstagramTarget.status != TargetStatus.REMOVED)
        )).scalar()
        
        total_strikes = (await session.execute(
            select(func.sum(InstagramTarget.anonymous_report_count))
        )).scalar() or 0
        
        success_rate = (victories / (victories + active_targets) * 100) if (victories + active_targets) > 0 else 0
        
        # --- 3. Blocked Users ---
        total_blocked = (await session.execute(
            select(func.count(User.id)).where(User.is_blocked_by_user == True)
        )).scalar() or 0

        # --- 4. Petitions ---
        total_petitions = (await session.execute(select(func.count(Petition.id)))).scalar() or 0
        active_petitions = (await session.execute(
            select(func.count(Petition.id)).where(Petition.status == PetitionStatus.ACTIVE)
        )).scalar() or 0
        total_signatures = (await session.execute(select(func.sum(Petition.signatures_current)))).scalar() or 0
        top_petition = (await session.execute(
            select(Petition).order_by(Petition.signatures_current.desc()).limit(1)
        )).scalar()

        # --- 5. Email Campaigns ---
        total_campaigns = (await session.execute(select(func.count(EmailCampaign.id)))).scalar() or 0
        total_email_actions = (await session.execute(select(func.sum(EmailCampaign.action_count)))).scalar() or 0
        top_campaign = (await session.execute(
            select(EmailCampaign).order_by(EmailCampaign.action_count.desc()).limit(1)
        )).scalar()
        
    # --- Calculations ---
    dau_perc = (dau / total_users * 100) if total_users > 0 else 0
    wau_perc = (wau / total_users * 100) if total_users > 0 else 0
    
    # --- UI Formatting ---
    # Helper to escape for MarkdownV2
    esc = Formatters.escape_markdown
    
    msg = (
        "🛡 *پیشخوان آماری صدای ما*\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        
        "👥 *ارتش مردمی*\n"
        f"• تعداد کل: `{esc(f'{total_users:,}')}`\n"
        f"• فعال \\(۲۴ ساعت\\): `{esc(f'{dau:,}')}`  `{generate_progress_bar(dau_perc)}` `{esc(f'{dau_perc:.1f}')}%`\n"
        f"• فعال \\(۷ روز\\): `{esc(f'{wau:,}')}`  `{generate_progress_bar(wau_perc)}` `{esc(f'{wau_perc:.1f}')}%`\n"
        f"• فعال \\(ماهانه\\): `{esc(f'{mau:,}')}`\n"
        f"• 🚫 مسدود‌کنندگان: `{esc(f'{total_blocked:,}')}`\n\n"
        
        "⚔️ *تاثیرگذاری*\n"
        f"• پیروزی‌ها: `{esc(f'{victories:,}')} 🏆`\n"
        f"• ضربات گزارش: `{esc(f'{total_strikes:,}')} 💥`\n"
        f"• درصد موفقیت: `{esc(f'{success_rate:.1f}')}%`\n"
        f"•🧃  ساندیسی فعال: `{esc(f'{active_targets:,}')}`\n\n"
        
        "📣 *پتیشن‌ها*\n"
        f"• تعداد کل: `{esc(f'{total_petitions:,}')}`\n"
        f"• در جریان: `{esc(f'{active_petitions:,}')}`\n"
        f"• مجموع امضاها: `{esc(f'{total_signatures:,}')}`\n"
        + (f"• برترین: `{esc(top_petition.title)}` \\({esc(f'{top_petition.signatures_current:,}')}\\)\n" if top_petition else "")
        + "\n"
        
        "📧 *ایمیل‌ها*\n"
        f"• تعداد کل: `{esc(f'{total_campaigns:,}')}`\n"
        f"• مجموع ارسال‌ها: `{esc(f'{total_email_actions:,}')}`\n"
        + (f"• برترین: `{esc(top_campaign.title)}` \\({esc(f'{top_campaign.action_count:,}')}\\)\n" if top_campaign else "")
        + "\n"
        
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"📅 _تاریخ گزارش: {esc(now.strftime('%Y-%m-%d %H:%M'))}_"
    )

    # --- Shareable Version (without backticks/complex formatting for external apps) ---
    share_msg = (
        "🛡 *پیشخوان آماری صدای ما*\n\n"
        "👥 *ارتش مردمی*\n"
        f"• تعداد کل: {total_users:,}\n"
        f"• فعال (۲۴ ساعت): {dau:,}\n"
        f"• فعال (۷ روز): {wau:,}\n\n"
        "⚔️ *تاثیرگذاری*\n"
        f"• پیروزی‌ها: {victories:,} 🏆\n"
        f"• ضربات گزارش: {total_strikes:,} 💥\n"
        f"• ساندیسی فعال: {active_targets:,} 🧃\n\n"
        "✌️ برای پیوستن به ارتش صدای ما:\n"
        "🔗 @Sedaye_Ma_Bot"
    )

    # Use reply_text for /stat command
    await update.message.reply_text(
        msg, 
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.stats_share_menu(share_msg)
    )
