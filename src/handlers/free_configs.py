"""
Free Configs Handler
Allows users to view free VPN configs posted by admins.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy import select

from src.database.models import FreeConfig, UserConfigReport, User
from src.database.connection import get_db
from config.messages_fa import Messages
from src.utils.keyboards import Keyboards, CallbackData
from src.utils.formatters import Formatters
from src.utils.security import encrypt_id


# Helper to get message function
def get_message_func(update: Update):
    if update.callback_query:
        return update.callback_query.edit_message_text
    return update.effective_message.reply_text


async def show_free_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active free configs (paginated)."""
    # Parse page number
    page = 0
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data.startswith("configs:page:"):
            page = int(query.data.split(":")[-1])
            
    message_func = get_message_func(update)

    async with get_db() as session:
        # Get total count first
        # Note: In a real app we'd cache this or use count(*), but for list len() is okay for small sets
        result = await session.execute(
            select(FreeConfig)
            .where(FreeConfig.is_active == True)
            .order_by(FreeConfig.report_count.asc(), FreeConfig.created_at.desc())
        )
        all_configs = result.scalars().all()
        
        if not all_configs:
            text = f"{Messages.FREE_CONFIGS_HEADER}\n\n{Messages.FREE_CONFIGS_EMPTY}"
            reply_markup = Keyboards.back_to_main()
            await message_func(text=text, parse_mode="MarkdownV2", reply_markup=reply_markup)
            return

        total_pages = len(all_configs)
        # Ensure page is valid
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
            
        config = all_configs[page]
        
        # Format single config
        text = f"{Messages.FREE_CONFIGS_HEADER}\n{Messages.FREE_CONFIGS_SUBTITLE}\n\n"
        
        desc = f" \\- {Formatters.escape_markdown(config.description)}" if config.description else ""
        # We show a truncated preview or just "Config #x" because the full config is long and ugly
        # But user wants to see it. Let's show it in a code block.
        # But if it's huge, it might spam. Let's just show it.
        text += f"📡 *کانفیگ شماره {page + 1}*\n"
        text += f"{desc}\n\n"
        text += f"`{Formatters.escape_markdown(config.config_uri)}`\n\n"
        text += Messages.FREE_CONFIGS_INSTRUCTIONS

        reply_markup = Keyboards.free_configs_pagination(config.id, page, total_pages)
        
        await message_func(
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )


async def copy_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send config as a separate message for easy copying."""
    query = update.callback_query
    config_id = int(query.data.split(":")[-1])
    
    async with get_db() as session:
        result = await session.execute(
            select(FreeConfig).where(FreeConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if config:
            await query.answer("کپی شد! ✅")
            # Send as new message so user can long-press to copy easily
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"`{config.config_uri}`",
                parse_mode="MarkdownV2"
            )
        else:
            await query.answer("❌ کانفیگ یافت نشد", show_alert=True)




async def report_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Report a broken config."""
    query = update.callback_query
    config_id = int(query.data.split(":")[-1])
    user_id = update.effective_user.id
    
    enc_id = encrypt_id(user_id)
    
    async with get_db() as session:
        # Get User's Encrypted ID (Canonical)
        result = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
        user = result.scalar_one_or_none()
        
        # User already fetches by encrypted_chat_id, so if user exists, use that.
        # But we already have enc_id from the function call.
        # If user not found in DB, we should create? Or just use the enc_id for logging?
        # Logging only requires ID.
        pass
        
        # Check if already reported
        existing = await session.execute(
            select(UserConfigReport).where(
                UserConfigReport.config_id == config_id,
                UserConfigReport.encrypted_user_id == enc_id
            )
        )
        if existing.scalar_one_or_none():
            await query.answer("⚠️ شما قبلاً این کانفیگ را گزارش کرده‌اید.", show_alert=True)
            return

        result = await session.execute(
            select(FreeConfig).where(FreeConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        
        if config:
            config.report_count += 1
            
            # Log the report
            report_log = UserConfigReport(config_id=config_id, encrypted_user_id=enc_id)
            session.add(report_log)
            
            await session.commit()
            await query.answer("✅ گزارش شما ثبت شد. بررسی می‌کنیم!", show_alert=True)
        else:
            await query.answer("❌ کانفیگ یافت نشد", show_alert=True)


# Export handlers
free_configs_handlers = [
    CallbackQueryHandler(show_free_configs, pattern=f"^{CallbackData.MENU_FREE_CONFIGS}$"),
    CallbackQueryHandler(show_free_configs, pattern=r"^configs:page:\d+$"),
    CallbackQueryHandler(copy_config, pattern=r"^config:copy:\d+$"),
    CallbackQueryHandler(report_config, pattern=r"^config:report:\d+$"),
    MessageHandler(filters.Regex(f"^{Messages.MENU_FREE_CONFIGS}$"), show_free_configs)
]
