"""
Text menu handlers for Sedaye Ma bot.
Routes text messages from persistent reply keyboard to appropriate handlers.
"""
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config import Messages
from src.handlers import (
    instagram,
    announcements,
    petitions,
    solidarity,
    resources,
    settings,
    admin
)


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from persistent menu."""
    text = update.message.text
    
    if text == Messages.MENU_TARGETS:
        await instagram.show_report_sandisi_menu(update, context)
        
    elif text == Messages.MENU_ANNOUNCEMENTS:
        await announcements.show_announcements(update, context)
        
    elif text == Messages.MENU_PETITIONS:
        await petitions.show_petitions(update, context)
        
    elif text == Messages.MENU_SOLIDARITY:
        await solidarity.show_solidarity(update, context)
        
    elif text == Messages.MENU_RESOURCES:
        await resources.show_resources(update, context)
        
    elif text == Messages.MENU_SETTINGS:
        await settings.show_settings(update, context)
        
    elif text == Messages.ADMIN_HEADER:
        # Check if actually admin
        if update.effective_user.id in settings.super_admin_ids: # Basic check, or use helper
             await admin.admin_panel(update, context)

# Export handler
text_menu_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_menu_text
)
