"""
Database models for Sedaye Ma bot.
Privacy-first design: NO user data stored except admin IDs (with consent).
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, 
    DateTime, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AdminRole(enum.Enum):
    """Admin role levels."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"


class TargetStatus(enum.Enum):
    """Instagram target status."""
    PENDING = "pending"   # User-suggested, awaiting admin approval
    ACTIVE = "active"     # Approved and visible
    REPORTED = "reported" # High report count
    REMOVED = "removed"   # Victory - page removed


class AnnouncementCategory(enum.Enum):
    """Announcement categories."""
    URGENT = "urgent"
    NEWS = "news"
    VICTORY = "victory"
    ACTION = "action"
    SAFETY = "safety"


class PetitionStatus(enum.Enum):
    """Petition status."""
    ACTIVE = "active"
    ACHIEVED = "achieved"
    EXPIRED = "expired"


class UserStatus(enum.Enum):
    """User status."""
    ACTIVE = "active"
    RESTRICTED = "restricted"
    BANNED = "banned"

# ═══════════════════════════════════════════════════════════════
# ADMIN MODEL (Only user data we store - with explicit consent)
# ═══════════════════════════════════════════════════════════════

class Admin(Base):
    """
    Admin users who have explicitly consented to being tracked.
    IDs are encrypted at rest.
    """
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    id = Column(Integer, primary_key=True)
    encrypted_telegram_id = Column(String(255), unique=True, nullable=False, index=True) # Deterministic Encrypted ID
    
    role = Column(SQLEnum(AdminRole), default=AdminRole.MODERATOR)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    targets_added = relationship("InstagramTarget", back_populates="added_by")
    announcements = relationship("Announcement", back_populates="created_by")
    free_configs = relationship("FreeConfig", back_populates="created_by")
    email_campaigns = relationship("EmailCampaign", back_populates="created_by")
    
    def __repr__(self):
        return f"<Admin(id={self.id}, role={self.role.value})>"


# ═══════════════════════════════════════════════════════════════
# INSTAGRAM TARGET MODEL
# ═══════════════════════════════════════════════════════════════

class InstagramTarget(Base):
    """Instagram pages flagged for reporting."""
    __tablename__ = "instagram_targets"
    
    id = Column(Integer, primary_key=True)
    ig_handle = Column(String(255), unique=True, nullable=False)  # e.g., "regime_page123"
    display_name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    profile_pic_url = Column(String(512), nullable=True)
    
    # Stats
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    
    # Report tracking (NO user IDs - just counters)
    report_reasons = Column(JSON, default=list)  # ["violence", "misinformation", ...]
    anonymous_report_count = Column(Integer, default=0)  # No user tracking!
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest
    
    # Status
    status = Column(SQLEnum(TargetStatus), default=TargetStatus.ACTIVE)
    
    # Timestamps
    first_listed = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)
    
    # Admin who added (foreign key)
    added_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    added_by = relationship("Admin", back_populates="targets_added")
    
    # Victory relationship
    victory = relationship("Victory", back_populates="target", uselist=False)
    
    def __repr__(self):
        return f"<InstagramTarget(handle=@{self.ig_handle}, status={self.status.value})>"
    
    @property
    def instagram_url(self) -> str:
        return f"https://instagram.com/{self.ig_handle}"


# ═══════════════════════════════════════════════════════════════
# VICTORY MODEL
# ═══════════════════════════════════════════════════════════════

class Victory(Base):
    """Recorded victories - pages that were successfully removed."""
    __tablename__ = "victories"
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("instagram_targets.id"), unique=True)
    victory_date = Column(DateTime, default=datetime.utcnow)
    celebration_message = Column(Text, nullable=True)
    final_report_count = Column(Integer, default=0)
    
    # Relationship
    target = relationship("InstagramTarget", back_populates="victory")
    
    def __repr__(self):
        return f"<Victory(target_id={self.target_id}, date={self.victory_date})>"


# ═══════════════════════════════════════════════════════════════
# ANNOUNCEMENT MODEL
# ═══════════════════════════════════════════════════════════════

class Announcement(Base):
    """Announcements and news for the community."""
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(SQLEnum(AnnouncementCategory), default=AnnouncementCategory.NEWS)
    
    # Media (optional)
    image_url = Column(String(512), nullable=True)
    
    # Anonymous reactions (no user tracking)
    reaction_fire = Column(Integer, default=0)
    reaction_heart = Column(Integer, default=0)
    reaction_fist = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    is_pinned = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    created_by = relationship("Admin", back_populates="announcements")
    
    def __repr__(self):
        return f"<Announcement(id={self.id}, title={self.title[:30]})>"


# ═══════════════════════════════════════════════════════════════
# PETITION MODEL
# ═══════════════════════════════════════════════════════════════

class Petition(Base):
    """Petitions for users to sign."""
    __tablename__ = "petitions"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    url = Column(String(512), nullable=False)  # External petition link
    
    # Progress tracking
    signatures_goal = Column(Integer, default=100000)
    signatures_current = Column(Integer, default=0)
    visit_count = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(PetitionStatus), default=PetitionStatus.ACTIVE)
    deadline = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Petition(id={self.id}, title={self.title[:30]})>"
    
    @property
    def progress_percent(self) -> int:
        if self.signatures_goal == 0:
            return 0
        return min(100, int((self.signatures_current / self.signatures_goal) * 100))
    
    @property
    def days_remaining(self) -> Optional[int]:
        if not self.deadline:
            return None
        delta = self.deadline - datetime.utcnow()
        return max(0, delta.days)


# ═══════════════════════════════════════════════════════════════
# FREE CONFIG MODEL
# ═══════════════════════════════════════════════════════════════

class FreeConfig(Base):
    """Free VPN configs shared by admins."""
    __tablename__ = "free_configs"

    id = Column(Integer, primary_key=True)
    config_uri = Column(Text, nullable=False)  # v2ray URI
    description = Column(String(255), nullable=True)  # Optional note (e.g., "US Server", "Fast")

    is_active = Column(Boolean, default=True)
    report_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)

    # Relationship
    created_by = relationship("Admin", back_populates="free_configs")

    def __repr__(self):
        return f"<FreeConfig(id={self.id}, description={self.description})>"


# ═══════════════════════════════════════════════════════════════
# SOLIDARITY MESSAGE MODEL
# ═══════════════════════════════════════════════════════════════

class SolidarityMessage(Base):
    """Anonymous solidarity messages from the community."""
    __tablename__ = "solidarity_messages"
    
    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)  # No user ID attached!
    location = Column(String(100), nullable=True)  # Optional: city/country
    
    # Moderation
    is_approved = Column(Boolean, default=False)
    
    # Anonymous heart counter
    hearts = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SolidarityMessage(id={self.id}, approved={self.is_approved})>"


# ═══════════════════════════════════════════════════════════════
# REPORT TEMPLATE MODEL
# ═══════════════════════════════════════════════════════════════

class ReportTemplate(Base):
    """Pre-written report templates for different violation types."""
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True)
    violation_type = Column(String(50), unique=True, nullable=False)
    name_fa = Column(String(100), nullable=False)  # Persian name
    name_en = Column(String(100), nullable=False)  # English name
    template_fa = Column(Text, nullable=True)  # Persian template
    template_en = Column(Text, nullable=False)  # English template
    
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ReportTemplate(type={self.violation_type})>"


# ═══════════════════════════════════════════════════════════════
# USER MODEL (Centralized & Encrypted)
# ═══════════════════════════════════════════════════════════════

class User(Base):
    """
    Central user entity.
    - Stores Chat ID ENCRYPTED (reversible for notifications).
    - Tracks basic activity stats.
    - Stores notification preferences.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    encrypted_chat_id = Column(String(255), unique=True, nullable=False, index=True) # Deterministic Encrypted ID
    
    # Activity
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Status
    # is_blocked_by_user: They blocked the bot (detected via 403 Forbidden).
    is_blocked_by_user = Column(Boolean, default=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    
    # Notification Preferences
    announcements_urgent = Column(Boolean, default=True)
    announcements_news = Column(Boolean, default=True)
    victories = Column(Boolean, default=True)
    targets = Column(Boolean, default=True)
    petitions = Column(Boolean, default=True)
    email_campaigns = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, status={self.status.value})>"


# ═══════════════════════════════════════════════════════════════
# USER REPORT LOG
# ═══════════════════════════════════════════════════════════════

class UserReportLog(Base):
    """
    Tracks which users have reported which targets.
    Uses Encrypted ID for privacy compliance.
    """
    __tablename__ = "user_report_logs"
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("instagram_targets.id"), nullable=False)
    
    encrypted_user_id = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('target_id', 'encrypted_user_id', name='uq_target_user_enc'),
    )
    
    def __repr__(self):
        return f"<ReportLog(target={self.target_id})>"


# ═══════════════════════════════════════════════════════════════
# USER CONCERN LOG
# ═══════════════════════════════════════════════════════════════

class UserConcernLog(Base):
    """
    Tracks concern reports.
    """
    __tablename__ = "user_concern_logs"
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("instagram_targets.id"), nullable=False)
    
    encrypted_user_id = Column(String(255), nullable=False)
    concern_type = Column(String(50), nullable=False)
    message_content = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('target_id', 'encrypted_user_id', 'concern_type', name='uq_concern_user_enc'),
    )


# ═══════════════════════════════════════════════════════════════
# USER VICTORY LOG
# ═══════════════════════════════════════════════════════════════

class UserVictoryLog(Base):
    """
    Tracks victory submissions.
    """
    __tablename__ = "user_victory_logs"
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("instagram_targets.id"), nullable=False)
    
    encrypted_user_id = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# USER CONFIG REPORT
# ═══════════════════════════════════════════════════════════════

class UserConfigReport(Base):
    """
    Tracks config reports.
    """
    __tablename__ = "user_config_reports"

    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey("free_configs.id"), nullable=False)
    encrypted_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('config_id', 'encrypted_user_id', name='uq_config_user_enc'),
    )


# ═══════════════════════════════════════════════════════════════
# EMAIL CAMPAIGN MODEL
# ═══════════════════════════════════════════════════════════════

class EmailCampaign(Base):
    """Email campaigns for users to send."""
    __tablename__ = "email_campaigns"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    receiver_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    
    action_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    created_by = relationship("Admin", back_populates="email_campaigns")
    
    def __repr__(self):
        return f"<EmailCampaign(id={self.id}, title={self.title[:30]})>"
        
    @property
    def mailto_link(self) -> str:
        """Generate mailto link."""
        from urllib.parse import quote
        safe_subject = quote(self.subject)
        safe_body = quote(self.body)
        return f"mailto:{self.receiver_email}?subject={safe_subject}&body={safe_body}"

    @property
    def redirect_link(self) -> str:
        from urllib.parse import quote
        safe_to = quote(self.receiver_email)
        safe_subject = quote(self.subject)
        safe_body = quote(self.body)
        return f"https://even-darker.github.io/Email-Redirector/?to={safe_to}&subject={safe_subject}&body={safe_body}"


# ═══════════════════════════════════════════════════════════════
# USER EMAIL ACTION
# ═══════════════════════════════════════════════════════════════

class UserEmailAction(Base):
    """
    Tracks which users have sent emails to prevent spam counting.
    """
    __tablename__ = "user_email_actions"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("email_campaigns.id"), nullable=False)
    encrypted_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('campaign_id', 'encrypted_user_id', name='uq_campaign_user_enc'),
    )

