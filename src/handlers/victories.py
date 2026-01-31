from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from sqlalchemy import select, func, desc
from datetime import datetime, UTC, timedelta

from config import Messages
from src.utils import Keyboards, Formatters
from src.utils.keyboards import CallbackData
from src.database import get_db, Victory, InstagramTarget, User, UserReportLog
from src.database.models import TargetStatus
from src.utils.security import encrypt_id
from .settings import show_settings


async def show_victories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show victory wall with statistics."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    enc_id = encrypt_id(chat_id)
    
    async with get_db() as session:
        # --- 1. Community Stats ---
        # Active targets count
        active_targets = (await session.execute(
            select(func.count(InstagramTarget.id))
            .where(InstagramTarget.status != TargetStatus.REMOVED)
        )).scalar() or 0

        # Removed targets count (Total victories)
        removed_targets = (await session.execute(
            select(func.count(InstagramTarget.id))
            .where(InstagramTarget.status == TargetStatus.REMOVED)
        )).scalar() or 0
        
        # Total reports across all users
        total_reports = (await session.execute(
            select(func.count(UserReportLog.id))
        )).scalar() or 0
        
        # --- 2. User-Specific Stats ---
        user_total_reports = (await session.execute(
            select(func.count(UserReportLog.id))
            .where(UserReportLog.encrypted_user_id == enc_id)
        )).scalar() or 0
        
        # Effective reports (reports user made on targets that are now REMOVED)
        user_effective_reports = (await session.execute(
            select(func.count(UserReportLog.id))
            .join(InstagramTarget, UserReportLog.target_id == InstagramTarget.id)
            .where(
                UserReportLog.encrypted_user_id == enc_id,
                InstagramTarget.status == TargetStatus.REMOVED
            )
        )).scalar() or 0

        # Latest victory
        latest_victory = (await session.execute(
            select(Victory, InstagramTarget)
            .join(InstagramTarget, Victory.target_id == InstagramTarget.id)
            .order_by(Victory.victory_date.desc())
            .limit(1)
        )).first()
        
        # --- 3. Formatting ---
        esc = Formatters.escape_markdown
        
        # Community Progress
        total_listed = active_targets + removed_targets
        progress_perc = int((removed_targets / total_listed * 100)) if total_listed > 0 else 0
        progress_bar = Formatters.generate_progress_bar(progress_perc)
        
        message = (
            "🏆 *تالار افتخار صدای ما*\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            "آمار افتخارات و پیروزی‌های جمعی ما\n\n"
            
            "📊 *آمار کلی جامعه:*\n"
            f"🧃 صفحات ساندیسی فعال: `{esc(str(active_targets))}`\n"
            f"🔫🧃 ساندیسی‌های بسته شده: `{esc(str(removed_targets))}`\n"
            f"💥 تعداد کل ریپورت ها: `{esc(str(total_reports))}`\n"
            f"📈 پیشرفت آزادی: `{progress_bar}` `{progress_perc}%`\n\n"
            
            "👤 *آمار فعالیت شما:*\n"
            f"⚔️ تعداد ریپورت‌های شما: `{esc(str(user_total_reports))}`\n"
            f"🔫💥 تعداد ساندیسی‌های بسته شده توسط شما: `{esc(str(user_effective_reports))}`\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        )
        
        if latest_victory:
            victory, target = latest_victory
            message += f"🎉 *آخرین پیروزی:* \n\n{Formatters.format_victory_card(victory, target)}"
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.victories_actions()
        )
        return ConversationHandler.END


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top 10 reporters with medals and user's rank."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    enc_id = encrypt_id(chat_id)
    
    async with get_db() as session:
        # 1. Get Top 10 users by report count (Tie breaker: join date)
        top_users_stmt = (
            select(
                UserReportLog.encrypted_user_id,
                func.count(UserReportLog.id).label('report_count'),
                User.first_seen
            )
            .join(User, UserReportLog.encrypted_user_id == User.encrypted_chat_id)
            .group_by(UserReportLog.encrypted_user_id, User.first_seen)
            .order_by(desc('report_count'), User.first_seen.asc())
            .limit(10)
        )
        top_results = (await session.execute(top_users_stmt)).all()
        
        # 2. Get User's Rank & Count
        user_count_stmt = (
            select(func.count(UserReportLog.id))
            .where(UserReportLog.encrypted_user_id == enc_id)
        )
        user_count = (await session.execute(user_count_stmt)).scalar() or 0
        
        # Calculate rank (users with more reports OR same reports but joined earlier)
        # Using a subquery for the counts
        rank_stmt = (
            select(func.count() + 1)
            .select_from(
                select(UserReportLog.encrypted_user_id)
                .join(User, UserReportLog.encrypted_user_id == User.encrypted_chat_id)
                .group_by(UserReportLog.encrypted_user_id, User.first_seen)
                .having(
                    (func.count(UserReportLog.id) > user_count) |
                    ((func.count(UserReportLog.id) == user_count) & (User.first_seen < (
                        select(User.first_seen).where(User.encrypted_chat_id == enc_id).scalar_subquery()
                    )))
                )
            )
        )
        user_rank = (await session.execute(rank_stmt)).scalar() or 1
        
        # 3. Format Leaderboard
        esc = Formatters.escape_markdown
        
        message = (
            "🏆 *گارد ویژه صدای ما⚔️*\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            "قدردانی از تک‌تیراندازهای فعال جامعه\n\n"
        )
        
        is_user_in_top_10 = False
        top_10_threshold = 0
        
        for i, (u_enc_id, count, _) in enumerate(top_results):
            rank = i + 1
            # Medal logic: Top 1-3 Gold, 4-8 Silver, 9-10 Bronze
            if rank <= 3: medal = "🥇"
            elif rank <= 8: medal = "🥈"
            else: medal = "🥉"
            
            # Fetch user object for nickname
            u_stmt = select(User).where(User.encrypted_chat_id == u_enc_id)
            u_obj = (await session.execute(u_stmt)).scalar_one_or_none()
            name = u_obj.effective_nickname if u_obj else f"User #{u_enc_id[:8]}"
            
            # Mark the current user in the list
            me_indicator = " ⭐" if u_enc_id == enc_id else ""
            if u_enc_id == enc_id:
                is_user_in_top_10 = True
                
            message += f"{rank}\\. {medal} *{esc(name)}*{me_indicator} \\- `{esc(str(count))}` تعداد گزارش\n"
            top_10_threshold = count
            
        message += "\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        
        # User's Rank Details
        message += f"👤⭐ *رتبه شما:* `{esc(str(user_rank))}`\n"
        
        if is_user_in_top_10:
            encouragement = [
                "جامعه به تک‌تیراندازهایی مثل شما نیاز داره! 🔥",
                "تعظیم در برابر تلاش شما! 🫡",
                "ستون ارتش مردمی! 🛡"
            ]
            import random
            chosen = random.choice(encouragement)
            message += f"💪 _{esc(chosen)}_\n"
        else:
            needed = (top_10_threshold - user_count) + 1 if top_10_threshold > 0 else 1
            if needed <= 0: needed = 1 # Edge case
            
            message += f"🎯 شما فقط `{esc(str(needed))}` ریپورت تا ورود به گارد ویژه فاصله دارید\\!\n\n"
            
            # Progress bar to top 10 (arbitrary max for visuals)
            progress_perc = int((user_count / (top_10_threshold or 1)) * 100)
            progress_bar = Formatters.generate_progress_bar(min(100, progress_perc))
            message += f"📊 *میزان پیشرفت تا ورود به گارد ویژه:*\n`{progress_perc}% `{progress_bar}`🎖️`\n"

        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.leaderboard_actions()
        )


async def view_all_victories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all victories list (legacy redirect to show_victories)."""
    await show_victories(update, context)


async def celebrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show celebration message."""
    query = update.callback_query
    await query.answer("🎉🎊🔥 تبریک! 🔥🎊🎉", show_alert=True)


# State for nickname conversation
NICKNAME = 1


# Nickname Flow Handlers
async def change_nickname_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for a new nickname."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👤 *تغییر لقب*\n\n"
        "لطفاً لقب جدید خود را \\(حداکثر ۳۰ کاراکتر\\) ارسال کنید\\.\n\n"
        "⚠️ *هشدار:* برای امنیت و حریم خصوصی خود، از نامی استفاده کنید که هویت واقعی شما را فاش نکند\\.",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(Messages.CANCEL_ACTION, callback_data=CallbackData.MENU_SETTINGS)]])
    )
    return NICKNAME


async def receive_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate and save user nickname."""
    new_nick = update.message.text.strip()
    
    # Exclusion list for menu buttons
    menu_buttons = [
        Messages.MENU_TARGETS, Messages.MENU_VICTORIES, Messages.MENU_STATS,
        Messages.MENU_ANNOUNCEMENTS, Messages.MENU_PETITIONS, Messages.MENU_SOLIDARITY,
        Messages.MENU_RESOURCES, Messages.MENU_SETTINGS, Messages.MENU_FREE_CONFIGS,
        Messages.MENU_EMAILS, Messages.BACK_BUTTON, Messages.CANCEL_ACTION
    ]
    
    if new_nick in menu_buttons:
        # If user clicked a menu button, end the conversation and don't save
        return ConversationHandler.END

    # Validation
    if len(new_nick) > 30:
        await update.message.reply_text("❌ لقب نباید بیشتر از ۳۰ کاراکتر باشد\\. لطفاً دوباره تلاش کنید\\.", parse_mode="MarkdownV2")
        return
    
    if any(char in new_nick for char in "<>{}[]@/"):
         await update.message.reply_text("❌ لقب شامل کاراکترهای غیرمجاز است\\. لطفاً نام ساده‌تری انتخاب کنید\\.", parse_mode="MarkdownV2")
         return

    enc_id = encrypt_id(update.effective_chat.id)
    
    async with get_db() as session:
        stmt = select(User).where(User.encrypted_chat_id == enc_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        if user:
            user.nickname = new_nick
            await session.commit()
            
            await update.message.reply_text(
                f"✅ لقب شما به *{Formatters.escape_markdown(new_nick)}* تغییر یافت\\.",
                parse_mode="MarkdownV2",
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ مشکلی در یافتن حساب شما پیش آمد\\.", parse_mode="MarkdownV2")
            return ConversationHandler.END


async def handle_victory_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate high-energy sharing text for the user."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    enc_id = encrypt_id(chat_id)
    
    async with get_db() as session:
        # Get User and Stats
        u_stmt = select(User).where(User.encrypted_chat_id == enc_id)
        user = (await session.execute(u_stmt)).scalar_one_or_none()
        
        user_total_reports = (await session.execute(
            select(func.count(UserReportLog.id))
            .where(UserReportLog.encrypted_user_id == enc_id)
        )).scalar() or 0
        
        user_effective_reports = (await session.execute(
            select(func.count(UserReportLog.id))
            .join(InstagramTarget, UserReportLog.target_id == InstagramTarget.id)
            .where(
                UserReportLog.encrypted_user_id == enc_id,
                InstagramTarget.status == TargetStatus.REMOVED
            )
        )).scalar() or 0
        
        # Determine Rank
        rank_stmt = (
            select(func.count(User.id))
            .where(
                select(func.count(UserReportLog.id))
                .where(UserReportLog.encrypted_user_id == User.encrypted_chat_id)
                .scalar_subquery() > user_total_reports
            )
        )
        rank = (await session.execute(rank_stmt)).scalar() + 1
        
        nickname = user.effective_nickname if user else "مبارز"
        
        # Hyped sharing text
        if rank <= 10:
            hype_title = f"🔥 بالاخره وارد ۱۰ نفر اول شدم!"
            medal = "🎖️" if rank > 3 else "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        else:
            hype_title = f"⚔️ دارم خودم رو به جمع برترین‌ها می‌رسونم!"
            medal = "🛡️"

        share_text = (
            f"{hype_title}\n\n"
            f"👤 لقب: {nickname}\n"
            f"⚔️ گزارش‌های من: {user_total_reports}\n"
            f"💥 ساندیسی‌های سرنگون شده: {user_effective_reports}\n"
            f"🏅 رتبه من: #{rank}\n\n"
            f"✌️ همبستگی رمز پیروزی ماست! شما هم به ما بپیوندید.\n"
            f"🔗 t.me/Sedaye_Ma_Bot"
        )
        
        await query.edit_message_text(
            f"📤 *اشتراک‌گذاری افتخارات*\n\n"
            f"مبارز عزیز *{Formatters.escape_markdown(nickname)}*، رتبه شما در گارد ویژه `{rank}` است\\! {medal}\n\n"
            "پلتفرم مورد نظر را برای اشتراک‌گذاری افتخارات خود انتخاب کنید:",
            parse_mode="MarkdownV2",
            reply_markup=Keyboards.generic_share_menu(share_text, back_callback=CallbackData.VICTORIES_LEADERBOARD)
        )


nickname_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(change_nickname_start, pattern=f"^{CallbackData.VICTORIES_NICKNAME_START}$")],
    states={
        NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nickname)]
    },
    fallbacks=[
        CallbackQueryHandler(show_victories, pattern=f"^{CallbackData.MENU_VICTORIES}$"),
        CallbackQueryHandler(show_settings, pattern=f"^{CallbackData.MENU_SETTINGS}$")
    ],
    per_message=False
)


# Export handlers
victories_handlers = [
    CallbackQueryHandler(show_victories, pattern=f"^{CallbackData.MENU_VICTORIES}$"),
    CallbackQueryHandler(show_leaderboard, pattern=f"^{CallbackData.VICTORIES_LEADERBOARD}$"),
    CallbackQueryHandler(handle_victory_share, pattern=f"^{CallbackData.VICTORIES_SHARE}$"),
    nickname_conversation,
    CallbackQueryHandler(view_all_victories, pattern=f"^{CallbackData.VICTORIES_ALL}$"),
    CallbackQueryHandler(celebrate, pattern=f"^{CallbackData.VICTORIES_CELEBRATE}$"),
]
