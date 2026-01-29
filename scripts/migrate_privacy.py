
import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.database.models import Base, Admin, User, UserStatus
from src.utils.security import encrypt_id
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db")
engine = create_async_engine(DATABASE_URL)

async def run_migration():
    async with engine.begin() as conn:
        logger.info("Starting Privacy Migration...")

        # 1. Rename existing tables to backup/legacy
        # We need to handle cases where tables might not exist (e.g. fresh install)
        tables = [
            "admins", 
            "notification_preferences",
            "user_report_logs",
            "user_concern_logs",
            "user_victory_logs",
            "user_config_reports",
            "user_email_actions"
        ]
        
        existing_tables = await conn.run_sync(lambda sync_conn: sync_conn.dialect.get_table_names(sync_conn))
        
        for table in tables:
            if table in existing_tables:
                # For Admin and Prefs, we want to migrate. For logs, we drop.
                if table in ["admins", "notification_preferences"]:
                    target_old = f"{table}_old"
                    if target_old in existing_tables:
                         logger.warning(f"{target_old} already exists. Dropping redundant '{table}' table.")
                         await conn.execute(text(f"DROP TABLE {table}"))
                    else:
                        logger.info(f"Renaming {table} to {table}_old")
                        await conn.execute(text(f"ALTER TABLE {table} RENAME TO {table}_old"))

                    # Drop potentially conflicting indices (ALWAYS)
                    if table == "admins":
                        await conn.execute(text("DROP INDEX IF EXISTS ix_admins_user_hash"))
                        await conn.execute(text("DROP INDEX IF EXISTS ix_admins_telegram_id"))
                else:
                    logger.info(f"Dropping incompatible log table: {table}")
                    await conn.execute(text(f"DROP TABLE {table}"))

    # 2. Create NEW Schema (all tables)
    logger.info("Creating new schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Data Migration
    async with engine.connect() as conn:
        # Check current tables again to see if _old tables exist
        current_tables = await conn.run_sync(lambda sync_conn: sync_conn.dialect.get_table_names(sync_conn))

        # Migrate Admins
        if "admins_old" in current_tables:
            logger.info("Migrating Admins...")
            
            # Check for columns in admins_old
            cols = await conn.run_sync(lambda sync_conn: [c['name'] for c in sync_conn.dialect.get_columns(sync_conn, "admins_old")])
            is_migrated = "user_hash" in cols
            
            result = await conn.execute(text("SELECT * FROM admins_old"))
            admins = result.fetchall()
            
            count = 0
            for admin in admins:
                if is_migrated:
                    # Direct Copy (assuming encrypted_telegram_id exists, ignoring user_hash if it was there)
                    # Actually, if it's already migrated, we might just copy encrypted_telegram_id
                    # But simpler to treat migration as 'legacy valid' if columns match new schema.
                    # Given the ambiguity, we'll focus on ensuring NEW schema compliance.
                    # If columns match new schema:
                    pass 
                    # Re-implementing valid copy if needed, but for now assuming we are migrating FROM legacy.
                    # If 'encrypted_telegram_id' is already there, we use it.
                    enc_id = getattr(admin, 'encrypted_telegram_id', None)
                    if not enc_id and hasattr(admin, 'telegram_id'):
                         enc_id = encrypt_id(admin.telegram_id)
                    
                    if enc_id:
                         await conn.execute(
                            text("""
                                INSERT OR IGNORE INTO admins (id, encrypted_telegram_id, role, created_at)
                                VALUES (:id, :enc_id, :role, :created_at)
                            """),
                            {"id": admin.id, "enc_id": enc_id, "role": admin.role, "created_at": admin.created_at}
                        )
                else:
                    # Legacy Transform
                    old_id = admin.id
                    raw_tg_id = admin.telegram_id
                    role = admin.role
                    created_at = admin.created_at
                    
                    enc_id = encrypt_id(raw_tg_id)
                    await conn.execute(
                        text("""
                            INSERT OR IGNORE INTO admins (id, encrypted_telegram_id, role, created_at)
                            VALUES (:id, :enc_id, :role, :created_at)
                        """),
                        {"id": old_id, "enc_id": enc_id, "role": role, "created_at": created_at}
                    )
                count += 1
            logger.info(f"Migrated {count} admins.")
            # Drop old table
            await conn.execute(text("DROP TABLE admins_old"))

        # Migrate Users (NotificationPreferences -> User)
        if "notification_preferences_old" in current_tables:
            logger.info("Migrating NotificationPreferences to Users...")
            result = await conn.execute(text("SELECT * FROM notification_preferences_old"))
            prefs = result.fetchall()
            
            for row in prefs:
                
                raw_chat_id = row.chat_id
                enc_chat_id = encrypt_id(raw_chat_id)
                await conn.execute(
                    text("""
                        INSERT INTO users (
                            encrypted_chat_id, 
                            first_seen, last_seen, 
                            is_blocked_by_user, status,
                            announcements_urgent, announcements_news, 
                            victories, targets, petitions, email_campaigns,
                            created_at, updated_at
                        )
                        VALUES (
                            :enc_id, 
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                            0, :active_status,
                            :u, :n, 
                            :v, :t, :p, :e,
                            :cat, :uat
                        )
                    """),
                    {
                        "enc_id": enc_chat_id,
                        "active_status": UserStatus.ACTIVE.name, 
                        "u": row.announcements_urgent,
                        "n": row.announcements_news,
                        "v": row.victories,
                        "t": row.targets,
                        "p": row.petitions,
                        "e": row.email_campaigns,
                        "cat": row.created_at,
                        "uat": row.updated_at
                    }
                )
            logger.info(f"Migrated {len(prefs)} users.")
            # Drop old table
            await conn.execute(text("DROP TABLE notification_preferences_old"))

        await conn.commit()
        logger.info("Migration Complete! 🚀")

if __name__ == "__main__":
    asyncio.run(run_migration())
