from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from src.database.connection import get_db
from src.database.models import EmailCampaign, Admin
from src.utils.keyboards import Keyboards, CallbackData
from src.utils.decorators import admin_required
from config import Messages
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

# States for adding email campaign
(
    ADDING_EMAIL_TITLE,
    ADDING_EMAIL_DESC,
    ADDING_EMAIL_RECEIVER,
    ADDING_EMAIL_SUBJECT,
    ADDING_EMAIL_BODY
) = range(5)

@admin_required
async def manage_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active email campaigns for management (delete)."""
    query = update.callback_query
    await query.answer()

    # Parse page
    page = 0
    if ":" in query.data and query.data.split(":")[-1].isdigit():
        page = int(query.data.split(":")[-1])

    limit = 5
    offset = page * limit

    async with get_db() as session:
        # Count total
        count_stmt = select(EmailCampaign).where(EmailCampaign.is_active == True)
        total_count = len((await session.execute(count_stmt)).scalars().all())
        total_pages = (total_count + limit - 1) // limit

        result = await session.execute(
            select(EmailCampaign)
            .where(EmailCampaign.is_active == True)
            .order_by(EmailCampaign.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        campaigns = result.scalars().all()

        if not campaigns and page == 0:
            await query.edit_message_text(
                "📧 *مدیریت ایمیل‌ها*\n\nلیست ایمیل‌ها خالی است\\.",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(Messages.ADMIN_ADD_EMAIL_BTN, callback_data=CallbackData.ADMIN_ADD_EMAIL)],
                    [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_PANEL)]
                ])
            )
            return

        await query.edit_message_text(
            f"📧 *مدیریت ایمیل‌ها* \(صفحه {page + 1} از {max(1, total_pages)}\)\n\nلیست کمپین‌های فعال:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_emails_list(campaigns, page, total_pages)
        )

@admin_required
async def view_email_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View details of an email campaign (Admin)."""
    query = update.callback_query
    campaign_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(EmailCampaign).where(EmailCampaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign or not campaign.is_active:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
            
        from src.utils.formatters import Formatters
        date_str = "N/A"
        if campaign.created_at:
            date_str = Formatters.escape_markdown(campaign.created_at.strftime('%Y-%m-%d %H:%M'))
            
        message = (
            f"📧 *{Formatters.escape_markdown(campaign.title)}*\n\n"
            f"📝 *توضیحات:*\n{Formatters.escape_markdown(campaign.description)}\n\n"
            f"📬 *گیرنده:* `{Formatters.escape_markdown(campaign.receiver_email)}`\n"
            f"📌 *موضوع:* `{Formatters.escape_markdown(campaign.subject)}`\n\n"
            f"✊ *تعداد ارسال‌ها:* {campaign.action_count}\n"
            f" *تاریخ ایجاد:* {date_str}"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.admin_email_view_actions(campaign.id)
        )

@admin_required
async def delete_email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete an email campaign."""
    query = update.callback_query
    email_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(EmailCampaign).where(EmailCampaign.id == email_id)
        )
        campaign = result.scalar_one_or_none()
        
        if campaign:
            campaign.is_active = False
            await session.commit()
            await query.answer("✅ ایمیل حذف شد")
        else:
            await query.answer("❌ یافت نشد", show_alert=True)
            
    await manage_emails(update, context)

@admin_required
async def start_add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new email campaign."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ *افزودن کمپین ایمیلی*\n\nلطفاً *عنوان کمپین* را وارد کنید:\n\(مثلاً: اعتراض به سازمان ملل\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.BACK_MAIN)]])
    )
    return ADDING_EMAIL_TITLE

async def receive_email_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_email_title"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 حالا *توضیحات* کمپین را وارد کنید:\n\(چرا باید این ایمیل ارسال شود؟\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.BACK_MAIN)]])
    )
    return ADDING_EMAIL_DESC

async def receive_email_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_email_desc"] = update.message.text.strip()
    await update.message.reply_text(
        "📬 آدرس *ایمیل گیرنده* را وارد کنید:\n\(مثلاً: info@un\.org\)",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.BACK_MAIN)]])
    )
    return ADDING_EMAIL_RECEIVER

async def receive_email_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_email_receiver"] = update.message.text.strip()
    await update.message.reply_text(
        "📌 *موضوع ایمیل \(Subject\)* را وارد کنید:",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.BACK_MAIN)]])
    )
    return ADDING_EMAIL_SUBJECT

async def receive_email_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_email_subject"] = update.message.text.strip()
    await update.message.reply_text(
        "📄 *متن ایمیل \(Body\)* را وارد کنید:",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.BACK_MAIN)]])
    )
    return ADDING_EMAIL_BODY

async def receive_email_body(update: Update, context: ContextTypes.DEFAULT_TYPE):
    body = update.message.text.strip()
    data = context.user_data
    
    async with get_db() as session:
        campaign = EmailCampaign(
            title=data["new_email_title"],
            description=data["new_email_desc"],
            receiver_email=data["new_email_receiver"],
            subject=data["new_email_subject"],
            body=body,
            created_by_admin_id=update.effective_user.id
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)

    # Broadcast Notification
    from src.services.notification_service import NotificationService
    service = NotificationService(context.bot)
    await service.broadcast_email_campaign(campaign)
        
    await update.message.reply_text(
        "✅ *کمپین ایمیلی با موفقیت ایجاد شد\!*",
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.admin_menu(is_super_admin=True) # Assuming admin is super for now or we check logic
    )
    return ConversationHandler.END

async def cancel_email_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("❌ عملیات لغو شد")
        # Call manage_emails to show the list again
        await manage_emails(update, context)
    return ConversationHandler.END

# Conversation Handler
add_email_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_email, pattern=f"^{CallbackData.ADMIN_ADD_EMAIL}$")],
    states={
        ADDING_EMAIL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email_title)],
        ADDING_EMAIL_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email_desc)],
        ADDING_EMAIL_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email_receiver)],
        ADDING_EMAIL_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email_subject)],
        ADDING_EMAIL_BODY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email_body)],
    },
    fallbacks=[CallbackQueryHandler(cancel_email_action, pattern=f"^{CallbackData.BACK_MAIN}$")],
    per_message=False
)
