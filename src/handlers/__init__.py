# src/handlers/__init__.py
from .start import start_handler, start_callback_handler
from .menu import menu_handlers
from .instagram import instagram_handlers
from .victories import victories_handlers
from .free_configs import free_configs_handlers
from .announcements import announcements_handlers
from .petitions import petitions_handlers
from .solidarity import solidarity_handlers
from .resources import resources_handlers
from .settings import settings_handlers
from .admin import admin_handlers
from .suggest import suggest_handlers
from .text_menu import text_menu_handler
from .removal import report_removal_conversation

from .email_campaigns import list_email_campaigns, track_email_action, show_email_details, show_invalid_email_alert
from telegram.ext import CallbackQueryHandler
from src.utils.keyboards import CallbackData

email_campaign_handlers = [
    CallbackQueryHandler(list_email_campaigns, pattern=f"^{CallbackData.MENU_EMAILS}$"),
    CallbackQueryHandler(list_email_campaigns, pattern="^emails:page:"),
    CallbackQueryHandler(show_email_details, pattern="^email:show:"),
    CallbackQueryHandler(show_invalid_email_alert, pattern="^email:invalid:"),
    CallbackQueryHandler(track_email_action, pattern="^email:done:"),
]




__all__ = [
    'start_handler',
    'start_callback_handler',
    'menu_handlers',
    'instagram_handlers',
    'victories_handlers',
    'free_configs_handlers',
    'announcements_handlers',
    'petitions_handlers',
    'solidarity_handlers',
    'resources_handlers',
    'settings_handlers',
    'admin_handlers',
    'suggest_handlers',
    'text_menu_handler',
    'report_removal_conversation',
    'email_campaign_handlers',
]

