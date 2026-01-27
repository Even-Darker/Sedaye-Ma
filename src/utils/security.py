"""
Security utilities for Sedaye Ma bot.
Handles privacy-preserving operations like hashing.
"""
import hashlib
from config import settings

class SecurityManager:
    """Manages security and privacy operations."""
    
    @staticmethod
    def hash_user_id(user_id: int) -> str:
        """
        Create a privacy-preserving hash of the user ID.
        Uses SHA256 with a salt from settings.
        """
        # Ensure we have a salt, fallback to a default if not set (development safety)
        salt = getattr(settings, "secret_key", "default_salt_change_me")
        
        # Create hash: SHA256(user_id + salt)
        payload = f"{user_id}:{salt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

# Global instance
security_manager = SecurityManager()
