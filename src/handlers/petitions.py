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


async def show_petitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active petitions."""
    query = update.callback_query
    if query:
        await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(Petition)
            .where(Petition.status == PetitionStatus.ACTIVE)
            .order_by(Petition.created_at.desc())
            .limit(5)
        )
        petitions = result.scalars().all()
        
        if not petitions:
            text = f"{Messages.PETITIONS_HEADER}\n{Messages.PETITIONS_SUBTITLE}\n\n{Messages.PETITIONS_EMPTY}"
            markup = Keyboards.back_to_main()
            if query:
                await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=markup)
            else:
                await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=markup)
            return
        
        # Show first petition
        petition = petitions[0]
        message = Formatters.format_petition_card(petition)
        
        if query:
            await query.edit_message_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.petition_actions(petition.id, petition.url)
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.petition_actions(petition.id, petition.url)
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
        
        message = Formatters.format_petition_card(petition)
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.petition_actions(petition.id, petition.url)
        )


# Export handlers
petitions_handlers = [
    CallbackQueryHandler(show_petitions, pattern=f"^{CallbackData.MENU_PETITIONS}$"),
    CallbackQueryHandler(view_petition, pattern=r"^petition:view:\d+$"),
]
