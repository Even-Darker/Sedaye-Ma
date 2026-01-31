
import pytest
from sqlalchemy import select, func, desc
from src.database.models import User, UserReportLog, InstagramTarget, TargetStatus
from src.utils import Formatters
from src.utils.security import encrypt_id

def test_progress_bar():
    """Test the progress bar generator helper."""
    # 0%
    assert Formatters.generate_progress_bar(0) == "░░░░░░░░░░"
    # 50%
    assert Formatters.generate_progress_bar(50) == "█████░░░░░"
    # 100%
    assert Formatters.generate_progress_bar(100) == "██████████"
    # Custom length
    assert Formatters.generate_progress_bar(50, length=4) == "██░░"

@pytest.mark.asyncio
async def test_leaderboard_ranking_and_tiebreak(db_session):
    """Test leaderboard ranking with ties and medals logic."""
    # 1. Setup mock data
    # User A: 10 reports, joined earlier
    # User B: 10 reports, joined later
    # User C: 15 reports
    
    u_a_id = 1
    u_b_id = 2
    u_c_id = 3
    
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    user_a = User(id=u_a_id, encrypted_chat_id=encrypt_id(u_a_id), first_seen=now - timedelta(days=10))
    user_b = User(id=u_b_id, encrypted_chat_id=encrypt_id(u_b_id), first_seen=now - timedelta(days=5))
    user_c = User(id=u_c_id, encrypted_chat_id=encrypt_id(u_c_id), first_seen=now - timedelta(days=2))
    
    db_session.add_all([user_a, user_b, user_c])
    await db_session.flush()
    
    # Target
    target = InstagramTarget(ig_handle="test", status=TargetStatus.ACTIVE)
    db_session.add(target)
    await db_session.flush()
    
    # Reports
    # User C: 15 reports
    for _ in range(15):
        db_session.add(UserReportLog(target_id=target.id, encrypted_user_id=user_c.encrypted_chat_id))
    
    # User A: 10 reports
    for _ in range(10):
        db_session.add(UserReportLog(target_id=target.id, encrypted_user_id=user_a.encrypted_chat_id))
        
    # User B: 10 reports
    for _ in range(10):
        db_session.add(UserReportLog(target_id=target.id, encrypted_user_id=user_b.encrypted_chat_id))
    
    await db_session.commit()
    
    # 2. Execute Ranking Query (same as in show_leaderboard)
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
    top_results = (await db_session.execute(top_users_stmt)).all()
    
    # Assertions
    assert len(top_results) == 3
    
    # Rank 1: User C (15 reports)
    assert top_results[0][0] == user_c.encrypted_chat_id
    assert top_results[0][1] == 15
    
    # Rank 2: User A (10 reports, joined earlier)
    assert top_results[1][0] == user_a.encrypted_chat_id
    assert top_results[1][1] == 10
    
    # Rank 3: User B (10 reports, joined later)
    assert top_results[2][0] == user_b.encrypted_chat_id
    assert top_results[2][1] == 10
    
    # 3. Test Rank Calculation for User B (should be rank 3)
    user_count = 10
    enc_id = user_b.encrypted_chat_id
    
    rank_stmt = (
        select(func.count() + 1)
        .select_from(
            select(UserReportLog.encrypted_user_id)
            .join(User, UserReportLog.encrypted_user_id == User.encrypted_chat_id)
            .group_by(UserReportLog.encrypted_user_id, User.first_seen)
            .having(
                (func.count(UserReportLog.id) > user_count) |
                ((func.count(UserReportLog.id) == user_count) & (User.first_seen < user_b.first_seen))
            )
        )
    )
    user_rank_b = (await db_session.execute(rank_stmt)).scalar()
    assert user_rank_b == 3
    
    # Test Rank Calculation for User A (should be rank 2)
    user_rank_a_stmt = (
        select(func.count() + 1)
        .select_from(
            select(UserReportLog.encrypted_user_id)
            .join(User, UserReportLog.encrypted_user_id == User.encrypted_chat_id)
            .group_by(UserReportLog.encrypted_user_id, User.first_seen)
            .having(
                (func.count(UserReportLog.id) > 10) |
                ((func.count(UserReportLog.id) == 10) & (User.first_seen < user_a.first_seen))
            )
        )
    )
    user_rank_a = (await db_session.execute(user_rank_a_stmt)).scalar()
    assert user_rank_a == 2
