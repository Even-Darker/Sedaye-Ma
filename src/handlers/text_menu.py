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
    import time
    
    text = update.message.text
    current_time = time.time()
    
    # Debounce check: Ignore identical messages within 2 seconds
    last_text = context.user_data.get('last_msg_text')
    last_time = context.user_data.get('last_msg_time', 0)
    
    if text == last_text and (current_time - last_time) < 2.0:
        return

    # Update cache
    context.user_data['last_msg_text'] = text
    context.user_data['last_msg_time'] = current_time
    
    if text == Messages.MENU_TARGETS or "ریپورت ساندیسی" in text:
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
        # Let the admin_panel handler decide access (it has @admin_required)
        await admin.admin_panel(update, context)

# Export handler
text_menu_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_menu_text
)
