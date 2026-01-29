"""
Petitions handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, Petition
from src.database.models import PetitionStatus


from sqlalchemy import func

async def show_petitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active petitions (page 0)."""
    await render_petition_page(update, context, offset=0)


async def navigate_petitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle petition navigation."""
    query = update.callback_query
    await query.answer()
    
    offset = int(query.data.split(":")[-1])
    await render_petition_page(update, context, offset=offset)


async def render_petition_page(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int):
    """Render a specific petition page."""
    query = update.callback_query
    
    async with get_db() as session:
        # Get total count
        count_query = select(func.count()).where(Petition.status == PetitionStatus.ACTIVE)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        if total == 0:
            text = f"{Messages.PETITIONS_HEADER}\n{Messages.PETITIONS_SUBTITLE}\n\n{Messages.PETITIONS_EMPTY}"
            if query:
                await query.edit_message_text(text, parse_mode="MarkdownV2")
            else:
                await update.message.reply_text(text, parse_mode="MarkdownV2")
            return

        # Validate offset
        if offset < 0: offset = 0
        if offset >= total: offset = total - 1
            
        # Get petition at offset
        result = await session.execute(
            select(Petition)
            .where(Petition.status == PetitionStatus.ACTIVE)
            .order_by(Petition.created_at.desc())
            .offset(offset)
            .limit(1)
        )
        petition = result.scalar_one_or_none()
        
        if not petition:
            # Should not happen if total > 0
            return
            
        # Format message with Total count header
        # We inject the count into the card or header
        header = f"{Messages.PETITIONS_HEADER} \\({total}\\)"
        
        card_content = Formatters.format_petition_card(petition)
        # Replace the first line of card (header) if needed, or just prepend
        # Formatters.format_petition_card starts with title.
        # Let's prepend the main header.
        
        message = f"{header}\n{card_content}\n{Messages.PETITIONS_HELP_FOOTER}"
        
        keyboard = Keyboards.petition_actions(petition.id, petition.url, offset, total)
        
        if query and query.message:
            try:
                await query.edit_message_text(
                    message,
                    parse_mode="MarkdownV2",
                    reply_markup=keyboard
                )
            except Exception:
                # content same
                pass
        else:
            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=keyboard
            )


async def view_petition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a specific petition."""
    query = update.callback_query
    await query.answer()
    
    petition_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(Petition).where(Petition.id == petition_id)
        )
        petition = result.scalar_one_or_none()
        
        if not petition:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        message = f"{Formatters.format_petition_card(petition)}\n{Messages.PETITIONS_HELP_FOOTER}"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.petition_actions(petition.id, petition.url)
        )


async def sign_petition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle petition click (tracking).
    NOTE: usage deprecated in favor of direct URL button for better reliability.
    """
    query = update.callback_query
    await query.answer()
    # Tracking logic removed as we use direct URL buttons now


async def handle_petition_share_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sharing options for a petition."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    petition_id = int(parts[2])
    offset = int(parts[3])
    
    async with get_db() as session:
        result = await session.execute(select(Petition).where(Petition.id == petition_id))
        petition = result.scalar_one_or_none()
        
        if not petition:
            return
            
        share_text = Formatters.format_petition_share(petition)
        
        await query.edit_message_text(
            f"📤 *اشتراک‌گذاری پتیشن*\n\n{Formatters.escape_markdown(petition.title)}\n\n"
            "پلتفرم مورد نظر را برای اشتراک‌گذاری انتخاب کنید:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.petition_share_menu(petition.title, petition.url, share_text, petition.id, offset)
        )


async def handle_petition_share_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show instructions for sharing on IG Story."""
    query = update.callback_query
    await query.answer()
    
    petition_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(select(Petition).where(Petition.id == petition_id))
        petition = result.scalar_one_or_none()
        
        if not petition:
            return
            
        share_text = Formatters.format_petition_share(petition)
        
        instructions = (
            "📸 *آموزش اشتراک در استوری اینستاگرام*\n\n"
            "۱\\. متن زیر را کپی کنید:\n\n"
            f"```\n{share_text}\n```\n\n"
            "۲\\. اپلیکیشن اینستاگرام را باز کنید\\.\n"
            "۳\\. عکس یا ویدیوی مورد نظر را انتخاب کنید\\.\n"
            "۴\\. از قسمت استیکرها، گزینه *LINK* را انتخاب کرده و لینک زیر را قرار دهید:\n"
            f"🔗 `{petition.url}`\n\n"
            "۵\\. متن کپی شده را به عنوان استیکر متنی یا کپشن اضافه کنید\\."
        )
        
        # We send this as a new message so the user can easily copy and keep it open
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=instructions,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main() # Or just let them be
        )


async def back_to_petition_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to petition detail from share options."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    offset = int(parts[-1])
    
    await render_petition_page(update, context, offset=offset)


# Export handlers
petitions_handlers = [
    CallbackQueryHandler(show_petitions, pattern=f"^{CallbackData.MENU_PETITIONS}$"),
    CallbackQueryHandler(navigate_petitions, pattern=r"^petition:nav:\d+$"),
    CallbackQueryHandler(view_petition, pattern=r"^petition:view:\d+$"),
    CallbackQueryHandler(sign_petition, pattern=r"^petition:sign:\d+$"),
    CallbackQueryHandler(handle_petition_share_options, pattern=r"^petition:share_opt:\d+:\d+$"),
    CallbackQueryHandler(handle_petition_share_ig, pattern=r"^petition:share_ig:\d+$"),
    CallbackQueryHandler(back_to_petition_view, pattern=r"^petition:view_back:\d+:\d+$"),
]
