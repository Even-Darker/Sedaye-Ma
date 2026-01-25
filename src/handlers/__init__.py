# src/handlers/__init__.py
from .start import start_handler, start_callback_handler
from .menu import menu_handlers
from .instagram import instagram_handlers
from .victories import victories_handlers
from .announcements import announcements_handlers
from .petitions import petitions_handlers
from .solidarity import solidarity_handlers
from .resources import resources_handlers
from .settings import settings_handlers
from .admin import admin_handlers
from .suggest import suggest_handlers
from .text_menu import text_menu_handler
from .removal import report_removal_conversation

__all__ = [
    'start_handler',
    'start_callback_handler',
    'menu_handlers',
    'instagram_handlers',
    'victories_handlers',
    'announcements_handlers',
    'petitions_handlers',
    'solidarity_handlers',
    'resources_handlers',
    'settings_handlers',
    'admin_handlers',
    'suggest_handlers',
    'text_menu_handler',
    'report_removal_conversation',
]

