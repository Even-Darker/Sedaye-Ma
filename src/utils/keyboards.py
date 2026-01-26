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
    MENU_STATS = "menu:stats"
    MENU_ANNOUNCEMENTS = "menu:announcements"
    MENU_PETITIONS = "menu:petitions"
    MENU_SOLIDARITY = "menu:solidarity"
    MENU_RESOURCES = "menu:resources"
    MENU_SETTINGS = "menu:settings"
    
    # Navigation
    BACK_MAIN = "nav:main"
    BACK_SANDISI = "nav:sandisi"
    BACK_FILTER = "nav:filter"
    BACK = "nav:back"
    BACK_ADMIN = "nav:admin"
    
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
    ADMIN_ANNOUNCEMENTS = "admin:announcements"
    ADMIN_PETITIONS = "admin:petitions"
    ADMIN_SOLIDARITY = "admin:solidarity"
    ADMIN_STATS = "admin:stats"
    ADMIN_MANAGE_ADMINS = "admin:manage_admins"
    ADMIN_PENDING_TARGETS = "admin:pending_targets"
    
    ADMIN_TARGET_EDIT = "admin:target:edit:{id}"
    ADMIN_TARGET_REMOVE = "admin:target:remove:{id}"
    ADMIN_TARGET_VICTORY = "admin:target:victory:{id}"
    ADMIN_CONFIRM_REMOVAL = "admin:confirm_removal:{id}"
    
    ADMIN_APPROVE_MSG = "admin:approve_msg:{id}"
    ADMIN_REJECT_MSG = "admin:reject_msg:{id}"
    
    ADMIN_CONFIRM_CLOSED_YES = "admin:closed:yes:{id}"
    ADMIN_CONFIRM_CLOSED_NO = "admin:closed:no:{id}"
    
    ADMIN_ADD_ADMIN = "admin:add_admin"
    ADMIN_REMOVE_ADMIN = "admin:remove_admin:{id}"


# Persistent bottom button text
MAIN_MENU_BUTTON = "🏠 منوی اصلی"


class Keyboards:
    """Keyboard builders for the bot."""
    
    @staticmethod
    def persistent_menu() -> ReplyKeyboardMarkup:
        """Persistent keyboard with main menu shortcut."""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(MAIN_MENU_BUTTON)]],
            resize_keyboard=True,
            is_persistent=True
        )
    
    @staticmethod
    def start() -> InlineKeyboardMarkup:
        """Start button keyboard."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.START_BUTTON, callback_data="start")]
        ])
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Main menu keyboard."""
        buttons = [
            [InlineKeyboardButton(Messages.MENU_TARGETS, callback_data=CallbackData.MENU_TARGETS)],
            [InlineKeyboardButton(Messages.MENU_ANNOUNCEMENTS, callback_data=CallbackData.MENU_ANNOUNCEMENTS)],
            [InlineKeyboardButton(Messages.MENU_PETITIONS, callback_data=CallbackData.MENU_PETITIONS)],
            [InlineKeyboardButton(Messages.MENU_SOLIDARITY, callback_data=CallbackData.MENU_SOLIDARITY)],
            [InlineKeyboardButton(Messages.MENU_RESOURCES, callback_data=CallbackData.MENU_RESOURCES)],
            [InlineKeyboardButton(Messages.MENU_SETTINGS, callback_data=CallbackData.MENU_SETTINGS)],
        ]
        # Admin only: show admin panel button
        if is_admin:
            buttons.append([InlineKeyboardButton("🔐 پنل مدیریت", callback_data="admin:panel")])
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def main_menu_persistent(is_admin: bool = False) -> ReplyKeyboardMarkup:
        """Main menu persistent keyboard (Reply Keyboard)."""
        buttons = [
            [KeyboardButton(Messages.MENU_TARGETS)],  # Row 1: Report Sandisi (Main)
            [KeyboardButton(Messages.MENU_ANNOUNCEMENTS), KeyboardButton(Messages.MENU_PETITIONS)],
            [KeyboardButton(Messages.MENU_SOLIDARITY), KeyboardButton(Messages.MENU_RESOURCES)],
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
            priority_emoji = "🔴" if target.priority <= 3 else "🟡" if target.priority <= 6 else "🟢"
            # Row 2: Quick Actions
            row = [
                InlineKeyboardButton(
                    f"{priority_emoji} @{target.ig_handle}",
                    url=f"https://instagram.com/{target.ig_handle}"
                ),
                InlineKeyboardButton(
                    "مشکل داره",   # "Concerns" 
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
    def petition_actions(petition_id: int, url: str) -> InlineKeyboardMarkup:
        """Petition action buttons."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(Messages.SIGN_PETITION, url=url)],
            [InlineKeyboardButton(Messages.SHARE_BUTTON, switch_inline_query=f"petition_{petition_id}")],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.MENU_PETITIONS)]
        ])
    
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
            [InlineKeyboardButton(Messages.GUIDE_SUPPORT, callback_data=CallbackData.RESOURCE_SUPPORT)],
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
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)]
        ])
    
    @staticmethod
    def admin_menu(is_super_admin: bool = False, pending_count: int = 0) -> InlineKeyboardMarkup:
        """Admin panel menu."""
        pending_badge = f" ({pending_count})" if pending_count > 0 else ""
        buttons = [
            [InlineKeyboardButton(f"✅ تأیید صفحات پیشنهادی{pending_badge}", callback_data=CallbackData.ADMIN_PENDING_TARGETS)],
            [InlineKeyboardButton(Messages.ADMIN_MANAGE_TARGETS, callback_data=CallbackData.ADMIN_MANAGE_TARGETS)],
            [InlineKeyboardButton(Messages.ADMIN_ANNOUNCEMENTS, callback_data=CallbackData.ADMIN_ANNOUNCEMENTS)],
            [InlineKeyboardButton(Messages.ADMIN_PETITIONS, callback_data=CallbackData.ADMIN_PETITIONS)],
            [InlineKeyboardButton(Messages.ADMIN_SOLIDARITY, callback_data=CallbackData.ADMIN_SOLIDARITY)],
            [InlineKeyboardButton(Messages.ADMIN_STATS, callback_data=CallbackData.ADMIN_STATS)],
        ]
        if is_super_admin:
            buttons.append([InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data=CallbackData.ADMIN_MANAGE_ADMINS)])
        buttons.append([InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.BACK_MAIN)])
        return InlineKeyboardMarkup(buttons)
    
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
                InlineKeyboardButton("🏆 تایید بسته شدن", callback_data=CallbackData.ADMIN_CONFIRM_CLOSED_YES.format(id=target_id)),
            ],
            [
                InlineKeyboardButton("❌ رد کردن", callback_data=CallbackData.ADMIN_CONFIRM_CLOSED_NO.format(id=target_id)),
            ]
        ])

    @staticmethod
    def concern_menu(target_id: int) -> InlineKeyboardMarkup:
        """Menu for choosing concern type."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 صفحه بسته شده", callback_data=CallbackData.TARGET_CONCERN_CLOSED.format(id=target_id))],
            [InlineKeyboardButton("💬 موارد دیگر", callback_data=CallbackData.TARGET_CONCERN_OTHER.format(id=target_id))],
            [InlineKeyboardButton(Messages.BACK_BUTTON, callback_data=CallbackData.TARGETS_LIST)], 
        ])
