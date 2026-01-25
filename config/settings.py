"""
Settings management for Sedaye Ma bot.
Loads configuration from environment variables.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env')


@dataclass
class Settings:
    """Application settings loaded from environment."""
    
    # Telegram
    bot_token: str
    super_admin_ids: List[int]
    
    # Database
    database_url: str
    
    # Security
    encryption_key: str
    
    # Environment
    environment: str
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Load settings from environment variables."""
        # Parse admin IDs
        admin_ids_str = os.getenv('SUPER_ADMIN_IDS', '')
        super_admin_ids = []
        for id_str in admin_ids_str.split(','):
            id_str = id_str.strip()
            if id_str:
                try:
                    super_admin_ids.append(int(id_str))
                except ValueError:
                    print(f"⚠️  Warning: '{id_str}' is not a valid Telegram user ID (must be numeric)")
                    print("   Get your ID by messaging @userinfobot on Telegram")
        
        return cls(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            super_admin_ids=super_admin_ids,
            database_url=os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./data/sedaye_ma.db'),
            encryption_key=os.getenv('ENCRYPTION_KEY', ''),
            environment=os.getenv('ENVIRONMENT', 'development'),
        )
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'
    
    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        path = Path('./data')
        path.mkdir(exist_ok=True)
        return path


# Singleton instance
settings = Settings.from_env()
