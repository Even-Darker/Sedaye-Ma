"""
Message formatters for Sedaye Ma bot.
Handles formatting of messages with data.
"""
from datetime import datetime
from typing import Optional
from config import Messages


class Formatters:
    """Message formatting utilities."""
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with K/M suffix."""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        # 'escape' backslash first so we don't escape the escapes
        text = text.replace('\\', '\\\\')
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def format_target_card(target) -> str:
        """Format a target for display."""
        priority_label = {
            1: Messages.TARGET_PRIORITY_HIGH,
            2: Messages.TARGET_PRIORITY_HIGH,
            3: Messages.TARGET_PRIORITY_HIGH,
            4: Messages.TARGET_PRIORITY_MEDIUM,
            5: Messages.TARGET_PRIORITY_MEDIUM,
            6: Messages.TARGET_PRIORITY_MEDIUM,
            7: Messages.TARGET_PRIORITY_LOW,
            8: Messages.TARGET_PRIORITY_LOW,
            9: Messages.TARGET_PRIORITY_LOW,
            10: Messages.TARGET_PRIORITY_LOW,
        }.get(target.priority, Messages.TARGET_PRIORITY_MEDIUM)
        
        # Build reasons badges
        reasons_map = {
            "violence": Messages.REASON_VIOLENCE,
            "misinformation": Messages.REASON_MISINFORMATION,
            "human_rights": Messages.REASON_HUMAN_RIGHTS,
            "propaganda": Messages.REASON_PROPAGANDA,
            "harassment": Messages.REASON_HARASSMENT,
        }
        reasons = " \\| ".join([reasons_map.get(r, r) for r in (target.report_reasons or [])])
        
        # Progress bar (visual representation)
        report_count = target.anonymous_report_count
        progress = min(report_count / 1000, 1.0)  # 1000 as a milestone
        filled = int(progress * 10)
        progress_bar = "━" * filled + "░" * (10 - filled)
        
        followers = Formatters.format_number(target.followers_count)
        
        # Improved Layout:
        # Header (Priority)
        # Handle + Name
        # Stats Row (Clean icons)
        # Progress Bar
        # Reasons
        
        return f"""
{priority_label}

[*@{Formatters.escape_markdown(target.ig_handle)}*](https://instagram.com/{target.ig_handle})
{Formatters.escape_markdown(target.display_name or '')}

📊 {report_count} {Messages.TARGET_REPORTS}

{progress_bar} {int(progress * 100)}%

🏷️ {reasons if reasons else '\\-'}
"""
    
    @staticmethod
    def format_victory_card(victory, target) -> str:
        """Format a victory for display."""
        date_str = victory.victory_date.strftime("%Y/%m/%d")
        followers = Formatters.format_number(target.followers_count)
        
        return f"""
🎉 *{Messages.LATEST_VICTORY}*:

[@{Formatters.escape_markdown(target.ig_handle)}](https://instagram.com/{target.ig_handle}) \\- {Messages.VICTORY_REMOVED}
🗓️ {Formatters.escape_markdown(date_str)}

"{Messages.VICTORY_CELEBRATE}" 🔥
"""
    
    @staticmethod
    def format_petition_card(petition) -> str:
        """Format a petition for display."""
        # progress_percent = petition.progress_percent
        # filled = int(progress_percent / 10)
        # progress_bar = "█" * filled + "░" * (10 - filled)
        
        current = Formatters.escape_markdown(Formatters.format_number(petition.signatures_current))
        goal = Formatters.escape_markdown(Formatters.format_number(petition.signatures_goal))
        
        status_line = ""
        if petition.status.value == "achieved":
            status_line = f"\n{Messages.PETITION_ACHIEVED}"
        elif petition.status.value == "expired":
            status_line = f"\n{Messages.PETITION_EXPIRED}"
        elif petition.days_remaining is not None:
            status_line = f"\n{Messages.PETITION_DEADLINE.format(petition.days_remaining)}"
            
        status_line = Formatters.escape_markdown(status_line)
        
        return f"""
📢  *{Formatters.escape_markdown(petition.title)}*

📝 {Formatters.escape_markdown(petition.description[:200])}{'\\.\\.\\.' if len(petition.description) > 200 else ''}

"""
    
    @staticmethod
    def format_announcement(announcement) -> str:
        """Format an announcement for display."""
        category_icons = {
            "urgent": Messages.ANNOUNCEMENT_URGENT,
            "news": Messages.ANNOUNCEMENT_NEWS,
            "victory": Messages.ANNOUNCEMENT_VICTORY,
            "action": Messages.ANNOUNCEMENT_ACTION,
            "safety": Messages.ANNOUNCEMENT_SAFETY,
        }
        category = category_icons.get(announcement.category.value, "📢")
        
        return f"""
{category}

*{Formatters.escape_markdown(announcement.title)}*

{Formatters.escape_markdown(announcement.content)}
"""
    
    @staticmethod
    def format_stats(stats: dict) -> str:
        """Format live statistics."""
        return f"""
{Messages.STATS_HEADER}

{Messages.STATS_ACTIVE_TARGETS.format(stats.get('active_targets', 0))}
{Messages.STATS_REMOVED.format(stats.get('removed_targets', 0))}
{Messages.STATS_TOTAL_REPORTS.format(Formatters.escape_markdown(Formatters.format_number(stats.get('total_reports', 0))))}


━━━━━━━━━━━━━━━━━━━━━━━━━━

{Messages.STATS_THIS_WEEK}
{Messages.STATS_REPORTS_INCREASE.format(stats.get('weekly_increase_percent', 0))}
{Messages.STATS_NEW_REMOVALS.format(stats.get('weekly_removals', 0))}
"""
    
    @staticmethod
    def format_solidarity_message(message) -> str:
        """Format a solidarity message."""
        location = message.location if message.location else Messages.MESSAGE_ANONYMOUS
        return f'"{Formatters.escape_markdown(message.message)}"\n━━━ {Formatters.escape_markdown(location)}'
    
    @staticmethod
    def format_template(template) -> str:
        """Format a report template for copying."""
        return f"""
{Messages.TEMPLATE_HEADER}
*{Formatters.escape_markdown(template.name_fa)} / {Formatters.escape_markdown(template.name_en)}*

{Messages.TEMPLATE_COPY_INSTRUCTION}

```
{template.template_en}
```
"""
    
    @staticmethod
    def format_new_petition_announcement(petition) -> str:
        """Format a new petition announcement."""
        return f"""
📢 *پتیشن جدیدی اضافه شد\\!*

[{Formatters.escape_markdown(petition.title)}]({petition.url})

📝 توضیحات: {Formatters.escape_markdown(petition.description)}
"""
