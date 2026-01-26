"""
Admin handlers for managing petitions.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, 
    MessageHandler, filters, CommandHandler
)
from sqlalchemy import select, func

from config import Messages
from src.database import get_db, Petition, Admin
from src.database.models import PetitionStatus
from src.utils import Keyboards
from src.utils.decorators import admin_required
from src.utils.keyboards import CallbackData
from src.handlers.text_menu import handle_menu_text

# Conversation states
ADD_PETITION_TITLE = 1
ADD_PETITION_URL = 2
ADD_PETITION_DESC = 3


@admin_required
async def manage_petitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show petitions management list."""
    query = update.callback_query
    if query:
        await query.answer()
        
    page = 1
    # Check for page number in callback data
    if query and query.data.startswith("admin:petitions:page:"):
        page = int(query.data.split(":")[-1])
        
    async with get_db() as session:
        # Get petitions (paginated 5 per page)
        limit = 5
        offset = (page - 1) * limit
        
        # Get entries
        stmt = (
            select(Petition)
            .where(Petition.status == PetitionStatus.ACTIVE)
            .order_by(Petition.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        petitions = (await session.execute(stmt)).scalars().all()
        
        # Count total
        count_stmt = select(func.count(Petition.id)).where(Petition.status == PetitionStatus.ACTIVE)
        total_count = (await session.execute(count_stmt)).scalar() or 0
        
        text = f"✊ *مدیریت پتیشن‌ها*\n\nتعداد کل: {total_count}\n\n"
        
        buttons = []
        
        if not petitions:
            text += "📭 هیچ پتیشن فعالی وجود ندارد."
        else:
            for p in petitions:
                # Format: Title [Link] <Delete>
                # Visits
                # Explanation
                
                text += (
                    f"📣 [{p.title}]({p.url})\n"
                    f"📝 {p.description[:100]}...\n\n"
                    f"👀 بازدید: {p.visit_count}\n"
                    f"🗑 حذف: /delete\\_petition\\_{p.id}\n"
                    f"➖ ➖ ➖ ➖ ➖\n\n"
                )
        
        # Navigation
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin:petitions:page:{page-1}")
            )
        if total_count > page * limit:
            nav_buttons.append(
                InlineKeyboardButton("بعدی ➡️", callback_data=f"admin:petitions:page:{page+1}")
            )
        if nav_buttons:
            buttons.append(nav_buttons)
            
        # Add New
        buttons.append([
            InlineKeyboardButton("➕ افزودن پتیشن جدید", callback_data="admin:add_petition")
        ])
        
        buttons.append([
            InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_PANEL)
        ])
        
        if query:
            await query.edit_message_text(
                text,
                parse_mode="Markdown", # Using Markdown, not V2 for simpler link handling here or mix
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )


@admin_required
async def start_add_petition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a new petition."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 *افزودن پتیشن جدید*\n\n"
        "لطفاً **عنوان** پتیشن را وارد کنید:",
        parse_mode="Markdown"
    )
    return ADD_PETITION_TITLE


@admin_required
async def receive_petition_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive title."""
    title = update.message.text
    context.user_data['new_petition_title'] = title
    
    await update.message.reply_text(
        "🔗 لطفاً **لینک (URL)** پتیشن را وارد کنید:",
        parse_mode="Markdown"
    )
    return ADD_PETITION_URL


@admin_required
async def receive_petition_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive URL."""
    url = update.message.text.strip()
    # Basic validation
    import re
    if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', url):
        await update.message.reply_text("❌ لینک نامعتبر است. لطفاً لینک صحیح وارد کنید (مانند https://example.com).")
        return ADD_PETITION_URL
        
    context.user_data['new_petition_url'] = url
    
    await update.message.reply_text(
        "📝 لطفاً **توضیحات کوتاه** پتیشن را وارد کنید:",
        parse_mode="Markdown"
    )
    return ADD_PETITION_DESC


@admin_required
async def receive_petition_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive description and save."""
    desc = update.message.text
    title = context.user_data['new_petition_title']
    url = context.user_data['new_petition_url']
    
    async with get_db() as session:
        new_petition = Petition(
            title=title,
            url=url,
            description=desc,
            status=PetitionStatus.ACTIVE
        )
        session.add(new_petition)
        await session.commit()
        await session.refresh(new_petition)
        
    # Broadcast notification
    from src.services.notification_service import NotificationService
    service = NotificationService(context.bot)
    await service.broadcast_petition(new_petition)
    
    await update.message.reply_text(
        f"✅ *پتیشن با موفقیت اضافه شد!*\n\n"
        f"📌 {title}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_PETITIONS)]
        ])
    )
    return ConversationHandler.END


@admin_required
async def cancel_add_petition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel operation."""
    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=Keyboards.admin_menu()
    )
    return ConversationHandler.END


@admin_required
async def delete_petition_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delete_petition_{id}."""
    text = update.message.text
    try:
        # Format: /delete_petition_123
        p_id = int(text.split("_")[-1])
        
        async with get_db() as session:
            petition = await session.get(Petition, p_id)
            if petition:
                await session.delete(petition)
                await session.commit()
                await update.message.reply_text(f"✅ پتیشن شماره {p_id} حذف شد.")
            else:
                await update.message.reply_text("❌ پتیشن یافت نشد.")
                
        # Redirect to list
        await manage_petitions(update, context)
        
    except Exception as e:
        await update.message.reply_text("خطا در حذف.")


# Filter for menu buttons to allow interruption
# Using filters.Text for exact matching key buttons
MenuFilter = filters.Text([
    Messages.MENU_TARGETS,
    Messages.MENU_ANNOUNCEMENTS,
    Messages.MENU_PETITIONS,
    Messages.MENU_SOLIDARITY,
    Messages.MENU_RESOURCES,
    Messages.MENU_SETTINGS,
    Messages.ADMIN_HEADER
])

async def check_menu_interruption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if message is a menu command, if so cancel and handle it."""
    # Logic is now handled by the filter and handler, just assume it matched
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=Keyboards.main_menu_persistent())
    await handle_menu_text(update, context)
    return ConversationHandler.END


# Conversation Handler
add_petition_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_petition, pattern="^admin:add_petition$")],
    states={
        ADD_PETITION_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~MenuFilter, receive_petition_title),
        ],
        ADD_PETITION_URL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~MenuFilter, receive_petition_url),
        ],
        ADD_PETITION_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~MenuFilter, receive_petition_desc),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_add_petition),
        MessageHandler(MenuFilter, check_menu_interruption)
    ]
)
