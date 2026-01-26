"""
Database connection and session management for Sedaye Ma bot.
Uses async SQLAlchemy with aiosqlite for SQLite support.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, text

from config import settings
from .models import Base


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database and create all tables."""
    # Ensure data directory exists
    settings.data_dir.mkdir(exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed default report templates
    await seed_report_templates()
    
    # Sync Super Admins from Environment
    await sync_super_admins()

    # Run Migrations
    await check_migrations()


async def seed_report_templates():
    """Seed default report templates if they don't exist."""
    from .models import ReportTemplate
    from sqlalchemy import select
    
    templates = [
        {
            "violation_type": "violence",
            "name_fa": "خشونت و تهدید",
            "name_en": "Violence & Threats",
            "template_en": "This account promotes violence and threatens individuals. The content includes threatening language and calls to violence which violates Instagram's Community Guidelines on Violence and Threats.",
            "template_fa": "این حساب کاربری خشونت را ترویج می‌دهد و افراد را تهدید می‌کند."
        },
        {
            "violation_type": "misinformation",
            "name_fa": "اطلاعات نادرست",
            "name_en": "Misinformation",
            "template_en": "This account spreads dangerous misinformation that could harm individuals. The content includes false claims which violates Instagram's policies on Misinformation.",
            "template_fa": "این حساب کاربری اطلاعات نادرست و خطرناک منتشر می‌کند."
        },
        {
            "violation_type": "human_rights",
            "name_fa": "نقض حقوق بشر",
            "name_en": "Human Rights Violations",
            "template_en": "This account is involved in or promotes human rights violations. The content supports oppression and persecution of individuals which violates Instagram's Community Guidelines.",
            "template_fa": "این حساب کاربری در نقض حقوق بشر دخیل است یا آن را ترویج می‌کند."
        },
        {
            "violation_type": "propaganda",
            "name_fa": "تبلیغات رژیم",
            "name_en": "Regime Propaganda",
            "template_en": "This account spreads state propaganda and promotes an oppressive regime. The content glorifies human rights abuses which violates Instagram's policies.",
            "template_fa": "این حساب کاربری تبلیغات رژیم سرکوبگر را منتشر می‌کند."
        },
        {
            "violation_type": "harassment",
            "name_fa": "آزار و اذیت",
            "name_en": "Harassment",
            "template_en": "This account engages in targeted harassment of individuals. The content includes bullying and intimidation which violates Instagram's policies on Bullying and Harassment.",
            "template_fa": "این حساب کاربری افراد را هدف آزار و اذیت قرار می‌دهد."
        },
    ]
    
    async with AsyncSessionLocal() as session:
        for template_data in templates:
            # Check if exists
            result = await session.execute(
                select(ReportTemplate).where(
                    ReportTemplate.violation_type == template_data["violation_type"]
                )
            )
            if not result.scalar_one_or_none():
                template = ReportTemplate(**template_data)
                session.add(template)
        
        await session.commit()


async def sync_super_admins():
    """Sync super admins from environment settings to database."""
    from .models import Admin, AdminRole
    from sqlalchemy import select
    
    if not settings.super_admin_ids:
        return

    async with AsyncSessionLocal() as session:
        for user_id in settings.super_admin_ids:
            # Check if exists
            result = await session.execute(
                select(Admin).where(Admin.telegram_id == user_id)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                # Create new super admin
                admin = Admin(telegram_id=user_id, role=AdminRole.SUPER_ADMIN)
                session.add(admin)
            elif admin.role != AdminRole.SUPER_ADMIN:
                # Promote existing admin
                admin.role = AdminRole.SUPER_ADMIN
                session.add(admin)
        
        await session.commit()


@asynccontextmanager
async def get_db():
    """Get database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_migrations():
    """Check and run necessary database migrations."""
    import logging
    logger = logging.getLogger(__name__)
    
    async with AsyncSessionLocal() as session:
        # Check if free_configs.report_count exists
        try:
            # We can't easily check columns in sqlite via sqlalchemy inspector in async mode quickly without creating a sync engine or raw sql
            # Let's try to query it. If it fails, add it.
            await session.execute(text("SELECT report_count FROM free_configs LIMIT 1"))
        except Exception:
            logger.info("Migration: Adding report_count to free_configs...")
            await session.rollback() # Clear error
            async with engine.begin() as conn:
                await conn.execute(text("ALTER TABLE free_configs ADD COLUMN report_count INTEGER DEFAULT 0"))
            logger.info("Migration: Done.")
        else:
            logger.info("Migration: No changes needed.")
