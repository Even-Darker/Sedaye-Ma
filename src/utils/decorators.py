"""
Decorators for Sedaye Ma bot.
Includes admin authentication decorators.
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from config import settings, Messages
from src.database import get_db, Admin
from src.database.models import AdminRole
from sqlalchemy import select


def admin_required(func):
    """
    Decorator to require admin access for a handler.
    Checks if the user is in the admins table.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check database directly
        async with get_db() as session:
            result = await session.execute(
                select(Admin).where(Admin.telegram_id == user_id)
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                return await func(update, context, *args, **kwargs)
        
        # Not authorized
        if update.callback_query:
            await update.callback_query.answer(Messages.ADMIN_UNAUTHORIZED, show_alert=True)
        else:
            await update.message.reply_text(Messages.ADMIN_UNAUTHORIZED, parse_mode="MarkdownV2")
        
        return None
    
    return wrapper


def super_admin_required(func):
    """
    Decorator to require super admin access for a handler.
    Only checks the super admin list from settings.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check database for super_admin role
        async with get_db() as session:
            result = await session.execute(
                select(Admin).where(
                    Admin.telegram_id == user_id,
                    Admin.role == AdminRole.SUPER_ADMIN
                )
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                return await func(update, context, *args, **kwargs)
        
        # Not authorized
        if update.callback_query:
            await update.callback_query.answer(Messages.ADMIN_UNAUTHORIZED, show_alert=True)
        else:
            await update.message.reply_text(Messages.ADMIN_UNAUTHORIZED, parse_mode="MarkdownV2")
        
        return None
    
    return wrapper
