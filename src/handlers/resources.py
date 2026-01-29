"""
Resources and guides handlers for Sedaye Ma bot.
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, ReportTemplate


async def show_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show resources menu."""
    query = update.callback_query
    if query:
        await query.answer()
    
    if query:
        await query.edit_message_text(
            Messages.RESOURCES_HEADER,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.resources_menu()
        )
    else:
        await update.message.reply_text(
            Messages.RESOURCES_HEADER,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.resources_menu()
        )


async def show_report_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Instagram reporting guide."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        Messages.GUIDE_REPORT_IG_TEXT,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )


async def show_safety_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show digital safety guide."""
    query = update.callback_query
    await query.answer()
    
    guide = """
🔒 *راهنمای امنیت دیجیتال*

*VPN:*
✅ همیشه از VPN معتبر استفاده کنید
✅ پیشنهاد: Mullvad, ProtonVPN, Windscribe

*حساب کاربری:*
✅ از ایمیل جداگانه برای فعالیت استفاده کنید
✅ احراز هویت دو مرحله‌ای را فعال کنید
✅ از رمز عبور قوی استفاده کنید

*ارتباطات:*
✅ از پیام‌رسان‌های امن استفاده کنید
✅ پیشنهاد: Signal, Telegram \\(با Secret Chat\\)

*مرورگر:*
✅ از حالت Incognito استفاده کنید
✅ کوکی‌ها را پاک کنید

⚠️ *هشدار:* هرگز اطلاعات شخصی را فاش نکنید
"""
    
    await query.edit_message_text(
        guide,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )


async def show_templates_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of report templates."""
    query = update.callback_query
    await query.answer()
    
    async with get_db() as session:
        result = await session.execute(
            select(ReportTemplate).where(ReportTemplate.is_active == True)
        )
        templates = result.scalars().all()
        
        await query.edit_message_text(
            f"{Messages.TEMPLATE_HEADER}\n\nیک دسته را انتخاب کنید:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.templates_list(templates)
        )


async def view_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View specific template."""
    query = update.callback_query
    await query.answer()
    
    violation_type = query.data.split(":")[-1]
    
    async with get_db() as session:
        result = await session.execute(
            select(ReportTemplate).where(ReportTemplate.violation_type == violation_type)
        )
        template = result.scalar_one_or_none()
        
        if not template:
            await query.answer(Messages.ERROR_NOT_FOUND, show_alert=True)
            return
        
        message = Formatters.format_template(template)
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.back_to_main()
        )


async def show_petitions_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show info about petitions."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        Messages.PETITIONS_GUIDE_TEXT,
        parse_mode="MarkdownV2",
        reply_markup=Keyboards.back_to_main()
    )



# Export handlers
resources_handlers = [
    CallbackQueryHandler(show_resources, pattern=f"^{CallbackData.MENU_RESOURCES}$"),
    CallbackQueryHandler(show_report_guide, pattern=f"^{CallbackData.RESOURCE_REPORT_IG}$"),
    CallbackQueryHandler(show_safety_guide, pattern=f"^{CallbackData.RESOURCE_SAFETY}$"),
    CallbackQueryHandler(show_templates_list, pattern=f"^{CallbackData.RESOURCE_TEMPLATES}$"),
    CallbackQueryHandler(show_petitions_info, pattern=f"^{CallbackData.RESOURCE_PETITIONS_INFO}$"),
    CallbackQueryHandler(view_template, pattern=r"^template:view:\w+$"),
]
