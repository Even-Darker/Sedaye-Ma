"""
Telegram keyboard builders for Sedaye Ma bot.
All keyboards are defined here for consistency.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from config import Messages


class CallbackData:
    """Callback data constants."""
    # Main menu
    MENU_TARGETS = "menu:targets"
    MENU_VICTORIES = "menu:victories"
    MENU_FREE_CONFIGS = "menu:free_configs"
    MENU_STATS = "menu:stats"
    MENU_ANNOUNCEMENTS = "menu:announcements"
    MENU_PETITIONS = "menu:petitions"
    MENU_SOLIDARITY = "menu:solidarity"
    MENU_RESOURCES = "menu:resources"
    MENU_SETTINGS = "menu:settings"
    MENU_EMAILS = "menu:emails"
    
    # Navigation
    BACK_MAIN = "nav:main"
    BACK_SANDISI = "nav:sandisi"
    BACK_FILTER = "nav:filter"
    BACK = "nav:back"
    BACK_ADMIN = "nav:admin"
    ADMIN_PANEL = "admin:panel"
    
    # User suggest target
    SUGGEST_TARGET = "suggest:target"
    SUGGEST_REMOVAL = "suggest:removal"
    SUGGEST_CONFIRM_YES = "suggest:confirm:yes"
    SUGGEST_CONFIRM_EDIT = "suggest:confirm:edit"
    
    # Report Removal
    REMOVAL_CONFIRM_YES = "removal:confirm:yes"
    REMOVAL_CONFIRM_NO = "removal:confirm:no"
    
    # Targets
    TARGETS_LIST = "targets:list"
    TARGET_VIEW = "target:view:{id}"
    TARGET_REPORT = "target:report:{id}"
    TARGET_TEMPLATE = "target:template:{id}"
    TARGET_I_REPORTED = "target:reported:{id}"
    TARGET_REPORT_CLOSED = "target:report_closed:{id}" # Legacy (mapped to problem button)
    TARGET_CONCERN_CLOSED = "target:concern:closed:{id}"
    TARGET_CONCERN_OTHER = "target:concern:other:{id}"
    TARGETS_SORT = "targets:sort:{by}"
    TARGETS_PAGE = "targets:page:{page}"
    
    # Filtering
    FILTER_MENU = "targets:filter_menu"
    FILTER_NEW = "targets:filter:new"
    FILTER_REPORTED = "targets:filter:reported"
    FILTER_ALL = "targets:filter:all"
    
    # Victories
    VICTORIES_ALL = "victories:all"
    VICTORIES_CELEBRATE = "victories:celebrate"
    VICTORIES_PAGE = "victories:page:{page}"
    
    # Announcements
    ANNOUNCEMENT_VIEW = "announce:view:{id}"
    ANNOUNCEMENT_REACT = "announce:react:{id}:{emoji}"
    
    # Petitions
    PETITION_VIEW = "petition:view:{id}"
    PETITION_SIGN = "petition:sign:{id}"
    PETITION_NAV = "petition:nav:{offset}"
    PETITIONS_PAGE = "petitions:page:{page}"
    
    # Solidarity
    SOLIDARITY_WRITE = "solidarity:write"
    SOLIDARITY_MORE = "solidarity:more"
    SOLIDARITY_HEART = "solidarity:heart:{id}"
    
    # Resources
    RESOURCE_REPORT_IG = "resource:report_ig"
    RESOURCE_SAFETY = "resource:safety"
    RESOURCE_TEMPLATES = "resource:templates"
    RESOURCE_SUPPORT = "resource:support"
    TEMPLATE_VIEW = "template:view:{type}"
    
    # Settings
    SETTINGS_NOTIF = "settings:notif"
    NOTIF_TOGGLE = "notif:toggle:{type}"
    
    # Admin
    ADMIN_ADD_TARGET = "admin:add_target"
    ADMIN_MANAGE_TARGETS = "admin:manage_targets"
    ADMIN_ADD_CONFIG = "admin:add_config"
    ADMIN_MANAGE_CONFIGS = "admin:manage_configs"
    ADMIN_DELETE_CONFIG = "admin:delete_config:{id}"
    ADMIN_ANNOUNCEMENTS = "admin:announcements"
    ADMIN_PETITIONS = "admin:petitions"
    ADMIN_SOLIDARITY = "admin:solidarity"
    ADMIN_STATS = "admin:stats"
    ADMIN_MANAGE_ADMINS = "admin:manage_admins"
    ADMIN_PENDING_TARGETS = "admin:pending_targets"
    ADMIN_PANEL = "admin:panel"
    
    ADMIN_TARGET_EDIT = "admin:target:edit:{id}"
    ADMIN_TARGET_REMOVE = "admin:target:remove:{id}"
    ADMIN_TARGET_VICTORY = "admin:target:victory:{id}"
    ADMIN_CONFIRM_REMOVAL = "admin:confirm_removal:{id}"
    
    ADMIN_APPROVE_MSG = "admin:approve_msg:{id}"
    ADMIN_REJECT_MSG = "admin:reject_msg:{id}"
    ADMIN_MESSAGE_PROCESS = "admin:msg:process:{action}:{id}"
    
    ADMIN_CONFIRM_CLOSED_YES = "admin:closed:yes:{id}"
    ADMIN_CONFIRM_CLOSED_NO = "admin:closed:no:{id}"
    
    ADMIN_ADD_ADMIN = "admin:add_admin"
    ADMIN_REMOVE_ADMIN = "admin:remove_admin:{id}"
    
    # Reports
    ADMIN_REPORTS = "admin:reports"
    ADMIN_REPORTS_CLOSED = "admin:reports:closed"
    ADMIN_REPORTS_MESSAGES = "admin:reports:messages"
    ADMIN_VIEW_MESSAGE = "admin:msg:view:{id}"

    # Configs
    CONFIGS_PAGE = "configs:page:{page}"
    CONFIG_REPORT = "config:report:{id}"
    CONFIG_COPY = "config:copy:{id}"
    
    # Email Campaigns
    EMAILS_PAGE = "emails:page:{page}"
    EMAIL_VIEW = "email:view:{id}"
    EMAIL_ACTION_DONE = "email:done:{id}:{page}"
    EMAIL_OPEN = "email:open:{id}"
    EMAILS_FILTER_NEW = "emails:filter:new"
    EMAILS_FILTER_DONE = "emails:filter:done"
    
    ADMIN_ADD_EMAIL = "admin:add_email"
    ADMIN_MANAGE_EMAILS = "admin:manage_emails"
    ADMIN_DELETE_EMAIL = "admin:delete_email:{id}"
    ADMIN_VIEW_EMAIL = "admin:email:view:{id}"



class Keyboards:
    """Keyboard builders for the bot."""
    
    @staticmethod
    def start() -> InlineKeyboardMarkup:
        """Start button keyboard."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.START_BUTTON, callback_data="start")]
        ])
    
    @staticmethod
    def main_menu_persistent(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Main menu persistent keyboard (Reply Keyboard)."""
        buttons = [
            [KeyboardButton(Messages.MENU_TARGETS)],  # Row 1: Report Sandisi (Main)
            [KeyboardButton(Messages.MENU_ANNOUNCEMENTS), KeyboardButton(Messages.MENU_PETITIONS)],
            #TODO: Add solidarity menu
            # [KeyboardButton(Messages.MENU_SOLIDARITY)],
            [KeyboardButton(Messages.MENU_EMAILS), KeyboardButton(Messages.MENU_FREE_CONFIGS)],
            [KeyboardButton(Messages.MENU_SETTINGS)]
        ]
        
        if is_admin:
            buttons.append([KeyboardButton(Messages.ADMIN_HEADER)])  # "🔐 پنل مدیریت" (Make sure this constant matches text)
            
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)

    
    @staticmethod
    def report_sandisi_menu() -> InlineKeyboardMarkup:
        """Submenu for Report Sandisi features."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 لیست ساندیسی‌ها", callback_data=CallbackData.FILTER_MENU)],
            [InlineKeyboardButton("🧃 معرفی ساندیس خور", callback_data=CallbackData.SUGGEST_TARGET)],
            [
                InlineKeyboardButton("✌️ گزارش موفقیت", callback_data=CallbackData.SUGGEST_REMOVAL),
                InlineKeyboardButton(Messages.MENU_VICTORIES, callback_data=CallbackData.MENU_VICTORIES)
            ],
        ])
    
    @staticmethod
    def targets_filter_menu() -> InlineKeyboardMarkup:
        """Menu to filter targets (New vs Reported vs All)."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🕰️ قدیمی", callback_data=CallbackData.FILTER_REPORTED),
                InlineKeyboardButton("🧃 جدید", callback_data=CallbackData.FILTER_NEW),
            ],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_SANDISI)],
        ])
    
    @staticmethod
    def confirm_suggest_handle() -> InlineKeyboardMarkup:
        """Keyboard to confirm suggested handle."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ صحیح است، ادامه", callback_data=CallbackData.SUGGEST_CONFIRM_YES)],
            [InlineKeyboardButton("✏️ ویرایش نام کاربری", callback_data=CallbackData.SUGGEST_CONFIRM_EDIT)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_SANDISI)],
        ])

    @staticmethod
    def back_to_main() -> InlineKeyboardMarkup:
        """Back to main menu button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])

    @staticmethod
    def back_to_admin() -> InlineKeyboardMarkup:
        """Back to admin menu button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_ADMIN)]
        ])

    @staticmethod
    def back_to_sandisi() -> InlineKeyboardMarkup:
        """Back to report sandisi menu button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_SANDISI)]
        ])
    
    @staticmethod
    def target_actions(target_id: int, ig_handle: str) -> InlineKeyboardMarkup:
        """Action buttons for a target."""
        return InlineKeyboardMarkup([
            # [
            #     InlineKeyboardButton(
            #         Messages.REPORT_BUTTON, 
            #         callback_data=CallbackData.TARGET_TEMPLATE.format(id=target_id)
            #     ),
            # ],
            [
                InlineKeyboardButton(
                    Messages.OPEN_PROFILE_BUTTON, 
                    url=f"https://instagram.com/{ig_handle}"
                ),
            ],
            [
                InlineKeyboardButton(
                    Messages.I_REPORTED_BUTTON,
                    callback_data=CallbackData.TARGET_I_REPORTED.format(id=target_id)
                ),
            ],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.TARGETS_LIST)]
        ])
    
    @staticmethod
    def targets_list(targets: list, page: int = 0, total_pages: int = 1, show_report_button: bool = True) -> InlineKeyboardMarkup:
        """List of targets with pagination."""
        buttons = []
        
        for target in targets:
            # TODO: Add priority emoji
            # priority_emoji = "🔴" if target.priority <= 3 else "🟡" if target.priority <= 6 else "🟢"
            priority_emoji = ""
            # Determine button text
            concern_text = "⚠️ اشکال" if show_report_button else "📝 گزارش"
            
            # Row 2: Quick Actions
            row = [
                InlineKeyboardButton(
                    f"{priority_emoji} @{target.ig_handle}",
                    url=f"https://instagram.com/{target.ig_handle}"
                ),
                InlineKeyboardButton(
                    concern_text,
                    callback_data=CallbackData.TARGET_REPORT_CLOSED.format(id=target.id)
                )
            ]
            
            if show_report_button:
                row.append(
                    InlineKeyboardButton(
                        Messages.I_REPORTED_BUTTON, 
                        callback_data=CallbackData.TARGET_I_REPORTED.format(id=target.id)
                    )
                )
                
            buttons.append(row)
            
            # Add spacer or separator logic if needed, but for now lists are enough.
            # (Note: Original View/More button is replaced by direct link + actions)
            # If "View details" is still needed (e.g. for reasons/stats), maybe add it?
            # User request implied clicking handle opens profile. 
            # Stats are visible in text? No, text is just header.
            # Standard list item text was: "🔴 @handle (count)"
            # Now it's a button.
            
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=CallbackData.TARGETS_PAGE.format(page=page-1)))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=CallbackData.TARGETS_PAGE.format(page=page+1)))
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_FILTER)])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def free_configs_pagination(config_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
        """Pagination for free configs with actions."""
        # Action Buttons
        actions = []
        actions.append(InlineKeyboardButton("📋 کپی کانفیگ", callback_data=CallbackData.CONFIG_COPY.format(id=config_id)))
        actions.append(InlineKeyboardButton("🚨 گزارش خرابی", callback_data=CallbackData.CONFIG_REPORT.format(id=config_id)))
        
        # Navigation Buttons
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ قبلی", callback_data=CallbackData.CONFIGS_PAGE.format(page=current_page-1)))
        
        if current_page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("بعدی ▶️", callback_data=CallbackData.CONFIGS_PAGE.format(page=current_page+1)))

        return InlineKeyboardMarkup([
            actions,
            nav_buttons,
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])
    
    @staticmethod
    def victories_actions() -> InlineKeyboardMarkup:
        """Victory wall action buttons."""
        return InlineKeyboardMarkup([
            # [InlineKeyboardButton(Messages.VIEW_ALL_VICTORIES, callback_data=CallbackData.VICTORIES_ALL)],
            # [InlineKeyboardButton(Messages.CELEBRATE_BUTTON, callback_data=CallbackData.VICTORIES_CELEBRATE)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_SANDISI)]
        ])
    
    @staticmethod
    def announcement_reactions(announcement_id: int, fire: int = 0, heart: int = 0, fist: int = 0) -> InlineKeyboardMarkup:
        """Announcement with reaction buttons."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🔥 {fire}", callback_data=CallbackData.ANNOUNCEMENT_REACT.format(id=announcement_id, emoji="fire")),
                InlineKeyboardButton(f"❤️ {heart}", callback_data=CallbackData.ANNOUNCEMENT_REACT.format(id=announcement_id, emoji="heart")),
                InlineKeyboardButton(f"✊ {fist}", callback_data=CallbackData.ANNOUNCEMENT_REACT.format(id=announcement_id, emoji="fist")),
            ],
            [InlineKeyboardButton(Messages.SHARE_BUTTON, switch_inline_query=f"announcement_{announcement_id}")],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.MENU_ANNOUNCEMENTS)]
        ])
    
    @staticmethod
    def petition_actions(petition_id: int, url: str, offset: int = 0, total: int = 1) -> InlineKeyboardMarkup:
        """Petition action buttons with navigation."""
        buttons = []

        buttons.append([
            InlineKeyboardButton(Messages.SHARE_BUTTON, switch_inline_query=f"petition_{petition_id}"),
            InlineKeyboardButton(Messages.SIGN_PETITION, url=url),
        ])
        
        # Navigation Row
        nav_row = []
        if offset > 0:
            nav_row.append(InlineKeyboardButton(Messages.PREV_BUTTON, callback_data=CallbackData.PETITION_NAV.format(offset=offset-1)))
            
        # Indicator (optional, or just logic)
        
        if offset < total - 1:
            nav_row.append(InlineKeyboardButton(Messages.NEXT_BUTTON, callback_data=CallbackData.PETITION_NAV.format(offset=offset+1)))
            
        if nav_row:
            buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def solidarity_actions() -> InlineKeyboardMarkup:
        """Solidarity wall actions."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.LEAVE_MESSAGE, callback_data=CallbackData.SOLIDARITY_WRITE)],
            [InlineKeyboardButton(Messages.LOAD_MORE, callback_data=CallbackData.SOLIDARITY_MORE)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])
    
    @staticmethod
    def resources_menu() -> InlineKeyboardMarkup:
        """Resources menu."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.GUIDE_REPORT_IG, callback_data=CallbackData.RESOURCE_REPORT_IG)],
            [InlineKeyboardButton(Messages.GUIDE_SAFETY, callback_data=CallbackData.RESOURCE_SAFETY)],
            [InlineKeyboardButton(Messages.GUIDE_TEMPLATES, callback_data=CallbackData.RESOURCE_TEMPLATES)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])
    
    @staticmethod
    def templates_list(templates: list) -> InlineKeyboardMarkup:
        """Report templates list."""
        buttons = []
        for template in templates:
            buttons.append([
                InlineKeyboardButton(
                    template.name_fa,
                    callback_data=CallbackData.TEMPLATE_VIEW.format(type=template.violation_type)
                )
            ])
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.MENU_RESOURCES)])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def notification_settings(prefs) -> InlineKeyboardMarkup:
        """Notification settings toggles."""
        def toggle_text(enabled: bool) -> str:
            return Messages.NOTIF_ENABLED if enabled else Messages.NOTIF_DISABLED
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{Messages.NOTIF_URGENT} [{toggle_text(prefs.announcements_urgent)}]",
                callback_data=CallbackData.NOTIF_TOGGLE.format(type="urgent")
            )],
            [InlineKeyboardButton(
                f"{Messages.NOTIF_NEWS} [{toggle_text(prefs.announcements_news)}]",
                callback_data=CallbackData.NOTIF_TOGGLE.format(type="news")
            )],
            [InlineKeyboardButton(
                f"{Messages.NOTIF_VICTORIES} [{toggle_text(prefs.victories)}]",
                callback_data=CallbackData.NOTIF_TOGGLE.format(type="victories")
            )],
            [InlineKeyboardButton(
                f"{Messages.NOTIF_PETITIONS} [{toggle_text(prefs.petitions)}]",
                callback_data=CallbackData.NOTIF_TOGGLE.format(type="petitions")
            )],
            [InlineKeyboardButton(
                f"{Messages.NOTIF_EMAILS} [{toggle_text(prefs.email_campaigns)}]",
                callback_data=CallbackData.NOTIF_TOGGLE.format(type="emails")
            )],
        ])
    

    @staticmethod
    def admin_menu(is_super_admin: bool = False, pending_count: int = 0, reports_count: int = 0) -> InlineKeyboardMarkup:
        """Main admin menu."""
        
        pending_badge = f" ({pending_count})" if pending_count > 0 else ""
        reports_badge = f" ({reports_count})" if reports_count > 0 else ""
        
        buttons = [
            # [
            #     InlineKeyboardButton(Messages.ADMIN_ADD_TARGET, callback_data=CallbackData.ADMIN_ADD_TARGET),
            #     InlineKeyboardButton(Messages.ADMIN_MANAGE_TARGETS, callback_data=CallbackData.ADMIN_MANAGE_TARGETS)
            # ],
            [
                InlineKeyboardButton(f"{Messages.ADMIN_PENDING_TARGETS}{pending_badge}", callback_data=CallbackData.ADMIN_PENDING_TARGETS)
            ],
            [
                InlineKeyboardButton(f"📄 گزارش‌ها و پیام‌ها{reports_badge}", callback_data=CallbackData.ADMIN_REPORTS),
            ],
            # [InlineKeyboardButton(Messages.ADMIN_ANNOUNCEMENTS, callback_data=CallbackData.ADMIN_ANNOUNCEMENTS)],
            [InlineKeyboardButton(Messages.ADMIN_MANAGE_EMAILS_BTN, callback_data=CallbackData.ADMIN_MANAGE_EMAILS), InlineKeyboardButton(Messages.ADMIN_PETITIONS, callback_data=CallbackData.ADMIN_PETITIONS),],
            [
                InlineKeyboardButton("📡 مدیریت کانفیگ‌ها", callback_data=CallbackData.ADMIN_MANAGE_CONFIGS),
                InlineKeyboardButton("➕ افزودن کانفیگ", callback_data=CallbackData.ADMIN_ADD_CONFIG),
            ],
        ]
        
        if is_super_admin:
            buttons.append(
                [
                    InlineKeyboardButton(Messages.ADMIN_STATS, callback_data=CallbackData.ADMIN_STATS),
                    InlineKeyboardButton(Messages.ADMIN_MANAGE_ADMINS, callback_data=CallbackData.ADMIN_MANAGE_ADMINS),
                ]
            )
            
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def admin_reports_menu(closed_count: int = 0, msgs_count: int = 0) -> InlineKeyboardMarkup:
        """Menu for reports types (with notification badges)."""
        closed_badge = f" ({closed_count})"
        msgs_badge = f" ({msgs_count})"
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"صفحه بسته شده{closed_badge} 📌", callback_data=CallbackData.ADMIN_REPORTS_CLOSED)],
            [InlineKeyboardButton(f"پیامهای کاربران{msgs_badge} 💬", callback_data=CallbackData.ADMIN_REPORTS_MESSAGES)],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_ADMIN)],
        ])
    
    @staticmethod
    def admin_messages_list(logs: list) -> InlineKeyboardMarkup:
        """List of user messages."""
        buttons = []
        for log in logs:
            # Showing partial ID or content
            preview = (log.message_content[:20] + "...") if log.message_content else "No Content"
            buttons.append([
                InlineKeyboardButton(
                    f"📩 {preview}",
                    callback_data=CallbackData.ADMIN_VIEW_MESSAGE.format(id=log.id)
                )
            ])
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_REPORTS)])
        return InlineKeyboardMarkup(buttons)

    ADMIN_MESSAGE_PROCESS = "admin:msg:process:{action}:{id}"

    @staticmethod
    def admin_message_process(log_id: int) -> InlineKeyboardMarkup:
        """Actions for a user message (Queue Mode)."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ حذف", callback_data=CallbackData.ADMIN_MESSAGE_PROCESS.format(action="reject", id=log_id)),
                InlineKeyboardButton("✅ بررسی شد", callback_data=CallbackData.ADMIN_MESSAGE_PROCESS.format(action="confirm", id=log_id)),
            ],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_REPORTS)]
        ])
    
    @staticmethod
    def admin_pending_approval(target_id: int) -> InlineKeyboardMarkup:
        """Admin approval buttons for pending targets."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تأیید", callback_data=f"admin:approve_target:{target_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"admin:reject_target:{target_id}"),
            ],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_ADMIN)],
        ])
    
    @staticmethod
    def admin_list(admins: list) -> InlineKeyboardMarkup:
        """List of admins with remove buttons."""
        buttons = []
        for admin in admins:
            buttons.append([
                InlineKeyboardButton(
                    f"❌ {admin.telegram_id} ({admin.role.value})",
                    callback_data=CallbackData.ADMIN_REMOVE_ADMIN.format(id=admin.id)
                )
            ])
        buttons.append([InlineKeyboardButton("➕ افزودن ادمین جدید", callback_data=CallbackData.ADMIN_ADD_ADMIN)])
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_ADMIN)])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def admin_target_actions(target_id: int) -> InlineKeyboardMarkup:
        """Admin actions for a target."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ ویرایش", callback_data=CallbackData.ADMIN_TARGET_EDIT.format(id=target_id))],
            [InlineKeyboardButton("🏆 علامت به عنوان حذف شده", callback_data=CallbackData.ADMIN_TARGET_VICTORY.format(id=target_id))],
            [InlineKeyboardButton("❌ حذف از لیست", callback_data=CallbackData.ADMIN_TARGET_REMOVE.format(id=target_id))],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_MANAGE_TARGETS)]
        ])
    
    @staticmethod
    def admin_solidarity_moderation(message_id: int) -> InlineKeyboardMarkup:
        """Admin moderation for solidarity messages."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تأیید", callback_data=CallbackData.ADMIN_APPROVE_MSG.format(id=message_id)),
                InlineKeyboardButton("❌ رد", callback_data=CallbackData.ADMIN_REJECT_MSG.format(id=message_id)),
            ]
        ])

    @staticmethod
    def admin_confirm_closed(target_id: int) -> InlineKeyboardMarkup:
        """Admin confirmation for closed report."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌", callback_data=CallbackData.ADMIN_CONFIRM_CLOSED_NO.format(id=target_id)),
                InlineKeyboardButton("✅", callback_data=CallbackData.ADMIN_CONFIRM_CLOSED_YES.format(id=target_id)),
            ],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_REPORTS)]
        ])

    @staticmethod
    def concern_menu(target_id: int) -> InlineKeyboardMarkup:
        """Menu for choosing concern type."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 صفحه بسته شده", callback_data=CallbackData.TARGET_CONCERN_CLOSED.format(id=target_id))],
            [InlineKeyboardButton("💬 موارد دیگر", callback_data=CallbackData.TARGET_CONCERN_OTHER.format(id=target_id))],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.TARGETS_LIST)], 
        ])

    @staticmethod
    def email_campaigns_list(campaigns: list, page: int = 0, total_pages: int = 1, completed_ids: set = None, filter_mode: str = "new") -> InlineKeyboardMarkup:
        """List of email campaigns with pagination and completion badges."""
        if completed_ids is None:
            completed_ids = set()
            
        buttons = []
        
        # Filter tabs
        new_label = "🆕 جدید" if filter_mode != "new" else "🆕 جدید ✓"
        done_label = "✅ انجام شده" if filter_mode != "done" else "✅ انجام شده ✓"
        buttons.append([
            InlineKeyboardButton(new_label, callback_data=CallbackData.EMAILS_FILTER_NEW),
            InlineKeyboardButton(done_label, callback_data=CallbackData.EMAILS_FILTER_DONE),
        ])
        
        for campaign in campaigns:
            # Add checkmark prefix if completed
            prefix = "✅ " if campaign.id in completed_ids else ""
            buttons.append([
                InlineKeyboardButton(
                    f"{prefix}📧 {campaign.title}",
                    callback_data=CallbackData.EMAIL_VIEW.format(id=campaign.id)
                )
            ])
            
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=CallbackData.EMAILS_PAGE.format(page=page-1)))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=CallbackData.EMAILS_PAGE.format(page=page+1)))
        if nav_buttons:
            buttons.append(nav_buttons)
            
        # No back button - user uses persistent keyboard
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def email_campaign_action(campaign_id: int, mailto_link: str, already_done: bool = False) -> InlineKeyboardMarkup:
        """Actions for a specific email campaign."""
        buttons = [
            [InlineKeyboardButton(Messages.EMAIL_SEND_BTN, url=mailto_link)],
        ]
        
        if already_done:
            buttons.append([InlineKeyboardButton("✅ قبلاً انجام دادید", callback_data="noop")])
        else:
            buttons.append([InlineKeyboardButton(Messages.EMAIL_DONE_BTN, callback_data=CallbackData.EMAIL_ACTION_DONE.format(id=campaign_id))])
        
        buttons.append([InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=CallbackData.MENU_EMAILS)])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def admin_emails_list(campaigns: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Admin list of campaigns to manage with pagination."""
        buttons = []
        for campaign in campaigns:
            buttons.append([
                InlineKeyboardButton(f"📄 {campaign.title[:20]}", callback_data=CallbackData.ADMIN_VIEW_EMAIL.format(id=campaign.id))
            ])
            
        # Pagination
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"{CallbackData.ADMIN_MANAGE_EMAILS}:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"{CallbackData.ADMIN_MANAGE_EMAILS}:{page+1}"))
            
        if nav_buttons:
            buttons.append(nav_buttons)
            
        buttons.append([InlineKeyboardButton(Messages.ADMIN_ADD_EMAIL_BTN, callback_data=CallbackData.ADMIN_ADD_EMAIL)])
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_PANEL)])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def admin_email_view_actions(campaign_id: int) -> InlineKeyboardMarkup:
        """Actions for viewing an email in admin panel (Delete, Back)."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ حذف کمپین", callback_data=CallbackData.ADMIN_DELETE_EMAIL.format(id=campaign_id))],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.ADMIN_MANAGE_EMAILS)]
        ])
