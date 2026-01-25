"""
Statistics service for Sedaye Ma bot.
Aggregates and caches statistics.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func

from src.database import get_db, InstagramTarget, Victory
from src.database.models import TargetStatus


class StatsService:
    """Service for calculating and caching statistics."""
    
    @staticmethod
    async def get_overview_stats() -> dict:
        """Get overview statistics for the dashboard."""
        async with get_db() as session:
            # Active targets
            active_result = await session.execute(
                select(func.count(InstagramTarget.id))
                .where(InstagramTarget.status == TargetStatus.ACTIVE)
            )
            active_targets = active_result.scalar() or 0
            
            # Removed targets
            removed_result = await session.execute(
                select(func.count(InstagramTarget.id))
                .where(InstagramTarget.status == TargetStatus.REMOVED)
            )
            removed_targets = removed_result.scalar() or 0
            
            # Total reports
            reports_result = await session.execute(
                select(func.sum(InstagramTarget.anonymous_report_count))
            )
            total_reports = reports_result.scalar() or 0
            
            # Followers silenced
            silenced_result = await session.execute(
                select(func.sum(InstagramTarget.followers_count))
                .where(InstagramTarget.status == TargetStatus.REMOVED)
            )
            followers_silenced = silenced_result.scalar() or 0
            
            # This week's victories
            week_ago = datetime.utcnow() - timedelta(days=7)
            weekly_result = await session.execute(
                select(func.count(Victory.id))
                .where(Victory.victory_date >= week_ago)
            )
            weekly_victories = weekly_result.scalar() or 0
            
            return {
                'active_targets': active_targets,
                'removed_targets': removed_targets,
                'total_reports': total_reports,
                'followers_silenced': followers_silenced,
                'weekly_victories': weekly_victories,
            }
    
    @staticmethod
    async def get_hottest_target():
        """Get the target with most reports today."""
        async with get_db() as session:
            result = await session.execute(
                select(InstagramTarget)
                .where(InstagramTarget.status == TargetStatus.ACTIVE)
                .order_by(InstagramTarget.anonymous_report_count.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
