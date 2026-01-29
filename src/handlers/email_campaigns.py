from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.connection import get_db
from src.database.models import EmailCampaign, UserEmailAction
from src.utils.keyboards import CallbackData, Keyboards
from src.utils.formatters import Formatters
from config import Messages
from sqlalchemy import select
import hashlib
import logging

logger = logging.getLogger(__name__)



from src.database.models import User
from src.utils.security import encrypt_id

async def get_user_encrypted_id(session, user_id: int) -> str:
    """Get canonical encrypted ID for user."""
    enc_id = encrypt_id(user_id)
    # User stores encrypted_chat_id directly. If user not in DB, we can still use this ID.
    # But checking DB confirms registration.
    res = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
    user = res.scalar_one_or_none()
    
    # If user not found, use generated enc_id anyway (it's deterministic)
    return enc_id


async def get_user_completed_campaign_ids(session, enc_id: str) -> set:
    """Get set of campaign IDs the user has completed."""
    if not enc_id: return set()
    stmt = select(UserEmailAction.campaign_id).where(UserEmailAction.encrypted_user_id == enc_id)
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}


def build_single_campaign_message(campaign, page: int, total_pages: int, completed_ids: set) -> tuple:
    """Build message text and keyboard for single campaign view."""
    
    # Check if done
    is_done = campaign.id in completed_ids
    done_badge = "✅ شما قبلا این کمپین را انجام داده اید" if is_done else ""
    
    # Title and description
    title = Formatters.escape_markdown(campaign.title)
    desc = Formatters.escape_markdown(campaign.description)
    
    # Stats
    action_text = f"📨 تعداد ارسال ها: {campaign.action_count}"
    stats_line = f"_{action_text}_"
    
    # Email target for fallback copy
    email_target = Formatters.escape_markdown(campaign.receiver_email)
    is_valid_email = "@" in campaign.receiver_email and "." in campaign.receiver_email
    
    lines = [f"{Messages.EMAILS_HEADER}"]
    if done_badge:
        lines.append(f"_{done_badge}_")
        
    lines.append(f"\n*کمپین: \n{title}*\n")
    lines.append(f"توضیحات: \n{desc}\n")
    lines.append(f"{stats_line}")

    
    # Buttons
    buttons = []
    
    # Row 1: Send Action (Direct Link to bypass callback limitations)
    if is_valid_email:
        # Link to redirector
        url = campaign.redirect_link
        buttons.append([
            InlineKeyboardButton("📤 ارسال ایمیل", url=url)
        ])
    else:
        # Fallback if email invalid format (rare) - Show Alert
        buttons.append([
            InlineKeyboardButton(" ارسال ایمیل", callback_data=f"email:invalid:{campaign.id}")
        ])

    # Row 2: Confirmation / Copy
    row2 = []
    if not is_done:
        row2.append(InlineKeyboardButton("✅ انجام دادم", callback_data=CallbackData.EMAIL_ACTION_DONE.format(id=campaign.id, page=page)))
    
    buttons.append(row2)
    
    # Row 3: Navigation
    nav_buttons = []
    
    # Previous
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=CallbackData.EMAILS_PAGE.format(page=page-1)))
        
    # Page Indicator
    nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    
    # Next
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=CallbackData.EMAILS_PAGE.format(page=page+1)))
        
    buttons.append(nav_buttons)
    
    message = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(buttons)
    
    return message, keyboard


async def list_email_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active email campaigns (One per page)."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Parse page
    page = 0
    if query.data.startswith("emails:page:"):
        try:
            page = int(query.data.split(":")[-1])
        except ValueError:
            page = 0
            
    limit = 1
    offset = page * limit
    
    async with get_db() as session:
        enc_id = await get_user_encrypted_id(session, user_id)
        completed_ids = await get_user_completed_campaign_ids(session, enc_id)
        
        # Count total
        count_stmt = select(EmailCampaign).where(EmailCampaign.is_active == True)
        total_count = len((await session.execute(count_stmt)).scalars().all())
        # Calc total pages
        if total_count == 0:
            total_pages = 1
        else:
            total_pages = (total_count + limit - 1) // limit # Ceiling division
        
        # Validate page range
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
            
        offset = page * limit # Recalculate offset after validation
        
        # Get page item
        stmt = (
            select(EmailCampaign)
            .outerjoin(UserEmailAction, (EmailCampaign.id == UserEmailAction.campaign_id) & (UserEmailAction.encrypted_user_id == enc_id))
            .where(EmailCampaign.is_active == True)
            .order_by(UserEmailAction.id.isnot(None), EmailCampaign.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        campaigns = (await session.execute(stmt)).scalars().all()
        
        if not campaigns:
            await query.edit_message_text(
                f"{Messages.EMAILS_HEADER}\n\n{Messages.EMAILS_EMPTY}",
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.back_to_main()
            )
            return

        message, keyboard = build_single_campaign_message(campaigns[0], page, total_pages, completed_ids)
        
        # Fix: Ensure message is different or suppress error
        try:
            await query.edit_message_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=keyboard
            )
        except Exception as e:
            # Message is not modified error is common if clicking same nav button
            logger.warning(f"Message edit update failed (likely no change): {e}")


async def list_email_campaigns_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List email campaigns from text menu."""
    user_id = update.effective_user.id
    
    limit = 1
    
    async with get_db() as session:
        enc_id = await get_user_encrypted_id(session, user_id)
        completed_ids = await get_user_completed_campaign_ids(session, enc_id)
        
        count_stmt = select(EmailCampaign).where(EmailCampaign.is_active == True)
        total_count = len((await session.execute(count_stmt)).scalars().all())
        total_pages = max(1, (total_count + limit - 1) // limit)
        
        stmt = (
            select(EmailCampaign)
            .outerjoin(UserEmailAction, (EmailCampaign.id == UserEmailAction.campaign_id) & (UserEmailAction.encrypted_user_id == enc_id))
            .where(EmailCampaign.is_active == True)
            .order_by(UserEmailAction.id.isnot(None), EmailCampaign.created_at.desc())
            .limit(limit)
        )
        campaigns = (await session.execute(stmt)).scalars().all()
        
        if not campaigns:
            await update.message.reply_text(
                f"{Messages.EMAILS_HEADER}\n\n{Messages.EMAILS_EMPTY}",
                parse_mode="MarkdownV2"
            )
            return

        message, keyboard = build_single_campaign_message(campaigns[0], 0, total_pages, completed_ids)
        
        await update.message.reply_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )


async def track_email_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track 'I did it' action."""
    query = update.callback_query
    
    # Parse id and page: email:done:ID:PAGE
    parts = query.data.split(":")
    campaign_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0
    
    user_id = update.effective_user.id
    
    async with get_db() as session:
        enc_id = await get_user_encrypted_id(session, user_id)
        if not enc_id:
             enc_id = encrypt_id(user_id) # Fallback if user somehow not in DB

        # Check if already acted
        stmt = select(UserEmailAction).where(
            UserEmailAction.campaign_id == campaign_id,
            UserEmailAction.encrypted_user_id == enc_id
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        
        if existing:
            await query.answer("قبلاً ثبت شده!", show_alert=True)
            return
            
        # Record action
        action = UserEmailAction(campaign_id=campaign_id, encrypted_user_id=enc_id)
        session.add(action)
        
        campaign_result = await session.execute(
            select(EmailCampaign).where(EmailCampaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            if campaign.action_count is None:
                campaign.action_count = 0
            campaign.action_count += 1
            
        await session.commit()
        
    await query.answer("ممنون! ثبت شد.", show_alert=True)
    
    # Refresh UI
    try:
        async with get_db() as session:
            # Re-fetch everything to ensure fresh state
            completed_ids = await get_user_completed_campaign_ids(session, enc_id)
            
            limit = 1
            # Recalculate total pages/offset logic as in list function
            count_stmt = select(EmailCampaign).where(EmailCampaign.is_active == True)
            total_count = len((await session.execute(count_stmt)).scalars().all())
            total_pages = max(1, (total_count + limit - 1) // limit)
            
            if page >= total_pages: page = total_pages - 1
            if page < 0: page = 0
            offset = page * limit
            
            stmt = (
                select(EmailCampaign)
                .outerjoin(UserEmailAction, (EmailCampaign.id == UserEmailAction.campaign_id) & (UserEmailAction.encrypted_user_id == enc_id))
                .where(EmailCampaign.is_active == True)
                .order_by(UserEmailAction.id.isnot(None), EmailCampaign.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            campaigns = (await session.execute(stmt)).scalars().all()
            
            if campaigns:
                message, keyboard = build_single_campaign_message(campaigns[0], page, total_pages, completed_ids)
                await query.edit_message_text(
                    message,
                    parse_mode="MarkdownV2",
                    reply_markup=keyboard
                )
    except Exception as e:
        logger.error(f"Error refreshing view after action: {e}")


async def show_email_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show email details copyable."""
    query = update.callback_query
    campaign_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(EmailCampaign).where(EmailCampaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            await query.answer("Not found", show_alert=True)
            return
        
        await query.answer()
        await query.message.reply_text(
            f"📋 *اطلاعات کپی:*\n\n"
            f"📬: `{Formatters.escape_markdown(campaign.receiver_email)}`\n\n"
            f"📌: `{Formatters.escape_markdown(campaign.subject)}`\n\n"
            f"📝: ```\n{Formatters.escape_markdown(campaign.body[:800])}\n```",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("حذف پیام", callback_data="delete_message")]
            ])
        )


async def show_invalid_email_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show alert for invalid email format."""
    query = update.callback_query
    await query.answer("❌ خطا: فرمت ایمیل تعریف شده برای این کمپین صحیح نیست.", show_alert=True)

