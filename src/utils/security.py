
import os
import logging
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_aessiv = None

def get_cipher():
    global _aessiv
    if _aessiv is None:
        key_str = os.getenv("ENCRYPTION_KEY")
        if not key_str:
            raise ValueError("ENCRYPTION_KEY not found in environment variables!")
        try:
            # Decode the base64 Fernet key to get raw bytes (32 bytes)
            key_bytes = base64.urlsafe_b64decode(key_str)
            # Initialize AESSIV (SIV mode for Deterministic Encryption)
            _aessiv = AESSIV(key_bytes)
        except Exception as e:
            logger.error(f"Invalid ENCRYPTION_KEY: {e}")
            raise
    return _aessiv

def encrypt_id(user_id: int) -> str:
    """
    Encrypts a user ID using AES-SIV (Deterministic).
    Returns base64 encoded string.
    """
    if user_id is None:
        return None
    try:
        cipher = get_cipher()
        # Encrypt ID
        ciphertext = cipher.encrypt(str(user_id).encode(), associated_data=None)
        # Return as url-safe base64 string
        return base64.urlsafe_b64encode(ciphertext).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_id(token: str) -> int:
    """
    Decrypts a deterministic token back to user ID.
    """
    if not token:
        return None
    try:
        cipher = get_cipher()
        ciphertext = base64.urlsafe_b64decode(token)
        plaintext = cipher.decrypt(ciphertext, associated_data=None)
        return int(plaintext.decode())
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None
