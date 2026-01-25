"""
Solidarity Wall handlers for Sedaye Ma bot.
Anonymous messages of support from the community.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, SolidarityMessage
from sqlalchemy import select
import random


# Conversation states
WRITING_MESSAGE = 1


async def show_solidarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show solidarity wall with random messages."""
    query = update.callback_query
    if query:
        await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(SolidarityMessage)
            .where(SolidarityMessage.is_approved == True)
        )
        all_messages = result.scalars().all()
        
        message = f"{Messages.SOLIDARITY_HEADER}\n{Messages.SOLIDARITY_SUBTITLE}\n\n"
        
        if all_messages:
            # Show random 3 messages
            display_messages = random.sample(all_messages, min(3, len(all_messages)))
            
            for msg in display_messages:
                message += f"{Formatters.format_solidarity_message(msg)}\n\n"
        else:
            message += "_هنوز پیامی ثبت نشده است\\._"
        
        if query:
            await query.edit_message_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.solidarity_actions()
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=Keyboards.solidarity_actions()
            )


async def load_more_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load more random solidarity messages."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(SolidarityMessage)
            .where(SolidarityMessage.is_approved == True)
        )
        all_messages = result.scalars().all()
        
        message = f"{Messages.SOLIDARITY_HEADER}\n{Messages.SOLIDARITY_SUBTITLE}\n\n"
        
        if all_messages:
            display_messages = random.sample(all_messages, min(3, len(all_messages)))
            
            for msg in display_messages:
                message += f"{Formatters.format_solidarity_message(msg)}\n\n"
        else:
            message += "_هنوز پیامی ثبت نشده است\\._"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.solidarity_actions()
        )


async def start_write_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start writing a solidarity message."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        Messages.SOLIDARITY_PROMPT,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )
    
    return WRITING_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and save solidarity message."""
    from src.utils.validators import Validators
    from src.utils import Formatters
    
    user_message = update.message.text
    
    # Validate message
    is_valid, sanitized_message, error = Validators.validate_solidarity_message(user_message)
    
    if not is_valid:
        error_msg = error or "پیام نامعتبر است"
        await update.message.reply_text(
            f"⚠️ *خطا*\n\n{Formatters.escape_markdown(error_msg)}\n\n"
            f"لطفاً پیام خود را اصلاح کنید \\(بین ۱۰ تا ۵۰۰ حرف، بدون لینک\\):",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
        )
        return WRITING_MESSAGE
    
    # Save anonymously
    async with get_db() as session:
        solidarity_msg = SolidarityMessage(
            message=sanitized_message,
            location=None,  # Could extract from message if user includes it
            is_approved=False  # Requires admin approval
        )
        session.add(solidarity_msg)
        await session.commit()
    
    await update.message.reply_text(
        Messages.SOLIDARITY_SUBMITTED,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )
    
    return ConversationHandler.END


async def cancel_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel writing message."""
    from src.handlers.menu import back_to_main
    
    # Navigate back to main menu
    await back_to_main(update, context)
    
    return ConversationHandler.END


# Solidarity conversation handler
solidarity_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_write_message, pattern=f"^{CallbackData.SOLIDARITY_WRITE}$")
    ],
    states={
        WRITING_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message),
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_write, pattern=f"^{CallbackData.BACK_MAIN}$"),
    ],
    per_message=False,
)


# Export handlers
solidarity_handlers = [
    CallbackQueryHandler(show_solidarity, pattern=f"^{CallbackData.MENU_SOLIDARITY}$"),
    CallbackQueryHandler(load_more_messages, pattern=f"^{CallbackData.SOLIDARITY_MORE}$"),
    solidarity_conversation,
]
